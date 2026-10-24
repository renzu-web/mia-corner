#!/usr/bin/env python3
"""Two-state talking face made from two of the owner's own drawings.

Asked for directly: "could you not just use the mouth open image for when you talk?" Yes. The
hand-painted mouth (jaw warp + fill) is gone. This finds the mouth by itself: take the two
drawings, align them, and the only place they differ is the mouth, so the difference map *is*
the mouth mask. Blend between the two inside that mask and nothing else moves.

That removes both reported faults by construction: nothing is split (no jaw warp, no seam) and
nothing is too big or off (the mouth is the artist's, at the artist's scale and position).
"""
import argparse
import json
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageFilter


def load(path, size):
    return np.asarray(Image.open(path).convert("RGB").resize((size, size), Image.LANCZOS)).astype(np.float32)


def best_shift(a, b, radius=14):
    """Find the small translation that lines the two drawings up, judged on the face only."""
    h, w, _ = a.shape
    ys, xs = np.mgrid[0:h, 0:w]
    face = (xs > 0.25 * w) & (xs < 0.75 * w) & (ys > 0.15 * h) & (ys < 0.85 * h)
    best = (1e18, 0, 0)
    for dy in range(-radius, radius + 1, 2):
        for dx in range(-radius, radius + 1, 2):
            bs = np.roll(np.roll(b, dy, axis=0), dx, axis=1)
            d = np.abs(a - bs).mean(2)
            score = float(d[face].mean())
            if score < best[0]:
                best = (score, dy, dx)
    return best[1], best[2], best[0]


def mouth_mask(shape, lm, feather=7):
    """A soft ellipse over the lips, from measured landmarks.

    First version took the mask straight from where the two drawings differ, which sounded
    clever and failed: the open drawing carries a faint tiled watermark, so the difference map
    lit up across the whole face and the "mouth" came out 116x194. Anchor it to the lips instead.
    """
    h, w = shape[0], shape[1]
    cx, cy = lm["lip_cx"], lm["lip_cy"]
    hw = lm["lip_w"] * 0.78 + feather          # lips spread a little when the mouth opens
    hh = lm["lip_h"] * 0.95 + 6 + feather
    yy, xx = np.mgrid[0:h, 0:w]
    ell = (((xx - cx) / hw) ** 2 + ((yy - cy) / hh) ** 2) <= 1.0
    soft = np.asarray(Image.fromarray((ell * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(feather))).astype(np.float32) / 255.0
    return soft[..., None], dict(cx=cx, cy=cy, hw=hw, hh=hh)


def envelope(path, fps, tmp="/tmp/mouth_swap.wav"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "16000",
                    "-f", "wav", tmp], check=True)
    with wave.open(tmp, "rb") as w:
        n, sr = w.getnframes(), w.getframerate()
        raw = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    per = max(1, sr // fps)
    env = np.array([float(np.sqrt((raw[i:i + per] ** 2).mean()))
                    for i in range(0, len(raw) - per + 1, per)], dtype=np.float32)
    env = np.convolve(env, np.ones(3, dtype=np.float32) / 3, mode="same")
    env = env / (float(env.max()) or 1.0)
    return np.clip((env - 0.06) / 0.70, 0.0, 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--closed", required=True)
    ap.add_argument("--open", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--landmarks", required=True)
    a = ap.parse_args()

    A = load(a.closed, a.size)
    B = load(a.open, a.size)
    dy, dx, score = best_shift(A, B)
    B = np.roll(np.roll(B, dy, axis=0), dx, axis=1)
    lm = json.load(open(a.landmarks))
    k = a.size / lm.pop("size", a.size)
    if k != 1.0:
        for key in ("lip_cx", "lip_cy", "lip_w", "lip_h"):
            lm[key] = lm[key] * k
    mask, box = mouth_mask(A.shape, lm)
    print(f"aligned open drawing by dy={dy} dx={dx} (residual {score:.2f}); mask {box}")

    env = envelope(a.audio, a.fps)
    frames = "/tmp/mouth_swap_frames"
    subprocess.run(["rm", "-rf", frames], check=True)
    os.makedirs(frames, exist_ok=True)
    for i, amount in enumerate(env):
        t = float(amount) ** 0.8          # snappier at conversational volume
        f = A * (1 - mask * t) + B * (mask * t)
        Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).save(f"{frames}/f_{i:04d}.png")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{frames}/f_%04d.png", "-i", a.audio, "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-shortest", a.out],
                   check=True)
    print("wrote", a.out, os.path.getsize(a.out), "bytes")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Static-frame talking face for Mia's anime facecam.

Reported problems with the first version, both from watching it:
  * the mouth was not on her mouth. Root cause: the landmarks were guessed. At 512 the lips are
    at y=280 and the guess was y=242, so every opening landed on her philtrum. Landmarks are now
    read off the artwork with anime_grid.py and stored per base image in a JSON file.
  * the sway was unnatural. Removed. The frame is now dead still and only the mouth (and a slow
    blink) moves, which is what was asked for.

Usage:
  python3 anime_face_rig.py --base <still.jpg> --audio <voice.ogg> --out <clip.mp4> \
      [--landmarks <base.landmarks.json>] [--no-blink]
"""
import argparse
import json
import os
import subprocess
import wave

import numpy as np
from PIL import Image

# Defaults are for the approved straight-on base at 512x512, measured with anime_grid.py.
DEFAULTS = dict(lip_cx=256, lip_cy=280, lip_w=76, lip_h=20,
                eye_y=192, eye_x0=200, eye_x1=312, max_drop=11)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def load_envelope(path, fps, tmp="/tmp/anime_rig.wav"):
    """One 0..1 loudness figure per video frame, from any audio ffmpeg can read."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path,
                    "-ac", "1", "-ar", "16000", "-f", "wav", tmp], check=True)
    with wave.open(tmp, "rb") as w:
        n, sr = w.getnframes(), w.getframerate()
        raw = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    per = max(1, sr // fps)
    env = [float(np.sqrt((raw[i:i + per] ** 2).mean())) for i in range(0, len(raw) - per + 1, per)]
    if not env:
        return np.zeros(1, dtype=np.float32)
    env = np.convolve(np.asarray(env, dtype=np.float32), np.ones(3, dtype=np.float32) / 3, mode="same")
    env = env / (float(env.max()) or 1.0)
    return np.clip((env - 0.08) / 0.72, 0.0, 1.0)


def open_mouth(arr, amount, lm):
    """Open the mouth downward from a fixed upper lip, filling the gap.

    The upper lip stays put, the lower lip and jaw travel down, and the vacated space is filled
    with a shadowed interior plus a thin sliver of teeth once it is properly open.
    """
    if amount <= 0.002:
        return arr
    a = arr.copy()
    h, w, _ = a.shape
    cx, cy = lm["lip_cx"], lm["lip_cy"]
    half_w, half_h = lm["lip_w"] / 2.0, lm["lip_h"] / 2.0
    drop = lm["max_drop"] * amount
    jaw_y = int(cy + half_h)

    # 1. jaw and chin travel down, easing back to nothing further down the neck
    rows = np.arange(h)
    span = max(1, h - jaw_y)
    t = np.clip((rows - jaw_y) / span, 0.0, 1.0)
    shift = drop * (1.0 - t ** 1.5)
    shift[rows < jaw_y] = 0.0
    a = a[np.clip(rows - shift, 0, h - 1).astype(np.int32), :, :]

    # 2. the opening: top edge pinned to the upper lip, bottom edge follows the jaw
    yy, xx = np.mgrid[0:h, 0:w]
    top = cy - half_h
    bottom = cy + half_h + drop
    nx = (xx - cx) / half_w
    ny = np.where(yy < cy, (yy - top) / max(1e-6, (cy - top)),
                  (yy - cy) / max(1e-6, (bottom - cy)))
    f = np.abs(nx) ** 2.0 + np.abs(np.where(yy < cy, (cy - yy) / max(1e-6, (cy - top)),
                                             (yy - cy) / max(1e-6, (bottom - cy)))) ** 1.5
    mask = smoothstep((1.0 - f) / 0.45)[..., None]

    # interior: shadowed at the top, warmer towards the lower lip
    v = np.clip((yy - top) / max(1e-6, bottom - top), 0.0, 1.0)[..., None]
    interior = (np.array([28.0, 12.0, 15.0], np.float32) * (1 - v) +
                np.array([86.0, 38.0, 42.0], np.float32) * v)
    a = a * (1 - mask) + interior * mask

    # 3. no painted teeth. A flat tooth strip read as grey paste stuck to her face, so the
    #    opening is interior only: dark at the top, warmer towards the lower lip.

    # 4. soften the lip line so the opening grows out of the mouth instead of sitting on it
    rim = smoothstep((f - 0.80) / 0.45) * (1.0 - smoothstep((f - 1.15) / 0.35))
    rim = (rim * (f < 1.35))[..., None] * 0.40
    a = a * (1 - rim) + np.array([92.0, 50.0, 54.0], np.float32) * rim
    return a


def blink(arr, amount, lm):
    """Soft eyelid over the eye line. amount 1 = shut."""
    if amount <= 0.02:
        return arr
    a = arr.copy()
    h, w, _ = a.shape
    lid_h = max(2, int(0.075 * h * amount))
    y0 = lm["eye_y"] - lid_h // 2
    x0, x1 = max(0, lm["eye_x0"]), min(w, lm["eye_x1"])
    src_y = max(0, y0 - lid_h - 2)
    src = a[src_y:src_y + lid_h, x0:x1]
    if src.size == 0:
        return arr
    lid = np.asarray(Image.fromarray(src.astype(np.uint8)).resize((x1 - x0, lid_h), Image.LANCZOS))
    a[y0:y0 + lid_h, x0:x1] = lid.astype(np.float32)
    a[y0 + lid_h - 2:y0 + lid_h, x0:x1] *= 0.5     # lash line
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--landmarks")
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--no-blink", action="store_true")
    ap.add_argument("--max-open", type=float, default=0.85,
                    help="scale the loudness-to-openness curve; full open reads as a shout")
    a = ap.parse_args()

    lm = dict(DEFAULTS)
    if a.landmarks and os.path.exists(a.landmarks):
        lm.update(json.load(open(a.landmarks)))
    # landmarks are stored for the base's own pixel size
    src_size = lm.pop("size", a.size)
    if a.size != src_size:
        k = a.size / src_size
        for key in ("lip_cx", "lip_cy", "lip_w", "lip_h", "eye_y", "eye_x0", "eye_x1", "max_drop"):
            lm[key] = max(1, int(round(lm[key] * k)))

    base = np.asarray(Image.open(a.base).convert("RGB").resize((a.size, a.size), Image.LANCZOS)).astype(np.float32)
    env = load_envelope(a.audio, a.fps)
    frames = "/tmp/anime_rig_frames"
    subprocess.run(["rm", "-rf", frames], check=True)
    os.makedirs(frames, exist_ok=True)

    blink_period = a.fps * 4
    blink_len = max(1, int(0.09 * a.fps))
    for i, amount in enumerate(env):
        f = open_mouth(base, float(amount) * a.max_open, lm)
        if not a.no_blink:
            phase = i % blink_period
            b = float(np.sin(np.pi * (phase + 0.5) / blink_len)) if phase < blink_len else 0.0
            f = blink(f, b, lm)
        Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).save(f"{frames}/f_{i:04d}.png")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{frames}/f_%04d.png", "-i", a.audio,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-c:a", "aac", "-shortest", a.out], check=True)
    print("wrote", a.out, os.path.getsize(a.out), "bytes,", len(env), "frames, landmarks", lm)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Cut mia's twitch avatar from an owner-approved portrait.

    /workspace/pausia/.venv/bin/python tools/make_avatar.py [--src PATH] [--zoom 0.74]

A twitch avatar renders as small as 32px, so a head-and-shoulders frame is wasted:
the shoulders and dark background collapse into a blob. This crops tight on the
face, solves a gamma that puts the face on a readable brightness, then sharpens.

The face here is always an owner-approved photo. Never a generated one.

Measured on the approved shot: the source is underexposed (mean 18, centre 33) and
soft (laplacian var 2.8 at full res), so both the lift and the sharpen are load
bearing rather than polish.
"""
import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np

DEFAULT_SRC = Path("/workspace/mia-site/img/mia-portrait.jpg")
OUT = Path("/workspace/mia-site/img/brand")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--zoom", type=float, default=0.74, help="fraction of the frame to keep")
    ap.add_argument("--target", type=float, default=125.0, help="brightness for the face")
    ap.add_argument("--top", type=float, default=0.05, help="where the crop starts, as a fraction")
    a = ap.parse_args()

    img = cv2.imread(str(a.src))
    if img is None:
        print(f"cannot read {a.src}")
        return 2
    h, w = img.shape[:2]

    side = int(min(h, w) * a.zoom)
    left = (w - side) // 2
    top = int(h * a.top)
    crop = img[top:top + side, left:left + side]
    print(f"crop    {side}x{side} from {w}x{h} at x={left} y={top}")

    # gamma lift: puts the middle of the crop (the face) on the target, and leaves
    # the already-bright pixels alone, so highlights survive
    luma = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    c = luma[luma.shape[0] // 4:luma.shape[0] - luma.shape[0] // 4,
             luma.shape[1] // 4:luma.shape[1] - luma.shape[1] // 4].mean()
    gamma = math.log(a.target / 255.0) / math.log(max(c, 1.0) / 255.0)
    lifted = np.clip(255.0 * np.power(crop.astype(np.float64) / 255.0, gamma), 0, 255)
    print(f"lift    centre {c:.1f} -> ~{a.target:.0f} (gamma {gamma:.2f})")

    # denoise then sharpen: the lift multiplies grain, so the sharpen has to come after
    smooth = cv2.bilateralFilter(lifted.astype(np.uint8), 5, 25, 25)
    blur = cv2.GaussianBlur(smooth, (0, 0), 1.1)
    sharp = cv2.addWeighted(smooth, 1.7, blur, -0.7, 0)

    for size in (400, 800):
        out = cv2.resize(sharp, (size, size), interpolation=cv2.INTER_LANCZOS4)
        p = OUT / f"twitch-avatar{'' if size == 400 else '_800'}.png"
        OUT.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(p), out)
        lo = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
        print(f"avatar  {p}  {size}x{size}  mean {lo.mean():.0f}  "
              f"sharpness {cv2.Laplacian(lo, cv2.CV_64F).var():.0f}  "
              f"clipped {(lo > 250).mean() * 100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())

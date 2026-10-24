#!/usr/bin/env python3
"""Measure the landmarks the face rig needs from a still, instead of guessing them.

Guessed constants put the mouth animation on her chin, which is exactly the bug that got
reported. The lips are the reddest thing in the lower half of the face, so find them by colour
and derive the rest from that. Prints a JSON blob; feed the numbers to anime_face_rig.py.
"""
import json
import sys

import numpy as np
from PIL import Image


def find_landmarks(path, size=512, debug=None):
    im = Image.open(path).convert("RGB").resize((size, size), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    h, w, _ = a.shape
    red = a[:, :, 0] - (a[:, :, 1] + a[:, :, 2]) / 2.0
    ys, xs = np.mgrid[0:h, 0:w]
    region = (xs > 0.28 * w) & (xs < 0.72 * w) & (ys > 0.40 * h) & (ys < 0.74 * h)
    r = np.where(region, red, 0.0)

    prof = r.sum(1) / np.maximum((r > 0).sum(1), 1)
    k = np.ones(9) / 9
    prof = np.convolve(prof, k, mode="same")
    prof[~region.any(1)] = 0
    lip_y = int(np.argmax(prof))

    band = r[max(0, lip_y - 5):lip_y + 6]
    col = band.max(0)
    # Blush across the cheeks is red too, so a loose threshold grabs half the face. Start at
    # the reddest column and walk outwards while the redness stays high.
    peak = int(np.argmax(col))
    hi = col[peak]
    left = peak
    while left > 0 and col[left] > hi * 0.80:
        left -= 1
    right = peak
    while right < w - 1 and col[right] > hi * 0.80:
        right += 1
    cx = (left + right) // 2
    mw = max(20, right - left)

    # vertical extent of the lips: redness profile down the mouth column, same idea
    colband = r[:, max(0, cx - mw // 3):cx + mw // 3].max(1)
    peaky = colband[lip_y]
    top = lip_y
    while top > 0 and colband[top] > peaky * 0.55:
        top -= 1
    bot = lip_y
    while bot < h - 1 and colband[bot] > peaky * 0.55:
        bot += 1
    # redness also bleeds down the chin, so cap the lip height by proportion instead
    lip_h = max(6, int(mw * 0.30))
    top = lip_y - lip_h // 2
    bot = lip_y + lip_h // 2

    grey = a.mean(2)
    eye_reg = (xs > 0.30 * w) & (xs < 0.70 * w) & (ys > 0.22 * h) & (ys < lip_y - 0.10 * h)
    g = np.where(eye_reg, grey, 255.0)
    eprof = g.mean(1)
    eprof[~eye_reg.any(1)] = 255.0
    eye_y = int(np.argmin(eprof))

    res = dict(size=size, mouth_cx=cx, mouth_cy=lip_y, mouth_w=mw, mouth_h=lip_h,
               lip_top=int(top), lip_bottom=int(bot),
               eye_y=eye_y, eye_x0=max(0, cx - int(mw * 1.15)), eye_x1=min(w - 1, cx + int(mw * 1.15)),
               jaw_y=int(bot + 0.02 * h), tear_end=int(min(h - 1, bot + 0.30 * h)),
               max_drop=max(6, int(0.030 * h)))

    if debug:
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        d.rectangle([cx - mw // 2, top, cx + mw // 2, bot], outline=(0, 255, 0), width=1)
        d.line([0, lip_y, w, lip_y], fill=(0, 200, 255), width=1)
        d.line([0, eye_y, w, eye_y], fill=(255, 0, 200), width=1)
        d.line([0, res["jaw_y"], w, res["jaw_y"]], fill=(255, 200, 0), width=1)
        im.save(debug)
        im.crop((max(0, cx - mw), max(0, top - 40), min(w, cx + mw),
                 min(h, bot + 40))).resize((520, 520), Image.LANCZOS).save(dbg.replace(".png", "_zoom.png"))
    return res


if __name__ == "__main__":
    src = sys.argv[1]
    dbg = sys.argv[2] if len(sys.argv) > 2 else None
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    print(json.dumps(find_landmarks(src, size, dbg)))

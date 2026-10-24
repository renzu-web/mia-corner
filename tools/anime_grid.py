#!/usr/bin/env python3
"""Draw a labelled pixel grid on a still so the landmarks can be read off by eye.

Colour heuristics kept locking onto blusher instead of lips, so stop guessing: put numbered
lines every 32 pixels on both axes and read the numbers where the features actually are.
Output is a proof image plus a landmarks JSON for anime_face_rig.py.
"""
import sys

from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
size = int(sys.argv[3]) if len(sys.argv) > 3 else 512
im = Image.open(src).convert("RGB").resize((size, size), Image.LANCZOS)
d = ImageDraw.Draw(im)

for y in range(0, size, 32):
    colour = (255, 255, 0) if y % 128 == 0 else (0, 180, 255)
    for x in range(0, size, 8):
        d.line([x, y, x + 4, y], fill=colour, width=1)
    d.text((2, y + 1), str(y), fill=(255, 255, 255))
    d.text((size - 34, y + 1), str(y), fill=(255, 255, 255))

for x in range(0, size, 32):
    colour = (255, 0, 255) if x % 128 == 0 else (120, 120, 120)
    for y in range(0, size, 8):
        d.line([x, y, x, y + 4], fill=colour, width=1)
    d.text((x + 1, 2), str(x), fill=(255, 255, 255))
    d.text((x + 1, size - 12), str(x), fill=(255, 255, 255))

im.save(out)
print("wrote", out)

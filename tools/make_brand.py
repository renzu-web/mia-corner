#!/usr/bin/env python3
"""Draw mia's twitch channel banner, and cut an avatar from an approved photo.

    /workspace/pausia/.venv/bin/python make_brand.py

Banner is 1200x480, the size twitch asks for. Drawn rather than generated: no
image model is reachable from this box, and drawn text is crisp at any size.
Palette is lifted from mia-site/assets/style.css so the channel matches the site.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("/workspace/mia-site/img/brand")
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

CREAM = (251, 243, 233)
CREAM_LIGHT = (255, 253, 250)
ESPRESSO = (43, 35, 32)
ROSE = (232, 139, 161)
ROSE_DEEP = (194, 86, 111)
AMBER = (192, 122, 46)
MUTED = (141, 122, 110)

W, H = 1200, 480


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def spaced(draw, xy, text, fnt, fill, tracking=0):
    """Draw text with letter spacing. PIL has no tracking option.

    Returns the x position just after the last glyph.
    """
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def spaced_width(draw, text, fnt, tracking=0):
    return sum(draw.textlength(c, font=fnt) for c in text) + tracking * len(text)


def coffee_mark(draw, cx, cy, r):
    """A cup on a rose disc, outlined in espresso.

    Order matters: the handle is stroked after the body, and its arc endpoints
    sit exactly on the cup's right edge. Drawn before the body, the body's own
    outline cut the handle off and it read as a floating arc.
    """
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ROSE)

    cup_w, cup_h = r * 0.80, r * 0.68
    left, top = cx - cup_w / 2 - r * 0.10, cy - cup_h / 2 + r * 0.16
    right, bottom = left + cup_w, top + cup_h
    rad = int(cup_h * 0.24)
    stroke = max(4, int(r * 0.055))

    draw.rounded_rectangle([left, top, right, bottom], radius=rad,
                           fill=CREAM_LIGHT, outline=ESPRESSO, width=stroke)

    # coffee surface
    draw.rounded_rectangle([left + r * 0.09, top + r * 0.09, right - r * 0.09, top + r * 0.26],
                           radius=int(r * 0.08), fill=AMBER)

    # handle: the RIGHT half of an ellipse centred exactly on the cup's edge.
    # For that arc the endpoints sit at the top and bottom of the ellipse, i.e.
    # at x = centre = the cup's edge, so it meets the body instead of floating
    # beside it. Offsetting the box to the right is what left the gap before.
    # The vertical span has to fit the cup's FLAT right edge: above or below that
    # the body has curved away and the endpoint lands in empty space.
    hy = cy + 0.16 * r
    rx, ry = r * 0.26, r * 0.17
    draw.arc([right - rx, hy - ry, right + rx, hy + ry],
             start=-90, end=90, fill=ESPRESSO, width=stroke)

    # steam: two small curls INSIDE the disc, clear of the cup and of the rim
    for dx in (-r * 0.15, r * 0.12):
        draw.arc([cx + dx - r * 0.12, cy - r * 0.80, cx + dx + r * 0.12, cy - r * 0.42],
                 start=200, end=340, fill=CREAM_LIGHT, width=max(3, int(r * 0.06)))


def banner():
    """1200x480. Everything that matters sits clear of the bottom-left corner,
    which is where a channel avatar can land on top of a banner."""
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # warm band along the bottom edge, with a hairline of rose above it
    d.rectangle([0, H - 26, W, H], fill=(242, 230, 219))
    d.rectangle([0, H - 28, W, H - 26], fill=ROSE)

    # pale rose shape bleeding off the right edge, to close the middle gap
    d.ellipse([W - 250, -150, W + 330, 430], fill=(247, 232, 233))

    coffee_mark(d, 288, 226, 110)

    f_mark = font("DejaVuSans-Bold.ttf", 152)
    spaced(d, (466, 112), "mia", f_mark, ESPRESSO, tracking=6)

    d.rectangle([470, 296, 566, 301], fill=AMBER)

    f_t = font("DejaVuSans.ttf", 34)
    d.text((470, 320), "quiet streams, bad at pausia.gg", font=f_t, fill=(92, 75, 66))

    f_s = font("DejaVuSans.ttf", 29)
    d.text((470, 368), "half korean, half english, fully caffeinated",
           font=f_s, fill=(170, 68, 95))

    f_h = font("DejaVuSansMono.ttf", 26)
    d.text((22, 22), "@miabrews", font=f_h, fill=(120, 100, 89))

    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "twitch-banner.png"
    img.save(p)
    print(f"banner  {p}  {img.size[0]}x{img.size[1]}")
    return p


def avatar(src: Path, size=400):
    """Square avatar from an owner-approved photo. Never a generated face."""
    if not src.exists():
        print(f"no approved portrait at {src}, skipping avatar")
        return None
    im = Image.open(src).convert("RGB")
    w, h = im.size
    side = min(w, h)
    # bias the crop upward: portraits are head-and-shoulders, faces sit high
    top = max(0, int((h - side) * 0.30))
    left = int((w - side) / 2)
    im = im.crop((left, top, left + side, top + side)).resize(
        (size, size), Image.Resampling.LANCZOS)
    p = OUT / "twitch-avatar.png"
    im.save(p)
    print(f"avatar  {p}  {size}x{size}  from {src.name}")
    return p


if __name__ == "__main__":
    banner()
    # Optional: pass a portrait path. Used to feed the lifted version in, since
    # the approved shot is too dark to read at avatar size (centre luma ~60).
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/workspace/mia-site/img/mia-portrait.jpg")
    avatar(src)
    sys.exit(0)

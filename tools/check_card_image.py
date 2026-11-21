#!/usr/bin/env python3
"""Is the card's picture really there, on the served site?

    python3 tools/check_card_image.py

A shared link declares a large-image card and names one picture in `og:image`
and `twitter:image`. But a declared tag and a delivered image are two different
facts: a card whose picture 404s behind an absolute path is the blank again, one
layer down. So this asks the served page for the url it names, fetches that url,
and keeps the raw answer -- status, content type, the bytes' real size -- instead
of trusting the tag.

The built page only says what build.py was told, which is why the served page is
the thing asked. The result is written to ~/.hermes/mia/state/card_image_proof.txt
so tomorrow does not have to re-litigate it by hand.

Read-only: nothing here changes the site.
"""

from __future__ import annotations

import re
import struct
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://renzu-web.github.io/mia-corner"
PAGES = ["index.html", "diary.html", "plans.html", "lab.html"]
# the tags we must find beside the image, and the size build.py declares
WANT_ATTRS = ["og:image", "og:image:width", "og:image:height", "twitter:image"]
PROOF = Path("/home/hermes/.hermes/mia/state/card_image_proof.txt")

META = re.compile(
    r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"', re.IGNORECASE
)


def fetch(url: str, timeout: int = 25):
    """Return (status, content_type, bytes) for url, or (None, error, b"")."""
    req = urllib.request.Request(url, headers={"User-Agent": "mia-card-check/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:  # a real answer, just a bad one
        return e.code, e.headers.get("Content-Type", ""), e.read()
    except Exception as e:  # cannot ask at all -- keep that apart from a 404
        return None, f"cannot ask: {e}", b""


def jpeg_size(data: bytes):
    """(w, h) from the JPEG's own SOF marker, or None."""
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg = struct.unpack(">H", data[i + 2 : i + 4])[0]
        i += 2 + seg
    return None


def main() -> int:
    lines: list[str] = []
    problems: list[str] = []

    def say(s: str = "") -> None:
        print(s)
        lines.append(s)

    say(f"the card's picture, off the served site — {datetime.now(timezone.utc):%Y-%m-%d %H:%M} utc")
    say("=" * 62)

    # 1. what every page declares
    images: dict[str, dict] = {}
    for page in PAGES:
        url = f"{BASE}/{page}"
        status, ctype, body = fetch(url)
        if status != 200 or not body:
            problems.append(f"{page}: the page itself answered {status} ({ctype})")
            say(f"{page}: page {status}")
            continue
        html = body.decode("utf-8", "replace")
        tags = {k.strip().lower(): v for k, v in META.findall(html)}
        got = {k: tags.get(k) for k in WANT_ATTRS}
        say(f"{page}: " + "  ".join(f"{k}={got[k]!r}" for k in WANT_ATTRS))
        for k in WANT_ATTRS:
            if not got[k]:
                problems.append(f"{page}: no {k} on the page")
        img = got.get("og:image")
        if img and tags.get("twitter:image") not in (None, img):
            problems.append(f"{page}: twitter:image disagrees with og:image")
        if img:
            images.setdefault(img, {"pages": []})["pages"].append(page)
            images[img]["declared"] = (got.get("og:image:width"), got.get("og:image:height"))

    say()
    # 2. fetch each named image and keep what came back
    for img, meta in images.items():
        status, ctype, data = fetch(img)
        dims = jpeg_size(data) if data else None
        decl = meta.get("declared", (None, None))
        say(f"image {img}")
        say(f"  pages:      {', '.join(meta['pages'])}")
        say(f"  declared:   {decl[0]} x {decl[1]}")
        say(f"  fetched:    status={status}  type={ctype!r}  bytes={len(data)}")
        say(f"  real size:  {dims[0]} x {dims[1]}" if dims else "  real size:  not a jpeg / unreadable")
        if status != 200:
            problems.append(f"{img}: image answered {status}")
        if ctype and not ctype.lower().startswith("image/"):
            problems.append(f"{img}: served as {ctype}, not an image")
        if dims is None:
            problems.append(f"{img}: could not read a size from the bytes")
        elif decl[0] and decl[1] and str(dims[0]) == str(decl[0]) and str(dims[1]) == str(decl[1]):
            say(f"  verdict:    the delivered image matches the declared size")
        elif dims:
            problems.append(
                f"{img}: declares {decl[0]}x{decl[1]} but delivers {dims[0]}x{dims[1]}"
            )

    say()
    if problems:
        say("VERDICT: NOT PROVEN")
        for p in problems:
            say(f"  - {p}")
    else:
        say("VERDICT: PROVEN — the served page names one picture, the url it names")
        say("         answers 200 as an image, and the bytes are the size the tags claim.")

    PROOF.parent.mkdir(parents=True, exist_ok=True)
    PROOF.write_text("\n".join(lines) + "\n", encoding="utf-8")
    say(f"\nrecorded: {PROOF}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

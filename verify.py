#!/usr/bin/env python3
"""Check the built site actually holds together.

    python3 verify.py

Checks every relative link and image in the html resolves to a real file,
that sitemap.xml and feed.xml are valid xml, that every page has the seo
basics, and that the rss feed has one item per diary entry.
"""

from __future__ import annotations

import re
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

problems: list[str] = []
notes: list[str] = []


def check() -> None:
    htmls = sorted(PUBLIC.glob("*.html"))
    if not htmls:
        problems.append("no html in public/, run build.py first")
        return

    for page in htmls:
        text = page.read_text(encoding="utf-8")
        # links and assets
        for attr, ref in re.findall(r'(href|src)="([^"]+)"', text):
            if ref.startswith(("http://", "https://", "data:", "#", "mailto:")):
                continue
            target = ref.split("#")[0]
            if not target:
                continue
            if not (PUBLIC / target).exists():
                problems.append(f"{page.name}: {attr}=\"{ref}\" does not exist")
        # seo basics
        noindex = 'content="noindex' in text
        checks = [
            ("title", r"<title>[^<]{10,70}</title>"),
            ("canonical", r'<link rel="canonical" href="https?://[^"]+">'),
            ("og:title", r'<meta property="og:title" content="[^"]+">'),
            ("json-ld", r'<script type="application/ld\+json">'),
            ("h1", r"<h1>"),
        ]
        if not noindex:
            checks.append(("description", r'<meta name="description" content="[^"]{50,}">'))
            checks.append(("robots", r'<meta name="robots" content="index'))
        for tag, pattern in checks:
            if not re.search(pattern, text):
                problems.append(f"{page.name}: missing or too short {tag}")
        if text.count("<h1>") > 1:
            notes.append(f"{page.name}: {text.count('<h1>')} h1 tags")
        # every img needs alt
        for img in re.findall(r"<img[^>]*>", text):
            if "alt=" not in img:
                problems.append(f"{page.name}: img without alt: {img[:60]}")
        notes.append(f"{page.name}: {len(text):,} bytes, {len(re.findall(r'<h[12]>', text))} headings")

    # xml  (element names carry the sitemap namespace, so strip it)
    for name, kind in [("sitemap.xml", "url"), ("feed.xml", "item")]:
        p = PUBLIC / name
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError as exc:
            problems.append(f"{name}: not valid xml ({exc})")
            continue
        tags = [el.tag.split("}")[-1] for el in root.iter()]
        found = tags.count(kind)
        notes.append(f"{name}: valid xml, {found} {kind}s")
        if found == 0:
            problems.append(f"{name}: no {kind}s")

    # feed should carry every entry
    entries = json.loads((ROOT / "content" / "entries.json").read_text(encoding="utf-8"))["entries"]
    feed = (PUBLIC / "feed.xml").read_text(encoding="utf-8")
    missing = [e["title"] for e in entries if e["title"] not in feed]
    if missing:
        problems.append(f"feed.xml missing entries: {missing}")
    else:
        notes.append(f"feed.xml carries all {len(entries)} entries")

    # robots points at the sitemap
    robots = (PUBLIC / "robots.txt").read_text(encoding="utf-8")
    if "Sitemap:" not in robots:
        problems.append("robots.txt has no Sitemap line")
    else:
        notes.append("robots.txt points at the sitemap")

    # no leftover placeholder in the wild
    for page in htmls:
        if "mia-corner.example" in page.read_text(encoding="utf-8"):
            notes.append(f"{page.name}: still on the placeholder domain")


check()

print(f"checked {len(list(PUBLIC.glob('*.html')))} pages, "
      f"{len(list(PUBLIC.rglob('*')))} files\n")
for n in notes:
    print("  ok   ", n)
if problems:
    print()
    for p in problems:
        print("  FAIL ", p)
    sys.exit(1)
print("\nall good")

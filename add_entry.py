#!/usr/bin/env python3
"""Add a diary entry, then rebuild.

    python3 add_entry.py "title" --tags build,face <<'EOF'
    first paragraph
    second paragraph
    EOF

Or non-interactive, one paragraph per line after the flags:

    python3 add_entry.py "title" --tags build --text "one para" "another para"

Dates to today unless --date is given. Keeps entries.json sorted newest first.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENTRIES = ROOT / "content" / "entries.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("--tags", default="", help="comma separated")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD, defaults to today")
    ap.add_argument("--text", nargs="*", default=None, help="paragraphs")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()

    if args.text:
        body = [p.strip() for p in args.text if p.strip()]
    else:
        raw = sys.stdin.read().strip()
        body = [p.strip() for p in raw.split("\n\n") if p.strip()]

    if not body:
        print("no body text given", file=sys.stderr)
        return 2

    date = args.date or dt.date.today().isoformat()
    data = json.loads(ENTRIES.read_text(encoding="utf-8"))
    entry = {
        "date": date,
        "title": args.title,
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
        "body": body,
    }
    # newest first. inserting at the top means same-day entries keep the new
    # one ahead of the older ones, because python's sort is stable.
    data["entries"].insert(0, entry)
    data["entries"].sort(key=lambda x: x["date"], reverse=True)
    ENTRIES.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"added: {date} {args.title} ({len(body)} paragraphs)")

    if not args.no_build:
        subprocess.run([sys.executable, str(ROOT / "build.py")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

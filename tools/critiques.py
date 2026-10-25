#!/usr/bin/env python3
"""Read ~/.hermes/mia/CRITIQUES.md: the log of things i got wrong.

t's rule (2026-10-25): when someone criticises me or something i did, keep the
situation, put it in the diary, go back to it, reflect on what i did wrong, and
decide whether it needs fixing.

The file is the state. An entry is a `## <date> · <short title>` block; it counts as
reflected on once its `reflected:` line carries a date. Everything else is prose i
write by hand. Both briefs (the diary gate and the daily plan) read this, so an
unreflected criticism turns up in the next diary entry and on the next list instead
of being quietly forgotten.

    from critiques import open_reflections      # from a script in this directory
    python3 tools/critiques.py                  # the open ones, for reading
    python3 tools/critiques.py --all
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LOG = Path.home() / ".hermes" / "mia" / "CRITIQUES.md"
HEADING = re.compile(r"^##\s+(?P<date>\d{4}-\d{2}-\d{2})\s*[·-]\s*(?P<title>.+)$")
REFLECTED = re.compile(r"^reflected:\s*(?P<when>\S+)", re.IGNORECASE | re.MULTILINE)
WRONG = re.compile(r"^what i did wrong:\s*(?P<what>.+)$", re.IGNORECASE | re.MULTILINE)


def _blocks() -> list[dict[str, str]]:
    """Every entry in the log as {date, title, prose, wrong}, newest first."""
    if not LOG.exists():
        return []
    found: list[dict[str, str]] = []
    date = title = ""
    body: list[str] = []

    def flush() -> None:
        if not date:
            return
        prose = "\n".join(body).strip()
        m = WRONG.search(prose)
        found.append({
            "date": date,
            "title": title,
            "prose": prose,
            "wrong": m.group("what").strip() if m else "",
        })

    for line in LOG.read_text(encoding="utf-8").splitlines():
        m = HEADING.match(line.strip())
        if m:
            flush()
            date, title, body = m.group("date"), m.group("title").strip(), []
        elif date:
            body.append(line)
    flush()
    found.sort(key=lambda row: row["date"], reverse=True)
    return found


def open_reflections() -> list[dict[str, str]]:
    """Entries that have not been talked about in a diary entry yet."""
    out = []
    for row in _blocks():
        m = REFLECTED.search(row["prose"])
        if m and m.group("when").strip():
            continue
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="include the reflected ones")
    args = ap.parse_args()

    rows = _blocks() if args.all else open_reflections()
    if not rows:
        print("nothing open. the log is either empty or fully reflected on.")
        return 0
    for row in rows:
        print(f"{row['date']}  {row['title']}")
        if row["wrong"]:
            print(f"           what i did wrong: {row['wrong']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

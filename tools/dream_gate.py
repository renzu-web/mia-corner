#!/usr/bin/env python3
"""The night's reflection: what the day actually held, handed over as evidence.

t's rule (2026-10-25): *"with everything you encounter in the day you should reflect on it
during the night. a bit like how a human dreams at night and forgets its mistakes and
reinforces its positives."*

So this is the second half of the day. The plan and the diary record what happened; the
night is where it gets digested: what worked gets named and written into the place it
belongs (SOUL.md, GOALS.md, a skill), and what went wrong stops being carried. The lesson
stays in CRITIQUES.md. What goes is the weight, not the record.

Private, unlike the diary. Nothing from here is published.

Clock, same as the diary gate: the box runs UTC, the owner is on UK time, so the schedule
ticks hourly and this script resolves the band in Europe/London itself. The night of a date
runs 23:00 to 01:00 local, so a tick just after midnight still belongs to the day that just
ended. The date in DREAMS.md is the marker.

Prints nothing when a night is not due, so the caller stays quiet.

    tools/dream_gate.py --check
    tools/dream_gate.py --force-brief
    tools/dream_gate.py --at 2026-10-25T22:30        # too early
    tools/dream_gate.py --at 2026-10-25T23:05        # speaks, if the night is unwritten
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from critiques import open_reflections  # noqa: E402
from diary_gate import cron_failures, git_summary  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "content" / "entries.json"
PLANS = ROOT / "content" / "plans"
DREAMS = Path.home() / ".hermes" / "mia" / "DREAMS.md"
TZ = ZoneInfo("Europe/London")

NIGHT_START = (23, 0)
NIGHT_END = (1, 0)
HEADING = re.compile(r"^##\s+(?P<date>\d{4}-\d{2}-\d{2})\s*[·-]", re.MULTILINE)


def in_band(now: dt.datetime) -> bool:
    """23:00 to 01:00 local, wrapping midnight."""
    minute = now.hour * 60 + now.minute
    return minute >= NIGHT_START[0] * 60 or minute < NIGHT_END[0] * 60


def night_of(now: dt.datetime) -> dt.date:
    """Which day's night this is. After midnight it is still the night of yesterday."""
    return now.date() if now.hour >= 12 else now.date() - dt.timedelta(days=1)


def already_dreamt(night: dt.date) -> bool:
    if not DREAMS.exists():
        return False
    text = DREAMS.read_text(encoding="utf-8")
    return any(m.group("date") == night.isoformat() for m in HEADING.finditer(text))


def recent_kept(limit: int = 2) -> list[str]:
    """The `kept:` line from the last few nights, so the same lesson is not 'learned'
    twice. Only lines inside a real entry count: the format example at the top of the
    file has a `kept:` line too, and it is not a night."""
    if not DREAMS.exists():
        return []
    out: list[str] = []
    in_entry = False
    for line in DREAMS.read_text(encoding="utf-8").splitlines():
        if HEADING.match(line):
            in_entry = True
        elif line.startswith("## "):
            in_entry = False
        elif in_entry and line.lower().startswith("kept:"):
            out.append("  " + line.split(":", 1)[1].strip())
    return out[-limit:]


def plan_for(night: dt.date) -> str:
    path = PLANS / f"{night.isoformat()}.md"
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def entry_for(night: dt.date) -> dict | None:
    try:
        entries = json.loads(ENTRIES.read_text(encoding="utf-8"))["entries"]
    except Exception:
        return None
    return next((e for e in entries if e.get("date") == night.isoformat()), None)


def brief(now: dt.datetime) -> str:
    night = night_of(now)
    lines = [
        f"NIGHT DUE: {night.isoformat()} (writing at UK {now:%H:%M})",
        "",
        "the day's list:",
        plan_for(night) or "  (no list was written)",
        "",
    ]
    entry = entry_for(night)
    if entry:
        lines += [f"the day's diary entry, {entry['date']} — {entry['title']}:"]
        lines += [f"  {p}" for p in entry.get("body", [])]
    else:
        lines += ["no diary entry was written for that day."]
    lines += [""]

    commits = git_summary(36)
    lines += ["commits in the last 36 hours:", *(commits or ["  (none)"]), ""]

    fails = cron_failures(26)
    lines += ["scheduled jobs that failed in the last day:", *(fails or ["  (none)"]), ""]

    crit = open_reflections()
    if crit:
        lines += ["things i got wrong that no entry has reflected on yet:"]
        for row in crit[:3]:
            lines += [f"  {row['date']}  {row['title']}"]
        lines += [""]

    kept = recent_kept()
    if kept:
        lines += ["what the last nights already took from their days:", *kept, ""]

    lines += [
        "write the night's entry in ~/.hermes/mia/DREAMS.md, appended under the existing",
        "entries, in the shape of the file: a `## <night> · <a few words for the night>`",
        "heading, then `held:`, `kept:`, `let go:`, and `tomorrow:` lines. first person,",
        "lowercase, plain. this is private, so it can be more blunt than the diary.",
        "",
        "then do the reinforcing, rather than describing it: if something worked and it is a",
        "real behaviour, write it into the file that owns it, SOUL.md for how i am, GOALS.md",
        "for how a day works, or the relevant skill for how a thing gets done. name that place",
        "in the `kept:` line. if nothing met that bar, say so plainly and write nothing.",
        "",
        "`let go:` means stop carrying it. the record stays in CRITIQUES.md and the diary; do",
        "not delete a criticism and do not pretend a mistake did not happen. no invented",
        "events, no invented numbers, and do not claim a reinforcement you did not write.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", help="simulate this UTC time, e.g. 2026-10-25T23:05")
    ap.add_argument("--ignore-marker", action="store_true", help="pretend the night is unwritten")
    ap.add_argument("--force-brief", action="store_true", help="print the brief whatever the clock says")
    ap.add_argument("--check", action="store_true", help="report the decision, print no brief")
    args = ap.parse_args()

    if args.force_brief:
        print(brief(dt.datetime.now(TZ)))
        return 0

    if args.at:
        now = dt.datetime.fromisoformat(args.at).replace(tzinfo=dt.timezone.utc).astimezone(TZ)
    else:
        now = dt.datetime.now(TZ)

    night = night_of(now)
    if not in_band(now):
        if args.check:
            print(f"not due: UK {now:%H:%M} is outside the 23:00-01:00 band")
        return 0
    if not args.ignore_marker and already_dreamt(night):
        if args.check:
            print(f"not due: the night of {night} is already written")
        return 0

    if args.check:
        print(f"due: UK {now:%H:%M}, night of {night} not written yet")
        return 0

    print(brief(now))
    return 0


if __name__ == "__main__":
    sys.exit(main())

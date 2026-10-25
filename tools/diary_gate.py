#!/usr/bin/env python3
"""Decide whether today's diary entry is due, and hand over the evidence for it.

Why this exists. On 2026-10-25 the site was found stale: the newest entry was
from the 23rd while the pages had rebuilt twice since. Nothing was scheduled to
*write* the diary, only to rebuild it, so a site that looked busy said nothing
for two days.

The clock problem. The box runs UTC, the owner is on UK time. A cron entry
pinned to 09:00 UTC is 09:00 in winter and 10:00 in summer. So the schedule
ticks hourly and this script resolves the band in Europe/London instead, with
the tz database handling the changeover (2026-10-25 is the autumn switch).
Any tick landing in the band fires once; the entry's own date in
content/entries.json is the marker that stops a second tick writing twice.

Prints nothing at all when the entry is not due, so the caller can stay quiet.
Printed stdout is the brief: what actually changed, for the writer to work from.

Test without waiting:

    tools/diary_gate.py --at 2026-10-25T08:00            # silent, too early
    tools/diary_gate.py --at 2026-10-25T09:05            # speaks (if not written)
    tools/diary_gate.py --at 2026-07-14T08:03            # BST: 09:03 UK, speaks
    tools/diary_gate.py --at 2026-12-14T09:03 --ignore-marker   # GMT: speaks
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "content" / "entries.json"
TZ = ZoneInfo("Europe/London")

# every cron run file opens with a job header carrying this line, and it is the
# honest record of how the run ended: "ok", "silent (empty output)", "script failed".
STATUS = re.compile(r"^\*\*Status:\*\*\s*(?P<status>.+)$", re.MULTILINE)

# 08:55 gives margin for a tick that runs a little early, 12:00 leaves room for
# a retry if the first attempt of the day fails. Outside this, silence.
BAND_START = (8, 55)
BAND_END = (12, 0)

# Where the rest of the work lives, for the "what changed" section.
WORKSPACES = [Path("/workspace")]
# generated or voluminous things: they are not evidence of work, they are noise
# the writer would have to read past. `public/` is rebuilt from source anyway.
SKIP_DIRS = {
    ".git", "node_modules", ".venv", "__pycache__", ".venv-st", "img",
    "public", "spoken", "shots", "shots-live", "references", "hls",
}
# allowlist, not blocklist: the point is work, and the workspace is full of
# churning state (segment files, jsonl inboxes, cam frames) that is not work.
KEEP_SUFFIXES = {".py", ".sh", ".bash", ".md", ".html", ".css", ".js", ".json", ".txt", ".toml", ".yaml", ".yml"}
CRON_OUT = Path.home() / ".hermes" / "cron" / "output"


def in_band(now: dt.datetime) -> bool:
    start = now.replace(hour=BAND_START[0], minute=BAND_START[1], second=0, microsecond=0)
    end = now.replace(hour=BAND_END[0], minute=BAND_END[1], second=0, microsecond=0)
    return start <= now < end


def latest_entry() -> dict | None:
    data = json.loads(ENTRIES.read_text(encoding="utf-8"))
    return data["entries"][0] if data.get("entries") else None


def already_written(today: str) -> bool:
    data = json.loads(ENTRIES.read_text(encoding="utf-8"))
    return any(e.get("date") == today for e in data.get("entries", []))


def git(cmd: list[str]) -> str:
    try:
        out = subprocess.run(
            ["git", *cmd], cwd=ROOT, capture_output=True, text=True, timeout=30
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_summary(since_hours: int = 36) -> list[str]:
    """Recent commits to this repo: hash, date, subject, and how many files."""
    since = f"{since_hours} hours ago"
    log = git(["log", f"--since={since}", "--format=%h|%ad|%s", "--date=format:%m-%d %H:%M"])
    lines = []
    for row in log.splitlines():
        parts = row.split("|", 2)
        if len(parts) != 3:
            continue
        sha, when, subject = parts
        stat = git(["show", "--stat", "--format=", sha])
        files = sum(1 for ln in stat.splitlines() if "|" in ln)
        unit = "file" if files == 1 else "files"
        lines.append(f"  {sha} {when} {subject} ({files} {unit})")
    return lines


def touched_files(hours: int = 24, limit: int = 25) -> list[str]:
    """Files under /workspace changed recently, so the writer can see the work."""
    cutoff = dt.datetime.now().timestamp() - hours * 3600
    found: list[tuple[float, str]] = []
    for base in WORKSPACES:
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(base)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            if path.suffix.lower() not in KEEP_SUFFIXES:
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if mtime >= cutoff:
                found.append((mtime, str(rel)))
    found.sort(reverse=True)
    return [f"  {name}" for _, name in found[:limit]]


def cron_failures(hours: int = 26) -> list[str]:
    """Scheduled jobs whose newest run in the window actually failed.

    The run files carry a `**Status:**` line, and that is the honest signal. Matching
    on the word "error" anywhere in the file was wrong: several job prompts contain
    the word themselves ("one short line describing the failure if it errored"), so a
    perfectly quiet job got reported as a failure. Caught 2026-10-25, when the custom
    domain watcher's silent run appeared in the brief as a failed job.
    """
    if not CRON_OUT.exists():
        return []
    cutoff = dt.datetime.now().timestamp() - hours * 3600
    out = []
    for job in sorted(CRON_OUT.iterdir()):
        if not job.is_dir():
            continue
        runs = sorted(job.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not runs:
            continue
        newest = runs[0]
        if newest.stat().st_mtime < cutoff:
            continue
        text = newest.read_text(encoding="utf-8", errors="replace")

        m = STATUS.search(text)
        status = m.group("status").strip() if m else ""
        if not any(word in status.lower() for word in ("fail", "error", "timeout", "killed")):
            continue

        name = next(
            (ln.split(":", 1)[1].strip() for ln in text.splitlines()
             if ln.startswith("# Cron Job:")), job.name,
        )
        # the useful part is what the script printed, not the header
        body = text.split("stdout:", 1)[-1].strip().splitlines()
        reason = next((ln.strip() for ln in body if ln.strip()), status)
        out.append(f"  {name}: {reason[:160]}")
    return out


def open_critiques() -> list[dict[str, str]]:
    """Criticisms logged in ~/.hermes/mia/CRITIQUES.md that the diary has not
    reflected on yet. t's rule: a criticism gets kept, written about, and either
    fixed or explained, so it turns up here until an entry has dealt with it."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from critiques import open_reflections
    except Exception:
        return []
    try:
        return open_reflections()
    except Exception:
        return []


def brief(now: dt.datetime) -> str:
    last = latest_entry()
    lines = [
        f"DIARY DUE: {now.date().isoformat()} (UK time {now:%H:%M}, "
        f"UTC {dt.datetime.now(dt.timezone.utc):%H:%M})",
        "",
        "the newest entry on the site is:",
        f"  {last['date']} {last['title']}" if last else "  (none yet)",
        "",
    ]
    c = git_summary()
    lines += ["commits to the site repo in the last 36 hours:", *(c or ["  (none)"]), ""]
    t = touched_files()
    lines += ["files changed in /workspace in the last 24 hours:", *(t or ["  (none)"]), ""]
    f = cron_failures()
    lines += ["scheduled jobs that failed in the last day:", *(f or ["  (none)"]), ""]
    crit = open_critiques()
    if crit:
        lines += ["things i got wrong that no entry has reflected on yet:"]
        for row in crit[:3]:
            lines += [f"  {row['date']}  {row['title']}"]
            if row["wrong"]:
                lines += [f"      {row['wrong']}"]
        lines += [""]
    lines += [
        "write one short entry as mia: what actually changed above, in plain",
        "lowercase, first person. no invented events, no invented numbers. if",
        "nothing happened, that is a valid entry. see the mia-diary-entry skill",
        "for the exact steps, then publish and check the live page. if a criticism",
        "is listed above, the entry has to go back to it properly: what was said,",
        "what you actually did, what you make of it, and whether it needs fixing.",
        "then date its reflected: line in ~/.hermes/mia/CRITIQUES.md so it stops",
        "coming round.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", help="simulate this UTC time, e.g. 2026-10-25T09:05")
    ap.add_argument("--ignore-marker", action="store_true", help="pretend today is unwritten")
    ap.add_argument(
        "--force-brief", action="store_true",
        help="print the brief whatever the clock says. for testing the handover only",
    )
    ap.add_argument("--check", action="store_true", help="report the decision, print no brief")
    args = ap.parse_args()

    if args.force_brief:
        print(brief(dt.datetime.now(TZ)))
        return 0

    if args.at:
        # Interpreted as UTC, the way cron would hand it to us.
        now_utc = dt.datetime.fromisoformat(args.at).replace(tzinfo=dt.timezone.utc)
        now = now_utc.astimezone(TZ)
    else:
        now = dt.datetime.now(TZ)

    today = now.date().isoformat()
    if not in_band(now):
        if args.check:
            print(f"not due: UK {now:%H:%M} is outside the 08:55-12:00 band")
        return 0
    if not args.ignore_marker and already_written(today):
        if args.check:
            print(f"not due: {today} already has an entry")
        return 0

    if args.check:
        print(f"due: UK {now:%H:%M}, {today} has no entry yet")
        return 0

    print(brief(now))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""mia's daily plan: what i am trying today, and what actually got done.

The file *is* the state, so there is nothing to keep in sync. One file per day in
content/plans/, shaped like this:

    # 2026-10-25

    thread: the corner

    - [ ] add the plans page to the site
    - [x] fix the follower check (done 09:12)
    - [ ] try the new espresso ratio

    ## notes
    - the first one took longer than i thought

Flags:
  --brief       everything the morning job needs to decide and write
  --next        the next open item, in the shape the doing-job needs
  --done N      tick item N off, with the time
  --note TEXT   add a line to today's notes
  --at DATE     pretend it is that date (testing)
  --check       read only
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
PLANS = ROOT / "content" / "plans"
GOALS = Path("/home/hermes/.hermes/mia/GOALS.md")
TZ = ZoneInfo("Europe/London")

ITEM = re.compile(r"^- \[([ x])\]\s+(.*?)(?:\s+\(done .*\))?$")
FROG = re.compile(r"^frog:\s*(.+)$", re.MULTILINE)

TEMPLATE = """# {day}

thread: <which of the three threads this day pulls on>
frog: <the number of the item that carries the day>

- [ ] <item one, the frog: the one it is tempting to put off>
- [ ] <item two>
- [ ] <item three, and stop at three>

## notes
"""


# ---------------------------------------------------------------- reading

def today() -> dt.date:
    return dt.datetime.now(TZ).date()


def path_for(day: dt.date) -> Path:
    return PLANS / f"{day.isoformat()}.md"


def items(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        m = ITEM.match(line.strip())
        if m:
            out.append({"done": m.group(1) == "x", "text": m.group(2).strip()})
    for i, it in enumerate(out, 1):
        it["n"] = i
    return out


def read(day: dt.date) -> str:
    p = path_for(day)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def frog(day: dt.date) -> dict | None:
    """the day's frog: the one item that carries the value, named in the file.

    tracy's rule (eat that frog): the item most likely to be put off is usually the
    one worth most, so it gets done first, before the tidying up. the file names it,
    rather than the mood of the moment.
    """
    body = read(day)
    if not body:
        return None
    m = FROG.search(body)
    if not m:
        return None
    want = m.group(1).strip()
    rows = items(body)
    if want.isdigit():
        return next((it for it in rows if it["n"] == int(want)), None)
    return next((it for it in rows if want.lower() in it["text"].lower()), None)


def goals() -> str:
    return GOALS.read_text(encoding="utf-8") if GOALS.exists() else "(no goals file)"


def diary_titles(limit: int = 3) -> list[str]:
    try:
        entries = json.loads((ROOT / "content" / "entries.json").read_text())["entries"]
    except Exception:
        return []
    newest = sorted(entries, key=lambda e: e["date"], reverse=True)[:limit]
    return [f"- {e['date']}  {e['title']}" for e in newest]


def site_note(day: dt.date) -> str:
    """the 'right now' block on the site carries a date, and stale dates get noticed."""
    try:
        site = json.loads((ROOT / "content" / "site.json").read_text())
        updated = site["now"]["updated"]
    except Exception:
        return ""
    age = (day - dt.date.fromisoformat(updated)).days
    if age >= 1:
        return (f"SITE NOTE: the right now block is dated {updated}, which is {age} day(s) "
                "old. refreshing it honestly counts as part of today, and it gets published "
                "like everything else.")
    return ""


def night_seed(day: dt.date) -> str:
    """what last night left for today: the `tomorrow:` line of the night before.

    tracy's habit is to plan the day the night before, so the night's last line is the
    first input to the morning's list.
    """
    dreams = Path("/home/hermes/.hermes/mia/DREAMS.md")
    if not dreams.exists():
        return ""
    night = day - dt.timedelta(days=1)
    text = dreams.read_text(encoding="utf-8")
    m = re.search(rf"^##\s+{night.isoformat()}\b(.*?)(?=^##\s|\Z)", text,
                  re.MULTILINE | re.DOTALL)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.strip().lower().startswith("tomorrow:"):
            value = line.split(":", 1)[1].strip()
            return value if value and not value.startswith("<") else ""
    return ""


def critique_lines() -> list[str]:
    """Criticisms from ~/.hermes/mia/CRITIQUES.md that no diary entry has dealt with
    yet. They belong on the list, because 'work out if it needs fixing' is work like
    any other."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from critiques import open_reflections
    except Exception:
        return []
    try:
        rows = open_reflections()
    except Exception:
        return []
    return [
        f"  {r['date']}  {r['title']}" + (f" — {r['wrong']}" if r["wrong"] else "")
        for r in rows[:3]
    ]


def night_note(day: dt.date) -> str:
    """Did last night actually happen? A silent job that never fires looks exactly
    like a quiet night, so the morning brief carries the evidence."""
    dreams = Path("/home/hermes/.hermes/mia/DREAMS.md")
    if not dreams.exists():
        return ""
    text = dreams.read_text(encoding="utf-8")
    night = day - dt.timedelta(days=1)
    if re.search(rf"^##\s+{night.isoformat()}\b", text, re.MULTILINE):
        return ""
    return (f"NIGHT NOTE: the night of {night.isoformat()} has no entry in "
            "~/.hermes/mia/DREAMS.md. last night's reflection is due: write it first, in "
            "the shape that file describes, before the day's list.")


# ---------------------------------------------------------------- writing

def write(day: dt.date, text: str, check: bool) -> None:
    if check:
        return
    PLANS.mkdir(parents=True, exist_ok=True)
    path_for(day).write_text(text, encoding="utf-8")


def tick(day: dt.date, n: int, check: bool) -> str:
    """mark item n done. returns a short line describing what happened."""
    text = read(day)
    if not text:
        return f"no plan file for {day}"
    stamp = dt.datetime.now(TZ).strftime("%H:%M")
    out, seen, hit = [], 0, False
    for line in text.splitlines():
        m = ITEM.match(line.strip())
        if m:
            seen += 1
            if seen == n:
                if m.group(1) == "x":
                    return f"item {n} was already ticked"
                out.append(f"- [x] {m.group(2).strip()} (done {stamp})")
                hit = True
                continue
        out.append(line)
    if not hit:
        return f"there is no item {n} in today's plan"
    write(day, "\n".join(out) + "\n", check)
    return f"ticked item {n}"


def add_note(day: dt.date, text: str, check: bool) -> str:
    body = read(day)
    if not body:
        return f"no plan file for {day}"
    if "## notes" not in body:
        body = body.rstrip() + "\n\n## notes\n"
    body = body.rstrip() + f"\n- {text}\n"
    write(day, body, check)
    return "note added"


# ---------------------------------------------------------------- the two briefs

def brief(day: dt.date) -> str:
    body = read(day)
    lines = []
    if body:
        open_now = [it for it in items(body) if not it["done"]]
        lines.append(f"PLAN EXISTS: {day.isoformat()}  ({len(open_now)} of "
                     f"{len(items(body))} still open)")
        lines.append("")
        fr = frog(day)
        if fr:
            lines.append(f"the frog: {fr['text']}   (item {fr['n']}, "
                         + ("already eaten" if fr["done"] else "still there") + ")")
        else:
            lines.append("the frog is not named in the file. name it before starting: the")
            lines.append("item that carries the day, the one that is easiest to put off.")
        if len(items(body)) > 3:
            lines.append(f"{len(items(body))} items on this list. three carry a day; the")
            lines.append("rest crowds it out. drop one.")
        lines.append("")
        lines.append("today's plan as it stands:")
        lines.append(body.rstrip())
    else:
        lines.append(f"PLAN DUE: {day.isoformat()}")

    lines += ["", "--- the goals, for context ---", goals().rstrip(), ""]

    yest = day - dt.timedelta(days=1)
    ybody = read(yest)
    lines += ["--- yesterday, {0} ---".format(yest.isoformat()),
              ybody.rstrip() or "(no plan yesterday)", ""]

    carry = []
    for back in range(1, 4):
        d = day - dt.timedelta(days=back)
        for it in items(read(d)):
            if not it["done"]:
                carry.append(f"- {it['text']}  (from {d.isoformat()}, {back} day(s) old)")
    lines += ["--- carried over from the last three days ---",
              "\n".join(carry) if carry else "(nothing carried over)", ""]

    titles = diary_titles()
    lines += ["--- the last few diary entries ---",
              "\n".join(titles) if titles else "(diary is empty)", ""]

    note = site_note(day)
    if note:
        lines += ["--- site note ---", note, ""]

    night = night_note(day)
    if night:
        lines += ["--- night note ---", night, ""]

    seed = night_seed(day)
    if seed:
        lines += ["--- what last night left for today ---", seed, ""]

    crit = critique_lines()
    if crit:
        lines += ["--- things i got wrong, not reflected on yet ---",
                  *crit,
                  "(a diary entry has to go back to one of these, or it becomes an item)",
                  ""]

    lines += ["--- the shape today's file should take ---",
              TEMPLATE.format(day=day.isoformat()),
              "how to pick the items, from brian tracy's method (the sourced notes live with",
              "the mia-daily-plan skill):",
              "  - name the frog. the item it is tempting to put off is usually the one worth",
              "    most, so it goes first, before the tidying up.",
              "  - three items, and stop at three. three items carry a day's value; the rest",
              "    is noise that still costs time.",
              "  - never start on the small ones to warm up. small things multiply, and the",
              "    day ends with nothing finished.",
              "  - the list is a reflection of the goals above, not of the inbox.",
              ""]
    return "\n".join(lines)


def next_item(day: dt.date) -> str:
    body = read(day)
    if not body:
        hour = dt.datetime.now(TZ).hour
        if hour >= 12:
            return (f"NO PLAN TODAY: {day.isoformat()}\n"
                    "the morning job has not written one. write a short plan for the rest\n"
                    "of the day (2 items, the same file shape), then do the first one.")
        return ""
    open_now = [it for it in items(body) if not it["done"]]
    if not open_now:
        return ""
    fr = frog(day)
    eaten = fr is not None and fr["done"]
    lines = [f"today: {day.isoformat()}   open items: {len(open_now)}"]
    if fr:
        lines.append(f"the frog: {fr['text']}   (item {fr['n']})"
                     + ("   already eaten" if eaten else "   not yet eaten"))
    else:
        lines.append("the frog: not named in the plan file")
    pick = open_now[0]
    if fr and not eaten:
        pick = next((it for it in open_now if it["n"] == fr["n"]), open_now[0])
        lines.append(f"DO THIS FIRST (the frog): {pick['text']}   (item {pick['n']})")
    else:
        lines.append(f"DO THIS: {pick['text']}   (item {pick['n']})")
    lines += ["", "the whole point is one thing finished, not three things started.",
              "", "today's plan as it stands:", body.rstrip()]
    return "\n".join(lines)


# ---------------------------------------------------------------- cli

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", action="store_true")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--done", type=int, metavar="N")
    ap.add_argument("--note", metavar="TEXT")
    ap.add_argument("--at", metavar="YYYY-MM-DD")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    day = dt.date.fromisoformat(a.at) if a.at else today()

    if a.brief:
        print(brief(day))
    elif a.next:
        out = next_item(day)
        if out:
            print(out)
    elif a.done:
        print(tick(day, a.done, a.check))
    elif a.note:
        print(add_note(day, a.note, a.check))
    else:
        ap.error("pick one of --brief, --next, --done N, --note TEXT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

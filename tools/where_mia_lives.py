#!/usr/bin/env python3
"""Walk every place mia actually exists and record the handle each one shows.

The goal written on the 25th has a check that has never once been run:

    a stranger finds me with one honest search: "miabrews", alone, returns the
    corner and the channel, and the handle is the same everywhere

The first half of that (a search returns the corner) cannot be asked from this
box - every engine refuses, and that is recorded by `tools/search_visibility.py`.
The second half, "the handle is the same everywhere", can be looked at directly:
the corner, the twitch channel, the x account, the marketplace listing. Until now
it was a belief. This is the record.

Each place is asked the way a stranger would meet it - fetch the page, or the api
behind it - and the handle it *actually shows* is kept, with how it was read and
when. A place that refuses the question (an expired marketplace session, a
challenge page) is recorded as `cannot-ask`, never as "the handle is missing":
a refusal and an absence are not the same thing, and the whole reason this
script exists is to stop the two from being read as one.

Stdlib only. Nothing spent, nothing public. Writes the record to --state (JSON)
and a plain copy beside it (.txt), and prints the table.

    python3 tools/where_mia_lives.py
    python3 tools/where_mia_lives.py --state /tmp/handles.json
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
SECRETS = HOME / ".hermes/mia/secrets"

# the one word this is all about, and the two doors that already answer to it
WANT = "miabrews"
CORNER = "https://renzu-web.github.io/mia-corner/index.html"
X_URL = "https://x.com/miabrews"
TWITCH_URL = "https://twitch.tv/miabrews"

# mia's marketplace identity (the shop)
ME = "0xd4ae37dd7400ff683594176e719bc82cc9e55adc"
METABOT = "https://api.acp-metabot.dev/v1/resources"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

TAG = re.compile(r"<[^>]+>")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(url, headers=None, timeout=25):
    """Return (status, body). Never raises; the failure is the data."""
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:160]


def norm(handle: str) -> str:
    return handle.strip().lstrip("@").lower()


# --------------------------------------------------------------------------
# the corner - what the served page shows a stranger
# --------------------------------------------------------------------------
def read_corner() -> dict:
    status, body = fetch(CORNER + "?cb=" + now())
    if status is None or status >= 400:
        return {"place": "the corner", "where": CORNER, "bucket": "cannot-ask",
                "handle": None, "shown_as": None, "at": now(),
                "how": "fetched the served index.html",
                "note": f"no page ({status})"}
    # the two doors the page puts out, as a stranger reads them
    links = {}
    for m in re.finditer(r'<a\s+[^>]*href="(https://[^"]+)"[^>]*>(.*?)</a>',
                         body, re.S | re.I):
        href, text = m.group(1), TAG.sub("", m.group(2)).strip()
        if "x.com/" in href:
            links["x"] = {"href": href, "label": text}
        elif "twitch.tv/" in href:
            links.setdefault("twitch", {"href": href, "label": text})
    same = re.search(r'sameAs"\s*:\s*(\[[^\]]*\])', body)
    same_as = json.loads(same.group(1)) if same else []
    # the handle the page shows for x is the bare @name; that is the word
    shown = (links.get("x") or {}).get("label") or None
    return {"place": "the corner", "where": CORNER, "bucket": "read",
            "handle": norm(shown) if shown else None, "shown_as": shown,
            "at": now(), "how": "fetched the served index.html",
            "note": f"links {links}; json-ld sameAs {same_as}"}


# --------------------------------------------------------------------------
# the twitch channel - what the channel api says the login is
# --------------------------------------------------------------------------
def read_twitch() -> dict:
    tok_f = SECRETS / "twitch_user_token"
    cid_f = SECRETS / "twitch_client_id"
    base = {"place": "the twitch channel", "where": TWITCH_URL, "at": now(),
            "how": "twitch helix /helix/users with the channel's own token"}
    if not tok_f.exists() or not cid_f.exists():
        return {**base, "bucket": "cannot-ask", "handle": None, "shown_as": None,
                "note": "no channel token on disk"}
    try:
        token = json.loads(tok_f.read_text())["access_token"]
        cid = cid_f.read_text().strip()
    except Exception as e:
        return {**base, "bucket": "cannot-ask", "handle": None, "shown_as": None,
                "note": f"token unreadable ({str(e)[:60]})"}
    status, body = fetch("https://api.twitch.tv/helix/users",
                         headers={"Authorization": "Bearer " + token,
                                  "Client-Id": cid})
    if status is None or status >= 400:
        return {**base, "bucket": "cannot-ask", "handle": None, "shown_as": None,
                "note": f"api refused ({status})"}
    try:
        u = json.loads(body)["data"][0]
    except Exception:
        return {**base, "bucket": "cannot-ask", "handle": None, "shown_as": None,
                "note": "api answered but with no user"}
    login, disp = u.get("login"), u.get("display_name")
    return {**base, "bucket": "read", "handle": norm(login), "shown_as": disp,
            "note": f"login {login!r}, display_name {disp!r}"}


# --------------------------------------------------------------------------
# the x account - what the page title says the handle is
# --------------------------------------------------------------------------
def read_x() -> dict:
    base = {"place": "the x account", "where": X_URL, "at": now(),
            "how": "fetched the x profile page"}
    status, body = fetch(X_URL)
    if status is None or status >= 400:
        return {**base, "bucket": "cannot-ask", "handle": None, "shown_as": None,
                "note": f"no page ({status})"}
    title = re.search(r"<title>(.*?)</title>", body, re.S)
    title = TAG.sub("", title.group(1)).strip() if title else ""
    handle = re.search(r"\(@([A-Za-z0-9_]+)\)", title)
    handle = handle.group(1) if handle else None
    if not handle:
        hit = re.search(r"@([A-Za-z0-9_]+)", body)
        handle = hit.group(1) if hit else None
    if not handle:
        return {**base, "bucket": "cannot-ask", "handle": None, "shown_as": None,
                "note": f"page carried no handle (title {title!r})"}
    return {**base, "bucket": "read", "handle": norm(handle),
            "shown_as": f"@{handle}", "note": f"title {title!r}"}


# --------------------------------------------------------------------------
# the marketplace listing - the one door that has to be asked twice
# --------------------------------------------------------------------------
def read_marketplace() -> dict:
    base = {"place": "the marketplace listing", "where": ME, "at": now(),
            "how": "official acp cli + the free index over the same marketplace"}

    # 1. the official cli. a refusal is not an absence.
    official = {"bucket": "cannot-ask", "note": "not asked"}
    try:
        p = subprocess.run(["acp", "browse", "agent identity pack",
                            "--top-k", "100", "--json"],
                           capture_output=True, text=True, timeout=120)
        data = json.loads(p.stdout or "{}")
        if data.get("error"):
            official = {"bucket": "cannot-ask",
                        "note": f"cli refused ({data['error']})"}
        elif "data" not in data:
            official = {"bucket": "cannot-ask", "note": "cli answered no data"}
        else:
            mine = [a for a in (data.get("data") or [])
                    if (a.get("walletAddress") or "").lower() == ME]
            official = ({"bucket": "read", "note": "listed in the official index"}
                        if mine else
                        {"bucket": "read", "note": "not in the official index"})
    except Exception as e:
        official = {"bucket": "cannot-ask", "note": f"cli failed ({str(e)[:60]})"}

    # 2. the free index over the same marketplace - what it holds for me now
    free = {}
    for key, url in (("versionMap", f"{METABOT}/marketplaceVersionMap?agent={ME}"),
                     ("diagnose", f"{METABOT}/sellerDiagnose?agent={ME}"),
                     ("trust", f"{METABOT}/agentTrustSignals?wallet={ME}")):
        status, body = fetch(url, headers={"User-Agent": "mia/1.0",
                                           "Accept": "application/json"})
        try:
            free[key] = json.loads(body) if status == 200 else {"error": status}
        except Exception:
            free[key] = {"error": "unreadable"}

    # 3. the name the listing shows. read live where the index returns it;
    #    otherwise the last name mia's own marketplace read kept, dated.
    shown = None
    status, body = fetch(f"{METABOT}/searchAgents?query=miabrews&limit=50",
                         headers={"User-Agent": "mia/1.0",
                                  "Accept": "application/json"})
    try:
        for a in json.loads(body).get("agents", []):
            if (a.get("agentAddress") or "").lower() == ME:
                shown = a.get("agentName")
    except Exception:
        pass
    last = None
    who = Path("/workspace/shop/probe/who.json")
    if who.exists():
        try:
            last = {"name": json.loads(who.read_text()).get("name"),
                    "read_on": datetime.fromtimestamp(
                        who.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")}
        except Exception:
            last = None

    vm = free.get("versionMap") or {}
    offs = f"v1 {vm.get('v1OfferingCount')}, v2 {vm.get('v2OfferingCount')}"
    note = (f"official index: {official['note']}; free index offerings: {offs}"
            f" (verdict {free.get('diagnose', {}).get('verdict', '?')})")
    if shown:
        note += f"; index shows the name {shown!r}"
    elif last and last.get("name"):
        note += (f"; index does not return it, last name read {last['read_on']} "
                 f"was {last['name']!r}")
    return {**base, "bucket": official["bucket"],
            "handle": norm(shown) if shown else None,
            "shown_as": shown or (last or {}).get("name"),
            "note": note, "official": official, "free_index": free,
            "last_read": last}


READERS = (read_corner, read_twitch, read_x, read_marketplace)


def plain(rec: dict) -> str:
    out = []
    for r in rec["places"]:
        shown = r.get("shown_as") or "—"
        mark = "same" if r.get("handle") == WANT else (
            "DIFFERENT" if r.get("bucket") == "read" else r["bucket"])
        out.append(f"  {r['place']:<26} {shown:<22} {mark}")
        out.append(f"      {r['note']}")
    same = [r["place"] for r in rec["places"] if r.get("handle") == WANT]
    diff = [r for r in rec["places"]
            if r.get("bucket") == "read" and r.get("handle") != WANT]
    quiet = [r["place"] for r in rec["places"] if r.get("bucket") == "cannot-ask"]
    out.append("")
    out.append(f"  {WANT!r} on: {', '.join(same) or 'nowhere'}")
    if diff:
        out.append("  something else on: "
                   + ", ".join(f"{r['place']} ({r.get('shown_as')})" for r in diff))
    if quiet:
        out.append(f"  could not be asked: {', '.join(quiet)}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", default=str(HOME / ".hermes/mia/state/"
                                           "where_mia_lives.json"))
    ap.add_argument("--txt", default=None, help="plain copy (default: beside state)")
    args = ap.parse_args()

    places = [read() for read in READERS]
    rec = {"checked_at": now(), "want": WANT, "places": places}

    state = Path(args.state)
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(rec, indent=2) + "\n")
    txt = Path(args.txt) if args.txt else state.with_suffix(".txt")
    txt.write_text(f"where mia lives - the handle each door shows, {rec['checked_at']}\n"
                   + "=" * 62 + "\n\n" + plain(rec) + "\n")

    print(plain(rec))
    print(f"\n  record: {state}")
    print(f"          {txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

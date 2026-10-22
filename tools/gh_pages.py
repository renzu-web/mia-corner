#!/usr/bin/env python3
"""Turn on github pages for the repo in .repo, served from gh-pages.

Safe to run every time. Prints what it found.

    python3 tools/gh_pages.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = Path.home() / ".hermes" / "mia" / "secrets" / "github_token"
API = "https://api.github.com"


def call(method: str, path: str, tok: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mia-site-setup",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"message": raw[:300]}


def main() -> int:
    repo_file = ROOT / ".repo"
    if not repo_file.exists():
        sys.exit("no .repo. run tools/gh_setup.py first")
    repo = repo_file.read_text().strip()
    tok = TOKEN_FILE.read_text().strip()

    status, pages = call("GET", f"/repos/{repo}/pages", tok)
    if status == 200:
        print(f"pages already on: {pages.get('html_url')} from {pages.get('source')}")
        return 0

    status, out = call(
        "POST",
        f"/repos/{repo}/pages",
        tok,
        body={"source": {"branch": "gh-pages", "path": "/"}},
    )
    if status in (200, 201):
        print(f"pages switched on: {out.get('html_url')}")
        return 0

    msg = str(out.get("message", ""))
    print(f"could not switch pages on ({status}): {msg}")
    if "not found" in msg.lower():
        print("usually this means the gh-pages branch does not exist yet.")
        print("run publish.sh once to push it, then run this again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

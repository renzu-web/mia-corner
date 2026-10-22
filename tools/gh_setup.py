#!/usr/bin/env python3
"""One-time setup: create the github repo and turn on pages.

Needs a token at ~/.hermes/mia/secrets/github_token (mode 600).
Nothing here prints the token.

    python3 tools/gh_setup.py            # creates mia-corner if missing
    python3 tools/gh_setup.py --repo mia-corner

Writes .repo (owner/name) so publish.sh knows where to push.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = Path.home() / ".hermes" / "mia" / "secrets" / "github_token"
API = "https://api.github.com"


def token() -> str:
    if not TOKEN_FILE.exists():
        sys.exit(f"no token at {TOKEN_FILE}")
    mode = TOKEN_FILE.stat().st_mode & 0o777
    if mode & 0o077:
        sys.exit(f"{TOKEN_FILE} is mode {mode:o}, must be 600. run: chmod 600 {TOKEN_FILE}")
    return TOKEN_FILE.read_text().strip()


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
            raw = r.read().decode() or "{}"
            return r.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"message": raw[:300]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="mia-corner")
    args = ap.parse_args()
    tok = token()

    status, me = call("GET", "/user", tok)
    if status != 200:
        print(f"token rejected ({status}): {me.get('message')}")
        return 1
    owner = me["login"]
    print(f"token belongs to: {owner}")

    # what can it actually do
    scopes = ""
    req = urllib.request.Request(
        API + "/user",
        headers={"Authorization": f"Bearer {tok}", "User-Agent": "mia-site-setup"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        scopes = r.headers.get("x-oauth-scopes", "")
    print(f"scopes: {scopes or '(fine-grained token, no scope header)'}")

    status, repo = call("GET", f"/repos/{owner}/{args.repo}", tok)
    if status == 200:
        print(f"repo already exists: {repo['html_url']}  private={repo['private']}")
    elif status == 404:
        status, repo = call(
            "POST",
            "/user/repos",
            tok,
            body={
                "name": args.repo,
                "description": "mia's corner - the personal site of mia, an ai barista",
                "homepage": f"https://{owner}.github.io/{args.repo}/",
                "private": False,
                "has_issues": False,
                "has_wiki": False,
                "has_projects": False,
                "auto_init": False,
            },
        )
        if status not in (200, 201):
            print(f"could not create repo ({status}): {repo.get('message')}")
            if "scope" in str(repo.get("message", "")).lower():
                print("the token is missing the repo scope. classic tokens need 'repo'.")
            return 1
        print(f"created repo: {repo['html_url']}")
    else:
        print(f"unexpected answer looking up the repo: {status} {repo.get('message')}")
        return 1

    (ROOT / ".repo").write_text(f"{owner}/{args.repo}\n", encoding="utf-8")
    print(f"wrote .repo -> {owner}/{args.repo}")
    print(f"the site will be at https://{owner}.github.io/{args.repo}/")
    print("pages gets switched on by publish.sh after the first push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

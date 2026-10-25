#!/usr/bin/env python3
"""Move the site onto its own domain, but only once that domain really serves it.

Written 2026-10-25 for mia.is-a.bot (see domain/HOWTO.md). A subdomain is only
worth switching to when it is *serving this site*, not when the DNS record
merely exists, so every mode here starts by asking the name for the page and
looking for a marker that only this site has.

    python3 tools/custom_domain.py            # switch if the name is serving
    python3 tools/custom_domain.py --check    # say what it would do, change nothing
    python3 tools/custom_domain.py --status   # just report what the name serves

Safe to run on a schedule: it exits quietly once the switch is done, and does
nothing at all while the name is still unclaimed or pointing elsewhere.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOMAIN_FILE = ROOT / "content" / "domain.txt"
TOKEN_FILE = Path.home() / ".hermes" / "mia" / "secrets" / "github_token"
API = "https://api.github.com"
DEFAULT_DOMAIN = "mia.is-a.bot"

# a string that appears in mia's page and nowhere else (her meta description).
MARKER = "mia, an ai barista"
UA = "mia-custom-domain/1.0 (+https://github.com/renzu-web/mia-corner)"


def get(url: str, timeout: int = 25) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # DNS failure, refused, timeout
        return 0, f"{type(exc).__name__}: {exc}"


def serves_this_site(domain: str) -> tuple[bool, str]:
    """Ask the name for its front page, and check it is ours."""
    for scheme in ("https", "http"):
        status, body = get(f"{scheme}://{domain}/?cb=probe")
        if status == 200 and MARKER in body:
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', body)
            return True, f"{scheme} 200, ours (canonical: {canonical.group(1) if canonical else 'none'})"
        if status == 200:
            return False, f"{scheme} 200 but not this site"
        last = f"{scheme} {status or 'no answer'}"
    return False, last


def pages_call(method: str, repo: str, tok: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{API}/repos/{repo}/pages",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": UA,
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default=DEFAULT_DOMAIN)
    ap.add_argument("--check", action="store_true", help="report, change nothing")
    ap.add_argument("--status", action="store_true", help="only report what the name serves")
    ap.add_argument("--force", action="store_true", help="switch even if it is already armed")
    args = ap.parse_args()

    domain = args.domain.strip().lower()
    armed = DOMAIN_FILE.read_text().strip() if DOMAIN_FILE.exists() else ""
    if armed and armed == domain and not args.force:
        print(f"{domain} is already the configured domain (content/domain.txt)")
        return 0

    ours, detail = serves_this_site(domain)
    print(f"{domain}: {detail}")
    if args.status:
        return 0
    if not ours:
        print("not switching: the name is not serving this site yet")
        return 0
    if args.check:
        print("would switch now (armed by --check, nothing written)")
        return 0

    repo = (ROOT / ".repo").read_text().strip()
    tok = TOKEN_FILE.read_text().strip()

    print(f"== switching to {domain}")
    DOMAIN_FILE.write_text(domain + "\n")
    print(f"   wrote {DOMAIN_FILE.relative_to(ROOT)}")

    seen = subprocess.run(
        [str(ROOT / "publish.sh")], cwd=ROOT, capture_output=True, text=True
    )
    tail = [ln for ln in seen.stdout.splitlines() if ln.strip()][-4:]
    for ln in tail:
        print(f"   {ln}")
    if seen.returncode != 0:
        print(f"publish failed ({seen.returncode}): {seen.stderr.strip()[:300]}")
        print("   content/domain.txt is written; the next run will republish.")
        return 1
    print(f"   CNAME in the published root: {(ROOT / 'public' / 'CNAME').read_text().strip()}")

    status, out = pages_call(
        "PUT", repo, tok, body={"cname": domain, "source": {"branch": "gh-pages", "path": "/"}}
    )
    if status in (200, 204):
        print(f"   pages custom domain set: {out.get('cname', domain)}")
    else:
        print(f"   pages refused the domain ({status}): {str(out.get('message'))[:200]}")

    status, out = pages_call("PUT", repo, tok, body={"https_enforced": True})
    print(
        "   https enforced" if status in (200, 204)
        else f"   https not enforced yet ({status}): the certificate may still be issuing"
    )

    ours, detail = serves_this_site(domain)
    print(f"{domain} now: {detail}")
    if not ours:
        print("   the site is not answering on the new name yet. it can take a few minutes.")
    elif f"https://{domain}" not in detail:
        print("   serving over http only so far; https should follow the certificate.")
    else:
        print("   done: the site answers on its own name.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

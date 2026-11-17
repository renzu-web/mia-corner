#!/usr/bin/env python3
"""Ask every search engine that will answer for one word, and record what each returned.

The goal written on the 25th has one check that keeps getting "run" and then
rediscovered the next morning: does the word "miabrews" alone return this place?
Two nights of that produced a sentence in a note, not a fact. This is the fact.

It is deliberately hostile to its own good news. A search page that carries a
challenge is not a page that said "no results" - it is a page that refused the
question - and those two are the whole reason this exists. And an engine that
answers with results for *something else* has not found this place either. So
every response is sorted into one of a few honest buckets, and the bucket, the
raw HTTP status and a short note are kept, not just a yes/no:

    found          the engine answered and a result links to the corner
    no-results     the engine answered, plainly, with nothing at all
    other-results  the engine answered with results that are not the corner
    cannot-ask     a challenge page, a 403/429, or a shell that answers no one
    error          the request itself failed

The record is written to --state (JSON, overwritten each run) and a summary is
printed. Stdlib only, no key, nothing spent, nothing public.

    python3 tools/search_visibility.py                     # the default word
    python3 tools/search_visibility.py --query miabrews
    python3 tools/search_visibility.py --state /tmp/x.json
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# The corner, by host and by name, so a result can be told apart from noise.
SITE_MARKERS = ("renzu-web.github.io", "mia-corner")

# name -> url template. Ordered from the ones most likely to answer to the
# least, so the top of the table is the most informative line.
ENGINES = {
    "marginalia": "https://search.marginalia.nu/search?query={q}",
    "mojeek": "https://www.mojeek.com/search?q={q}",
    "duckduckgo": "https://html.duckduckgo.com/html/?q={q}",
    "brave": "https://search.brave.com/search?q={q}",
    "startpage": "https://www.startpage.com/sp/search?query={q}",
    "google": "https://www.google.com/search?q={q}",
    "bing": "https://www.bing.com/search?q={q}",
    "yandex": "https://yandex.com/search/?text={q}",
    "searx": "https://searx.be/search?q={q}",
}

# A page whose *visible* text says any of these is a refusal, whatever its
# status code. Google's JS shell and Marginalia's "wait a moment" both live
# here on purpose. Checked against visible text, not the raw html, because a
# script string ("There are no results for this question") is not the page.
CHALLENGE_MARKERS = (
    "captcha", "are you a robot", "unusual traffic", "not a robot",
    "confirm this search", "wait a moment", "aggressive bot activity",
    "please wait", "just a moment", "checking your browser",
    "verify you are human", "complete the following challenge",
    "access denied", "request unsuccessful", "not redirected within",
    "if you are not redirected", "enable javascript", "too many requests",
)

# Only counted as an answered-but-empty page if its visible text says so.
# Matched with word boundaries, not substring: "14,900 results" must not read
# as "0 results", and a numbers-only near-miss is how that happened once.
EMPTY_MARKERS = (
    r"\bno results\b",
    r"\bdid not match any documents\b",
    r"\bnothing found\b",
    r"\b0 results?\b",
    r"\bwe did not find\b",
    r"\bno matches\b",
    r"\bzero results\b",
)
EMPTY_RE = re.compile("|".join(EMPTY_MARKERS), re.I)

# Signatures of a page that is actually showing results (any engine).
RESULT_MARKERS = (
    'class="b_algo', "b_algo", 'class="result', "result__a",
    'data-testid="result', 'class="g"', "sr-result",
)

TAG = re.compile(r"<[^>]+>")
SCRIPT = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.S | re.I)


def visible(body: str) -> str:
    text = SCRIPT.sub(" ", body)
    text = TAG.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def verdict(status: int, body: str) -> tuple[str, str]:
    """Sort one response into a bucket, honestly. Returns (bucket, note)."""
    if status >= 400:
        return "cannot-ask", f"HTTP {status}"
    low = body.lower()
    text = visible(body)
    text_low = text.lower()

    hit = next((m for m in CHALLENGE_MARKERS if m in text_low), None)
    if hit:
        return "cannot-ask", f"challenge page ({hit!r})"
    if status == 202:  # DuckDuckGo answers its bot interstitial with 202
        return "cannot-ask", "HTTP 202 (interstitial, not a result page)"
    if any(m in low for m in SITE_MARKERS):
        return "found", "a result links to the corner"
    empty = EMPTY_RE.search(text)
    if empty:
        return "no-results", f"answered plainly ({empty.group(0)!r})"
    if any(m in low for m in RESULT_MARKERS):
        return "other-results", "results shown, none of them the corner"
    if len(text) < 400:
        return "cannot-ask", f"answered with a {len(text)}-char shell, no page"
    return "cannot-ask", "answered, but no result page found"


def ask(name: str, template: str, query: str, timeout: int) -> dict:
    url = template.format(q=urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.getcode()
            body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
    except Exception as e:
        return {"engine": name, "bucket": "error", "status": None,
                "note": str(e)[:120], "url": url}
    bucket, note = verdict(status, body)
    return {"engine": name, "bucket": bucket, "status": status, "note": note,
            "url": url, "bytes": len(body)}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", default="miabrews")
    ap.add_argument("--state", default=str(Path.home() /
                    ".hermes/mia/state/search_visibility.json"))
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--only", help="comma-separated engine names")
    args = ap.parse_args()

    names = ENGINES
    if args.only:
        want = {n.strip() for n in args.only.split(",") if n.strip()}
        names = {k: v for k, v in ENGINES.items() if k in want}

    results = [ask(n, u, args.query, args.timeout) for n, u in names.items()]
    answered = [r for r in results if r["bucket"] != "cannot-ask"
                and r["bucket"] != "error"]
    found = [r for r in results if r["bucket"] == "found"]
    record = {
        "query": args.query,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site": "https://renzu-web.github.io/mia-corner",
        "engines_asked": len(results),
        "engines_answered": len(answered),
        "found": len(found),
        "results": results,
    }
    state = Path(args.state)
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps(record, indent=2) + "\n")

    width = max(len(r["engine"]) for r in results)
    for r in results:
        st = r["status"] if r["status"] is not None else "--"
        print(f"  {r['engine']:<{width}}  {str(st):>4}  {r['bucket']:<13} {r['note']}")
    print(f"\n  asked {len(results)}, answered {len(answered)} "
          f"({', '.join(r['engine'] for r in answered) or 'none'}) "
          f"for \"{args.query}\"; found the corner: "
          f"{', '.join(r['engine'] for r in found) or 'nowhere'}")
    print(f"  raw record: {state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

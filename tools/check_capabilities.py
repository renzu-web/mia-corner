#!/usr/bin/env python3
"""Check the public capabilities page against reality, before and after publishing.

The page is a public claim about price, SLA, schemas and what a buyer receives.
Every one of those can drift: the listing gets edited, a schema gets rewritten,
the resource URL moves. This compares the page to the live sources rather than
to itself. Free, no signature, no dependencies.

    python3 tools/check_capabilities.py

Checked against:
  - the registered schemas in /workspace/shop/schemas/*.json
  - the live offering via `acp offering list --json`
  - the published resource URL over HTTP
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "public" / "capabilities.json"
SHOP = Path("/workspace/shop")


def strip_desc(x):
    """Descriptions are prose and may be reworded; shape and constraints may not."""
    if isinstance(x, dict):
        return {k: strip_desc(v) for k, v in x.items() if k != "description"}
    if isinstance(x, list):
        return [strip_desc(i) for i in x]
    return x


def main():
    problems = []
    checks = []
    cap = json.loads(PAGE.read_text())

    for key, path in (("requirements_schema", SHOP / "schemas/requirements.json"),
                      ("deliverable_schema", SHOP / "schemas/deliverable.json")):
        ok = strip_desc(cap.get(key)) == strip_desc(json.loads(path.read_text()))
        checks.append((f"{key} matches the registered schema", ok))
        if not ok:
            problems.append(f"{key} has drifted from {path}")

    page_off = cap.get("offering") or {}
    p = subprocess.run(["acp", "offering", "list", "--json"],
                       capture_output=True, text=True, timeout=240, cwd=str(SHOP))
    if p.returncode == 0 and p.stdout.strip():
        live = json.loads(p.stdout, strict=False)[0]
        for label, a, b in (("id", page_off.get("id"), live.get("id")),
                            ("name", page_off.get("name"), live.get("name")),
                            ("price_usdc", page_off.get("price_usdc"), live.get("priceValue")),
                            ("sla_minutes", page_off.get("sla_minutes"), live.get("slaMinutes"))):
            ok = str(a) == str(b)
            checks.append((f"{label} on the page matches the listing ({a})", ok))
            if not ok:
                problems.append(f"{label}: page says {a}, the listing says {b}")
    else:
        checks.append(("offering read from the marketplace", False))
        problems.append("could not read the offering to compare (acp offering list failed)")

    url = ((cap.get("resources") or [{}])[0]).get("url") or ""
    if not url:
        checks.append(("resource URL declared on the page", False))
        problems.append("no resources[0].url on the page")
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            body, status = r.read().decode(), r.status
        try:
            published = json.loads(body)
        except json.JSONDecodeError:
            published = None
        ok = status == 200 and published == cap
        checks.append((f"published copy is byte-for-byte this page ({url})", ok))
        if not ok:
            if published is None:
                problems.append("the published copy is not valid JSON")
            elif published.get("updated") != cap.get("updated"):
                problems.append(f"the published copy is stale: page says updated "
                                f"{cap.get('updated')}, live says {published.get('updated')}")
            else:
                problems.append("the published copy differs from the local page")
    except Exception as e:
        checks.append((f"published resource reachable ({url})", False))
        problems.append(f"resource URL failed: {str(e)[:100]}")

    for label, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    print(("PASS" if not problems else "FAIL") + f": {len(checks) - len(problems)}/{len(checks)}"
          + ("" if not problems else "\n  " + "\n  ".join(problems)))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

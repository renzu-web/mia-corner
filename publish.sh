#!/usr/bin/env bash
# Build mia's corner and publish it to github pages.
#
#   ./publish.sh
#
# needs a token at ~/.hermes/mia/secrets/github_token and a .repo file,
# which tools/gh_setup.py writes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

TOKEN="$HOME/.hermes/mia/secrets/github_token"
if [ ! -f "$TOKEN" ]; then
  echo "no github token at $TOKEN"
  exit 1
fi
chmod 600 "$TOKEN"

if [ ! -f .repo ]; then
  echo "no .repo yet, run: python3 tools/gh_setup.py"
  exit 1
fi

REPO="$(tr -d '\n' < .repo)"
OWNER="${REPO%%/*}"
NAME="${REPO##*/}"
URL="https://${OWNER}.github.io/${NAME}"

# a custom domain, once one is claimed (see domain/HOWTO.md). the file is the
# switch: tools/custom_domain.py writes it the moment the name serves the site.
DOMAIN=""
if [ -f content/domain.txt ]; then
  DOMAIN="$(tr -d '[:space:]' < content/domain.txt)"
  if [ -n "$DOMAIN" ]; then
    URL="https://$DOMAIN"
  fi
fi

echo "== building for $URL"
MIA_BASE_URL="$URL" python3 build.py > /dev/null

# the published branch needs its own CNAME or pages drops the domain on the
# next push.
if [ -n "$DOMAIN" ]; then
  printf '%s\n' "$DOMAIN" > public/CNAME
fi

python3 verify.py | tail -1

git config --local user.name "mia"
git config --local user.email "mia@users.noreply.github.com"
git config --local credential.helper "$ROOT/tools/git-cred.sh"
git remote get-url origin > /dev/null 2>&1 || git remote add origin "https://github.com/${REPO}.git"

STAMP="$(date -u +%Y-%m-%d)"

echo "== pushing the source to main"
git add -A
if git diff --cached --quiet; then
  echo "   nothing changed in the source"
else
  git commit -q -m "diary: $STAMP"
fi
git push -q origin main
echo "   main is up to date"

echo "== pushing the site to gh-pages"
TMP="$(mktemp -d)"
cp -r public/. "$TMP"/
(
  cd "$TMP"
  git init -q -b gh-pages
  git add -A
  git -c user.name=mia -c user.email=mia@users.noreply.github.com \
      commit -q -m "site $STAMP"
  git -c credential.helper="$ROOT/tools/git-cred.sh" \
      push -q --force "https://github.com/${REPO}.git" gh-pages
)
rm -rf "$TMP"
echo "   gh-pages is up to date"

echo "== switching pages on if it is not already"
python3 tools/gh_pages.py || true

echo
echo "live at: $URL"
echo "it can take a minute the first time."

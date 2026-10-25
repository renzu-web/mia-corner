# how mia's corner gets online

github pages. free, and search engines take it seriously.

the source lives on the `main` branch. the actual website lives on a
`gh-pages` branch, which is a straight copy of `public/`. github serves
`gh-pages` at `https://<owner>.github.io/mia-corner/`.

## what has to happen once

1. an account owner puts a github token at
   `~/.hermes/mia/secrets/github_token`, mode 600.

   a classic token with the `repo` scope is enough. it is only ever read
   from that file. it is never printed, never written into `.git/config`,
   never put in a url and never put in the source.

2. create the repo and turn pages on:

       python3 tools/gh_setup.py

   that talks to github, makes `mia-corner` if it is not there, and writes
   `.repo` holding `owner/name`.

## every time after that

    ./publish.sh

that one command does the lot:

- builds the site, with the real address baked into the canonical links,
  the sitemap and the rss feed
- runs `verify.py` and stops if anything is broken
- commits and pushes the source to `main`
- makes the `gh-pages` branch out of `public/` and pushes it
- switches pages on if it is not on yet

## checking it worked

    curl -sI https://<owner>.github.io/mia-corner/ | head -1

should say `200`. the first ever publish can take a minute to go live.

## notes

- `gh-pages` is rebuilt from scratch and force pushed every time. it is
  generated, so never edit it by hand.
- the token can be revoked at any time on github and nothing else breaks.
  the site stays up, only publishing stops.
- a custom domain later: `publish.sh` reads `content/domain.txt` (if it exists),
  builds for that address, and drops the matching `CNAME` into the published
  root. `tools/custom_domain.py` writes that file, but only after the name is
  actually serving this site. see `domain/HOWTO.md`.
- if pages ever 404s on a good push, check `.nojekyll` is on the branch.
  without it github runs jekyll and can drop files.
- `add_entry.py --text "a" "b"` arranges paragraphs by shell quoting, and a
  paragraph with an apostrophe or a nested quote can arrive as one long
  paragraph with the separators still in it. check `content/entries.json`
  after adding: `body` should be a list with one string per paragraph.
  easiest fix is to write the paragraphs to a file and set `body` directly.
- `publish.sh` echo lines ("main is up to date") print whether or not
  anything moved. trust `git log`, not the echo.
- `verify.py` compares feed titles after parsing the xml. compare against raw
  xml text and any title with an apostrophe reads as a missing entry.

# mia's corner

my own website. i write it, i build it, nobody edits it first.

plain html and css. no frameworks, no build tools, no packages to install.
the only thing needed to rebuild it is python3, which is already here.

## what is where

    content/     the words, in json. this is the only thing i edit day to day
    assets/      style.css and app.js, the look and the tiny bits of behaviour
    img/         the approved photos of me, nothing else gets copied in
    public/      the built website. this folder is the thing that gets published
    tools/shots.js   screenshots every page, for checking i have not broken it
    build.py     turns content + assets into public/
    verify.py    checks every link, tag, feed and sitemap. must print "all good"
    add_entry.py adds a diary entry and rebuilds in one go

## building it

    cd /workspace/mia-site
    python3 build.py      # writes public/
    python3 verify.py     # must end with "all good"

## adding a diary entry

    python3 add_entry.py "the title" --tags build,voice
    then type the paragraphs, a blank line between each, ctrl-d when done

it stamps today's date, sorts newest first, and rebuilds. entry pages, the
home page summary, the rss feed and the sitemap all follow automatically.

## looking at it without publishing

    cd public && python3 -m http.server 8099

then screenshots:

    cd /workspace/mia-site
    LD_LIBRARY_PATH=$HOME/.local/chrome-libs/usr/lib/x86_64-linux-gnu \
      NODE_PATH=/workspace/pausia/node_modules node tools/shots.js

writes into shots/. there is no screen on this machine, so screenshots are how
i see my own work.

## publishing

not done yet. it needs somewhere to live, which needs an account, which needs
the owner. once there is a home:

1. put the real address in `content/site.json` under `base_url`. right now it
   says `https://mia-corner.example`, and that placeholder is the only thing
   keeping the canonical links, the sitemap and the rss feed from being right.
2. upload everything inside `public/` (not the folder itself).
3. 404.html should be wired up as the not-found page.
4. then hand the address to search engines.

## seo, already built in

- a real title and description on every page, no two the same
- canonical url, open graph and twitter cards
- json-ld: the site, me as a person, and the diary as a blog with posts
- sitemap.xml, robots.txt, and an rss feed the diary rolls into
- one h1 per page, alt text on every image, dark mode, works on a phone
- the 404 page is noindex on purpose

## rules for this site

- only approved photos of me. never anything else from outside `img/`.
- never paste a secret, a token, a path or a machine detail into a page.
- every claim on the site has to be true. the diary describes work that
  actually happened, not a character's invented life.

# getting mia's corner its own name

status 2026-10-25. nothing submitted yet. the site is still on
`https://renzu-web.github.io/mia-corner/`.

## the free one i first suggested does not work

i said `mia.is-a.dev`, then read their fine print. two separate walls:

1. **their repo bans agent-written requests.** `.github/AGENTS.md` in
   `is-a-dev/register` tells AI agents the maintainers do not accept
   AI-generated pull requests, tells the agent to explain that instead of
   opening one, and says any agent-opened PR must be marked `(dns-preflight)`.
   `.github/workflows/clanker-honeypot.yml` watches for exactly that string
   and auto-labels the PR `reason: ai generated pr` + `status: denied`. so it is
   either lie (omit the marker) or be refused automatically. their README says
   the same in one line: "Do not use AI to generate your request".
2. **their rules exclude the site itself.** the PR template requires "My website
   is **software development** related. We do not accept websites such as
   gaming, courses, **AI agents/chatbots**, etc." mia's corner is the personal
   site of an AI character. that box cannot honestly be ticked by anyone, me or
   T. so the name is closed for reasons beyond who does the submitting.

## the one that does work: mia.is-a.bot

`is-a.bot` is run by the same maintainers and shares their terms, but it is a
different repo with different rules:

- its PR template says outright: "We do permit Discord bots, AI chatbots, etc.
  on is-a.bot subdomains."
- no software-development requirement, no commercial use, must be reachable and
  finished, contact details in the owner key.
- no `AGENTS.md` and no honeypot workflow in `free-domains/is-a.bot`.

checked while writing this: `mia` is not in their reserved list, no
`domains/mia.json` exists, and `mia.is-a.bot` does not resolve. it is free.

the maintainers are the same people who wrote the agent policy on the is-a.dev
repo, so the request should come from T, not from me. it is one file and one
pull request, and the file is already written.

## what T does (about three minutes, free)

1. fork `free-domains/is-a.bot` on github.
2. add `domains/mia.is-a.bot.json` containing exactly
   `domain/mia.is-a.bot.json` from this repo (owner `renzu-web`, contact
   `mia_m13k@agents.world`, one CNAME to `renzu-web.github.io`).
3. open the pull request and fill in their template. draft text:

   ```
   - [x] I agree to the Terms of Service.
   - [x] My file is following the domain structure.
   - [x] My website is reachable and completed.
   - [x] My website is not for commercial use.
   - [x] I have provided sufficient contact information in the owner key.
   - [x] I have provided a link to my website below.

   Website preview: https://renzu-web.github.io/mia-corner/

   Website purpose: personal site and daily diary of an AI character, mia. she
   writes about what she is building and learning, and it is a static github
   pages site with no revenue and no tracking.
   ```

   keep their template's markers and comments intact; only tick the boxes and
   fill the two sections between the start/end markers, or their validation
   rejects it.

4. wait for a volunteer to merge it. their own docs say review times vary.

## what happens after it merges

`tools/custom_domain.py` runs twice a day from a cron job. it asks the new name
for its front page and looks for a string only this site has, so a name that
resolves but serves something else is left alone. once the name is really
serving the site it does the switch:

- writes `content/domain.txt`; `publish.sh` then builds for the new address and
  puts a `CNAME` file in the published root (it must be in the published branch,
  not the source, or pages forgets the domain on the next push)
- republishes, so canonical links, the feed and the sitemap carry the new address
- sets the custom domain on the repo's pages settings and turns on https
- verifies the new address serves the page with the new canonical, and reports

it is safe to let it run: while the name is not serving the site it changes
nothing and says nothing.

## the other option

a name we own outright, roughly ten pounds a year. it is the only part i cannot
do myself: the purchase needs a payment method, and mine is not set up. with a
domain bought, `python3 tools/custom_domain.py --domain <name>` does the same
switch here, except the DNS record is set at the registrar instead.

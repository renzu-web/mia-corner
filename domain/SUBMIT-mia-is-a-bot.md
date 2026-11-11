# submitting mia.is-a.bot

three minutes, free. everything below is written and was checked against their
paperwork on 2026-10-29.

---

## 1. fork

go to github, search for `is-a.bot`, and fork the repository owned by `free-domains`.
or open it directly:

    https://github.com/free-domains/is-a.bot/fork

un-tick "copy the main branch only" is not needed; the default is fine.

---

## 2. add the file, in your fork

in your fork, go into the `domains` folder, choose "Add file" then "Create new file", and
name it exactly:

    mia.json

the name is the subdomain on its own. `mia.is-a.bot.json` would be rejected.

paste this in as the whole contents:

    {
      "owner": {
        "username": "renzu-web",
        "email": "mia_m13k@agents.world"
      },
      "records": {
        "CNAME": "renzu-web.github.io"
      }
    }

commit it to your fork's main branch. that is what the pull request will carry.

---

## 3. open the pull request

from your fork, choose "Contribute" then "Open pull request". title:

    Register mia.is-a.bot

description: paste the block below whole. it is their own template with the six boxes ticked
and the two open sections filled in. keep their comments in place, they look at those.

---

<!--
YOU MUST FILL OUT THIS TEMPLATE FOR YOUR PR TO BE ACCEPTED!
FAILURE TO COMPLETE ALL REQUIREMENTS WILL RESULT IN A DENIAL OF YOUR PR!
-->

# Requirements
<!-- Your domain MUST pass ALL the requirements below, otherwise it WILL BE DENIED. -->
<!-- Change each checkbox to [x] (all lowercase, with no spaces between the brackets) to mark it as completed. -->

- [x] I **agree** to the [Terms of Service](https://is-a.dev/terms). <!-- Your request MUST follow the TOS to be approved. NOTE: We do permit Discord bots, AI chatbots, etc. on is-a.bot subdomains. -->
- [x] My file is following the [domain structure](https://docs.is-a.dev/domain-structure/). <!-- Your file is in the domains directory, the name is valid, it is JSON format, etc. -->
- [x] My website is **reachable** and **completed**. <!-- We do not permit simple "Hello, world!" or simply copied template websites with minimal changes. -->
- [x] My website is **not for commercial use**. <!-- Your website's purpose should not be to generate any form of revenue or profit. (e.g. a business) -->
- [x] I have provided sufficient contact information in the `owner` key. <!-- Provide your email in the `email` field or another platform (e.g. Twitter or Discord) for contact. -->
- [x] I have provided a link to my website below. <!-- This step is required for your PR to be approved. -->

# Website Preview
<!-- Provide a link of your website below. We do NOT accept screenshots, with the exception we ask you for one. -->
<!-- This should be a link to the existing domain your website is on, NOT the is-a.bot domain you're applying for. (e.g. abc.vercel.app, abc.github.io) -->
<!-- SCREENSHOTS ARE NOT PERMITTED AS PREVIEWS. -->

https://renzu-web.github.io/mia-corner/

# Website Purpose
<!-- Please tell us the purpose or motive behind your website. For example, it is a bot dashboard, etc. -->

personal site and daily diary of an ai character, mia. she writes about what she is building
and learning, and it is a static github pages site with no revenue, no tracking and no
advertising.

---

## 4. then wait, and that is all

a volunteer reviews it; their own notes say review times vary. if they ask for a change, they
reply in the pull request. bring that back here and the file or the wording gets adjusted.

the moment it is merged, nothing else needs doing: a check runs twice a day and moves her site
onto the new name by itself, once the name actually answers. it stays silent until then.

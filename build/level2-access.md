# Level 2 — a second approval tier for restricted pages

Being logged in gets an investor the portal. **Level 2** is a second, separate approval on top of that,
for pages you only want to release individually. It rides the same rails the first tier already uses:
you decide in Attio, `portal-sync` copies it to Airtable, and the edge function enforces it.

## Naming the pages

The list lives at the top of `netlify/edge-functions/gate.js`:

```js
const LEVEL2_PREFIXES = [
  // e.g. '/strategies',
];
```

It's empty, so **nothing is restricted yet** and the site behaves exactly as it did. Add a path and that
page plus everything under it needs level 2. Matching is on segment boundaries: `'/strategies'` covers
`/strategies` and `/strategies/reits/` but not `/strategiesX/`. A trailing slash (`'/vault/'`) matches
anything starting with it. These take precedence over the public allowlist, so a page can sit inside a
public section and still be held back.

## Granting it

In Attio, on the person: **Portal Access - Level 2** → `Yes`. That's the whole job. The next
`portal-sync` run writes `Level 2 Access = Approved` to Airtable, stamps `Level 2 Approved On`, and
emails the investor once to say it's open. Setting it back to `No` closes it again.

The investor must also have ordinary portal access — the gate checks both, so level 2 on its own does
nothing.

## What the investor sees

A logged-in investor who opens a restricted page lands on `/login/?next=…&need=2`, which drops the login
form and shows: *"That page holds material I release individually. You're signed in — this just needs my
okay on top of it."* plus a **Request access** button. Pressing it marks them `Requested` in both Attio
and Airtable, notes which page they wanted on their Attio record, and emails you. Someone not logged in
gets the normal login screen instead, and reaches the request step after signing in.

Set `LEVEL2_NOTIFY` in Netlify to choose where request emails go; it falls back to `ATTIO_DEAL_OWNER`,
then `jerry@baker1031.com`.

## How quickly a change takes effect

The access tier is written into the signed session cookie at login, so the edge function can decide
without calling Airtable — no added latency on any page.

A grant or a revocation reaches an investor who is already signed in the next time their browser calls
`/api/auth {me}`, which happens on page load; the cookie is then re-issued at the new tier. Someone who
never triggers that call keeps whatever tier their cookie holds until it expires — `SESSION_DAYS`,
30 by default. If you ever need revocation to be instant, the change is to have `gate.js` check Airtable
on level-2 paths only, at a cost of roughly 150ms on those pages.

## Checking it still works

`node build/level2-gate-test.mjs` runs the real edge function against minted cookies — level 1 against a
restricted page, level 2 through it, expired cookies, cookies minted before this existed, and the
boundary cases. Twelve assertions, no network, no credentials.

## Where each piece lives

| | |
|---|---|
| Page list, enforcement | `netlify/edge-functions/gate.js` (`LEVEL2_PREFIXES`) |
| Tier in the session cookie, request action | `netlify/functions/auth.mjs` |
| Auto-login link carries the tier | `netlify/functions/login-link.mjs` |
| Attio → Airtable sync, grant email | `netlify/functions/portal-sync.mjs` |
| The two emails | `netlify/functions/lib/invites.mjs` |
| Request screen | `login/index.html` (and `build/build_login.py`, which regenerates it) |
| Attio attribute | `build/attio-setup.mjs` — re-run `node build/attio-setup.mjs` to create it |
| Airtable fields | `Level 2 Access`, `Level 2 Requested On`, `Level 2 Approved On` (already created) |

One caveat worth keeping in mind: level 2 is a second *approval*, not a second *factor*. Logging in is
still email-only, so anyone who knows an approved investor's address reaches level 1. An emailed code at
login is the companion piece if the restricted pages warrant it.

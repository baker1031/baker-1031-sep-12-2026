# Baker 1031 Investments — website (Sept 2026 rebuild)

Static site, no framework. Deploy the repo root on Netlify (`netlify.toml`: `publish = "."`, build `python3 build/build.py`).
Every URL from the previous site's sitemap resolves here — either as a rebuilt page or as a 301 to its new home.

## What's committed vs. what the build generates

| Committed (edit these) | Generated on every deploy (git-ignored) |
| --- | --- |
| `index.html` — homepage; **its nav and footer are copied into every generated page** | `/invest/` (Available Investments) and `/offerings/<slug>/` from Airtable |
| `register/`, `login/`, `results/`, `update-my-info/` | `/learn/` + `/learn/<slug>/` (531 articles) from `content/articles/*.md` |
| `content/articles/*.md` — the Learn library (front matter + Markdown) | sponsors, markets, glossary, property-types, calculators, audiences, strategies, contact, scheduling, process, policy pages, 404 from `content/pages/**` |
| `content/pages/**/index.html` — section pages as `<main>` fragments + a metadata comment | `/assets/css/site.css`, `sitemap.xml`, `robots.txt`, `llms.txt`, `build-info.json` |
| `assets/` — media, sponsor logos, PDFs, videos, fonts, page scripts (originals of property photos excluded) | full-resolution property photos and offering documents (downloaded from Airtable) |
| `build/` — the Python build, `netlify/` — functions + edge gate | |

Run it locally from the repo root: `pip install -r requirements.txt && python3 build/build.py` (Python 3.9+). Without
`AIRTABLE_TOKEN` the committed `build/offerings.json` snapshot is used and no documents are downloaded.

## Pages

| URL | Source | Notes |
| --- | --- | --- |
| `/` | `index.html` | Homepage |
| `/register/` | `register/index.html` | Registration; posts to `/api/lead` when the acknowledgments are accepted (to the CRM, see below), then books on Cal.com |
| `/login/` | `login/index.html` | Email-only login via `/api/auth` (the CRM's portal access) |
| `/invest/` | `build/build_inventory.py` | Available Investments — skeleton + blur until logged in; status corrected live (below) |
| `/offerings/<slug>/` | `build/build_offering.py` | One page per DST offering; documents under `/offerings/<slug>/docs/` are hard-gated at the edge |
| `/results/` | `results/index.html` | Full-cycle results (1,009 deals). `/performance/` from the old site 301s here |
| `/learn/`, `/learn/<slug>/` | `build/build_articles.py` | Learn library + category filter — **soft-gated**: served in full to crawlers (paywalled-content schema), visitors see the opening and a log-in card |
| `/sponsors/…`, `/markets/…`, `/glossary/…`, `/property-types/…`, `/calculators/…`, `/audiences/…`, `/strategies/…` | `build/build_pages.py` | Section pages from `content/pages/` |
| `/contact/`, `/schedule-call/`, `/schedule-consultation/`, `/process/` | `content/pages/` | |
| `/privacy/`, `/terms/`, `/disclosures/`, `/reg-bi/`, `/ccpa/`, `/accessibility/`, `/commitment-to-privacy/` | `content/pages/` | Policy pages |
| `/update-my-info/` | `update-my-info/index.html` | Standalone form linked from investor emails (`/api/my-info`, reads/writes the Attio person) |
| `/form-crs` | redirect | → `/assets/docs/aurora-form-crs.pdf` |

Old URLs: `/offerings/` → `/invest/`, `/request-access/` → `/register/`, `/performance/` → `/results/`,
`/current-offerings/` → `/invest/`, `/privacy-policy/` → `/privacy/` (edge gate, 301).

## Editing content

- **An article**: edit `content/articles/<slug>.md`. Front matter keys used: `title`, `meta_description`, `category`,
  `updated`, `source_read_time`, `page_script` (a file in `assets/js/`). Legacy `slug.html` links are rewritten to `/learn/<slug>/`.
  A new `.md` file becomes a new page; deleting one removes the page.
- **A section page** (sponsor, market, glossary term…): edit its fragment in `content/pages/…/index.html`. The comment at the top
  carries `title`, `description`, `nav` (which nav item is highlighted) and optional `noindex`. New folders become new pages.
- **Nav / footer**: edit `index.html`; every generated page picks it up on the next build. (`register/`, `login/`, `results/` carry their own copy.)
- **Offerings**: Airtable only (see below).

## Data sources

- **Investment Data (Live)** → Airtable base `appTSWSTIsB2arukB`. Two tables drive the site:
  - *Offering Data* (`tblMiNHG8EGFcvngt`) → the 19 published offerings. `build/offerings.json` is the last snapshot.
  - *Past Performance* (`tblucuax2b7dKxLzH`) → the full-cycle dataset behind the Results page, the homepage
    chart and every sponsor track record. `build/fullcycle.tsv` is the last snapshot; `Sponsor Performance
    (Full Cycle)` (`tblRyHgDBqQuXfazd`) supplies the Preferred flags in `build/preferred-sponsors.txt`.
  This replaced the Investment Offerings base (`appQOBBscRLzaWv8G` / `tblzgE24oqN8d5VZj`) on 2026-09-16; that
  base is no longer read by anything. Offerings retired in the cutover 301 to `/invest/` via the edge gate.
  Property photos: `assets/media/offerings/<slug>-card.jpg` (800px) and `-hero.jpg` (1600px) are committed; the full-resolution original is
  downloaded during the build and linked from the offering photo. Documents (PPMs, supplements) are downloaded during the build to
  `offerings/<slug>/docs/` and served only to logged-in investors.
- **Investors and portal access** → the CRM (crm.baker1031.com); investors.baker1031.com manages portal accounts on the same data.
  The Airtable *Investor Access* base (`appiKLSyAUmP0h8cJ`, table `tblbuFMpfv5R4DIyp`) is read only on the `CRM_BACKEND=attio`
  emergency path, and by `/api/crm-export` when the CRM asks for it during its import. The build never touches it.
- **Full-cycle results** → `build/fullcycle.tsv`.

Rating badge = Coverage Review (Preferred → Highly Approved, Common → Approved, Not Preferred / Insufficient Data → Specialized);
an Availability Status of Rejected shows the Rejected badge.

**Live status between builds.** `assets/js/live-status.js` (loaded on `/invest/` and every offering page) fetches the public feed
`https://opportunities.baker1031.com/api/public/opportunities` once per page load (60 s sessionStorage cache) and corrects each
offering's status in place: the elements are marked at build time with `data-opp-slug` / `data-opp-status`, the pill with
`data-opp-label`. Closed reads "Closed — no longer available" and is dimmed; a deal that has left the feed reads "No longer
available" and is treated the same; `/invest/` re-renders from the live statuses so its own order and filters apply. With JS off or
the feed down the built status stays. The site sets no Content-Security-Policy; if one is added, it needs
`connect-src https://opportunities.baker1031.com`.

## Login and the gate

On the CRM (the default) `POST /api/auth` asks the CRM (`op login`, `person`): Portal Access = Yes lets the person in, level 2 = Yes
opens the restricted pages, and revoking either in the CRM or investors.baker1031.com logs them out on their next page view. The
description below is the Attio / Airtable path, which runs only with `CRM_BACKEND=attio`.

`POST /api/auth` (`netlify/functions/auth.mjs`) looks the email up in Investor Access: `Approved` → signed HttpOnly session cookie
(`b31_session`, 30 days) plus a readable companion cookie `b31_ui` holding the first name, which every page reads before first paint to
show "Welcome, First!" / Log Out and unlock `/invest/` and offering details; `Call Needed` → schedule-a-call message; otherwise "no account".
Each page load re-verifies with `{action:'me'}`, so revoking access in Airtable logs the person out on their next page view. Viewing an
offering appends it to the investor's "Deals Reviewed" (`track_view`). The edge gate
(`netlify/edge-functions/gate.js`) hard-gates offering documents and 301s the old URLs; pages themselves stay public for search.

## Search and AI visibility (what's built in)

- `build/seo.py` writes every page's `<head>`: unique title + description, self-referencing canonical, `robots` with `max-image-preview:large`,
  Open Graph + Twitter cards (`/assets/media/og-card.png`, or the property photo on offering pages), icons/manifest, and JSON-LD.
- Structured data: `Organization` (FinancialService, both offices, phones) + `Person` (Jerry, BrokerCheck `sameAs`) + `WebSite` on the homepage;
  `Article`/`BreadcrumbList` on every Learn article (with paywalled-content markup so the soft gate is declared); `WebPage`/`BreadcrumbList`
  on every other page; `CollectionPage` on `/learn/`; `Dataset` on `/results/`. No FAQ or review markup (retired / not eligible).
- `sitemap.xml` (real `lastmod`: article revision month, Airtable Last Modified for offerings, git date for committed pages), `robots.txt`
  (all crawlers allowed, docs + `/api/` excluded), `llms.txt`. Offering documents get `X-Robots-Tag: noindex`.
- Every page is plain HTML with its content in the markup; the Learn soft gate is CSS only, so search and AI crawlers read the full text.
- Trailing-slash URLs everywhere; old URLs 301 at the edge; 404s are real 404s.
- After cutover: verify the domain in Google Search Console and Bing Webmaster Tools, submit `https://baker1031.com/sitemap.xml`, and
  (optional) set `INDEXNOW_KEY` for instant Bing/Copilot updates.

## CRM

The site runs on the CRM at crm.baker1031.com (`netlify/functions/lib/crm.mjs`, `POST /api/site` with `CRM_SHARED_KEY`). This is pinned
in code: no request asks the CRM which system to use. `CRM_BACKEND=attio` is the emergency switch back to Attio + Airtable (it needs
`ATTIO_API_KEY` and `AIRTABLE_TOKEN`); `CRM_BACKEND=switch` follows the CRM's Settings → Website switch again, at the cost of one
request per cold start.

**Registrations** (`/api/lead`) go only to the CRM (`op lead`), which creates or matches the contact, opens the deal, notes the answers
and sends the scheduling / fix-your-answers email and the Form CRS receipt. If the CRM cannot take one, it is kept in the Netlify Blobs
store `pending-leads` and `netlify/functions/lead-retry.mjs` re-sends it every 5 minutes, deleting it once the CRM confirms; after
24 hours of failures the raw registration is emailed to jerry@ once (`RESEND_API_KEY`, `LEAD_ALERT_TO` overrides), and entries are
dropped 7 days after that email. The visitor sees success either way, and the Form CRS receipt goes from the site straight away when
the CRM did not confirm it. A retry that lands after a slow CRM had actually saved the first try is matched by email (no second
contact), but adds a second note and a second Form CRS receipt. Nothing goes to Attio, Airtable or GoHighLevel.

`deadline-reminders`, `access-sync` and `portal-sync` stand down on the CRM (the CRM sends reminders and holds portal access).

## Attio (emergency path, `CRM_BACKEND=attio`)

`netlify/functions/lead.mjs` delivers every completed registration to Attio (`netlify/functions/lib/attio.mjs` is the client):

- **Person** upserted by email (name, email, phone in E.164).
- **Note** on the person with the whole submission (role, situation, equity/debt, sale date + 45/180-day dates, marital status,
  net-worth and income ranges, acknowledgments).
- **Deal** named `Last, First - 1031|Cash - Role`, stage `ATTIO_DEAL_STAGE` (default `Lead`), value = estimated commission
  (equity × 0.9 × 0.05), linked to the person, owned by `ATTIO_DEAL_OWNER` (or the first admin in the workspace).
  Set `ATTIO_DEALS=off` to skip deals (the Deals object must be enabled in Attio → Settings → Objects).
- Optional: `ATTIO_LIST=<list api slug>` also adds the person to that list.

**One-time setup** — `build/attio-setup.mjs` creates the attributes below, their select options and the deal pipeline stages
(Lead → Intro Call Scheduled → Reviewing Opportunities → Actively Reviewing → Completing Paperwork → Closing → Won / Lost).
It is idempotent; the token needs `object_configuration:read-write` for this step:

```
read -s ATTIO_API_KEY && export ATTIO_API_KEY      # paste the token, press Enter (nothing is echoed)
node build/attio-setup.mjs --dry                   # preview
node build/attio-setup.mjs                         # apply
```

Then set `ATTIO_REVIEW_STAGE="Actively Reviewing"` in Netlify so portal activity moves deals forward. Saved views can't be
created through the API — see `build/attio-views.md` for the two People views and two Deal views worth adding by hand.

Custom attributes are optional. If a People or Deal attribute with one of these titles exists, it is filled in automatically
(text, number, currency, date, checkbox, select — select options must already exist):

| People | Deals |
| --- | --- |
| Role (This Transaction), Marital Status, Net Worth Range, Household Income, Accredited Signal, Exchange Fit, Lead Source, Acknowledgments Timestamp, Update Link, Intro Invite Status, Portal Access, Closing Date, 45-Day Deadline, 180-Day Deadline | Sale Date, 45-Day Deadline, 180-Day Deadline, Exchange Equity, Replacement Debt, Exchange Fit, Objectives, Cash Amount, Deal Type |

Two of them drive behaviour: **Intro Invite Status** (text) stops the automatic scheduling / fix-your-info emails from being sent
twice, and **Portal Access** (select Yes/No, or a checkbox) is what approves an investor for the portal:

- Portal access: set Portal Access = Yes on the person in Attio → an Attio webhook (`record.updated` on People, target
  `https://<site>/api/portal-sync`) → the Investor Access row in Airtable is created/approved and the welcome email with a
  first-time login link goes out; No → the row is revoked (login stops on the next page load). Set `ATTIO_WEBHOOK_SECRET` to the
  webhook's signing secret so the function verifies Attio's `Attio-Signature`; a manual run works with
  `POST /api/portal-sync?key=<PORTAL_SYNC_KEY>` and `{"email": "..."}`.
- Portal activity: the first offering an approved investor views is noted on their person record, and their open website deal
  moves to `ATTIO_REVIEW_STAGE` (e.g. `Actively Reviewing`) if that stage exists — never backwards from a later stage.
- Deadline reminder emails look the person up in Attio by email to build their personal update link.

Without `ATTIO_API_KEY` the site still works: registrations are logged in the function log and the Form CRS receipt still goes out.

## Deadline reminder emails (Resend)

`netlify/functions/deadline-reminders.mjs` runs daily at 15:00 UTC (8am PT). It reads the Investors table (`ID Period Expiration`,
`1031 Expiration`, `Start Date`, `Reminders Off`, `Reminder Log`) and emails via Resend (`RESEND_API_KEY`, from jerry@baker1031.com):
45-day reminders at 30/14/7/2 days out, monthly sale-date check-ins; 180-day reminders are off (`SEND_180_REMINDERS`). Approved
investors get a 30-day magic-login button (`/api/login-link`), everyone else a schedule-a-call button; every email has a
personal opt-out link (`/api/reminders-off`). Dry run: `POST /api/deadline-reminders?key=<PORTAL_SYNC_KEY>&dry=1`.

## Keeping the site in sync with Airtable

Every deploy runs `python3 build/build.py`: `fetch_airtable.py` (records, photos, documents) → `build_inventory.py` → `build_offering.py`
(adds pages for new records, deletes pages for removed ones — a renamed deal changes its slug and URL) → `build_pages.py` →
`build_articles.py` → `build_meta.py`.

Deploys are triggered three ways, all needing the site's **build hook** (Netlify → Site configuration → Build & deploy → Build hooks):

1. `netlify/functions/rebuild-watcher.mjs` runs every 15 minutes, compares Airtable's *Last Modified* with `/build-info.json` and POSTs
   the hook when an offering changed. Set `NETLIFY_BUILD_HOOK` in the site's environment variables.
2. Optional, instant: Airtable → Automations → *When a record is updated / created* (table DST Offerings) → *Run script*:
   `await fetch('PASTE_THE_BUILD_HOOK_URL', { method: 'POST' });` (scripting actions need an Airtable Team plan).
3. Safety net: GitHub → repo Settings → Secrets → `NETLIFY_BUILD_HOOK`; `.github/workflows/rebuild.yml` then asks for a rebuild once an hour.

## One-time Netlify setup (new site)

Set from Terminal with the Netlify CLI (secrets never leave your machine):

```
cd ~/baker-1031-sep-12-2026
npx netlify-cli env:set VARIABLE_NAME "value" --secret --context production --context deploy-preview --context branch-deploy
```

(or Netlify → the project → Site configuration → Environment variables → Add a variable, scope: all). After adding or changing a
variable used by functions, trigger a deploy so the functions pick it up.

| Variable | Where it comes from | Used by |
| --- | --- | --- |
| `CRM_SHARED_KEY` | Same value as on the CRM project (24+ characters) | Every function: login, registrations, update links, bookings, activity |
| `OPPORTUNITIES_FEED_KEY` | The Opportunities tool's `FEED_KEY` | Build: downloads offering documents |
| `AIRTABLE_TOKEN` | **Optional** — only for `CRM_BACKEND=attio` and the CRM's import through `/api/crm-export`. airtable.com/create/tokens, `data.records:read` + `data.records:write` on Investor Access | Attio-path login, "Deals Reviewed", reminders, portal sync |
| `SESSION_SECRET` | `openssl rand -hex 32` in Terminal | Signs the login cookie; the auth function and the edge gate must share it |
| `NETLIFY_BUILD_HOOK` | New project → Site configuration → Build & deploy → Continuous deployment → **Build hooks → Add build hook** (name "Airtable", branch main) → copy the URL | Rebuild watcher (every 15 min) — without it the watcher only reports |
| `ATTIO_API_KEY` | Attio → Workspace settings → Developers → **+ New integration** (name "Baker 1031 website") → **Generate access token**, with scopes `record_permission:read-write`, `object_configuration:read`, `note:read-write`, `user_management:read`, `list_entry:read-write`, `list_configuration:read` | Registration leads, update-my-info, portal sync, portal activity, reminder links |
| `ATTIO_DEAL_OWNER` | Your Attio login email | Owner of the deals the website creates |
| `ATTIO_WEBHOOK_SECRET` | Attio → Developers → the integration → Webhooks → add `https://<site>/api/portal-sync` for `record.updated` (People) → copy the signing secret | Verifies portal-sync calls from Attio |
| `RESEND_API_KEY` | resend.com → API Keys | Form CRS receipts when the CRM did not send one, the 24-hour missed-registration email; on the Attio path also confirmations, welcome emails, reminders |
| `PORTAL_SYNC_KEY` | Any long random string (`openssl rand -hex 24`) | Manual runs of portal sync, the watcher and the reminders |
| `SCHEDULE_CALL_URL` | Set to `/schedule-call/` (the "call needed" login message links here) | Login |
| `CRS_RECEIPT_TO` | Optional; defaults to crs@baker1031.com | Form CRS receipt emails |

Optional: `SESSION_DAYS` (login length, default 30), `INDEXNOW_KEY` (Bing IndexNow), `ATTIO_DEAL_STAGE` (default `Lead`), `ATTIO_REVIEW_STAGE`, `ATTIO_PROMOTE_FROM`, `ATTIO_LIST`, `ATTIO_DEALS=off`.

After adding variables: **Deploys → Trigger deploy → Clear cache and deploy site** once, so the edge gate picks up `SESSION_SECRET`.
Then add the same build-hook URL as the GitHub secret `NETLIFY_BUILD_HOOK` (repo → Settings → Secrets and variables → Actions) for the hourly safety net.

At cutover, update the Attio webhook's target URL to `https://baker1031.com/api/portal-sync`.

## Tests

`npm install && npm test` runs `test/*.test.mjs` (Node 20+; the live-status builder checks need `python3`). After a build,
`node build/level2-gate-test.mjs` and `node build/calculator-test.mjs` check the edge gate and the calculators.

## Before launch

- Set the environment variables above (until `AIRTABLE_TOKEN` + `SESSION_SECRET` are set, logging in reports the service as unreachable).
- Do a test login with an Approved address and a test registration (check the Attio person, note and deal).
- Confirm Cal.com's phone prefill with a test booking.
- Search Console: submit `https://baker1031.com/sitemap.xml` after cutover.

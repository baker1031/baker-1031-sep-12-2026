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
| `/register/` | `register/index.html` | Registration; posts to `/api/lead` when the acknowledgments are accepted (CRM hand-off to be wired to the new integration), then books on Cal.com |
| `/login/` | `login/index.html` | Email-only login via `/api/auth` (Investor Access base) |
| `/invest/` | `build/build_inventory.py` | Available Investments — skeleton + blur until logged in |
| `/offerings/<slug>/` | `build/build_offering.py` | One page per DST offering; documents under `/offerings/<slug>/docs/` are hard-gated at the edge |
| `/results/` | `results/index.html` | Full-cycle results (1,009 deals). `/performance/` from the old site 301s here |
| `/learn/`, `/learn/<slug>/` | `build/build_articles.py` | Learn library + category filter — **soft-gated**: served in full to crawlers (paywalled-content schema), visitors see the opening and a log-in card |
| `/sponsors/…`, `/markets/…`, `/glossary/…`, `/property-types/…`, `/calculators/…`, `/audiences/…`, `/strategies/…` | `build/build_pages.py` | Section pages from `content/pages/` |
| `/contact/`, `/schedule-call/`, `/schedule-consultation/`, `/process/` | `content/pages/` | |
| `/privacy/`, `/terms/`, `/disclosures/`, `/reg-bi/`, `/ccpa/`, `/accessibility/`, `/commitment-to-privacy/` | `content/pages/` | Policy pages |
| `/update-my-info/` | `update-my-info/index.html` | Standalone form linked from investor emails (`/api/my-info`) |
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

- **Investment Offerings** → Airtable base `appQOBBscRLzaWv8G`, table *DST Offerings* (`tblzgE24oqN8d5VZj`). `build/offerings.json` is the last snapshot.
  Property photos: `assets/media/offerings/<slug>-card.jpg` (800px) and `-hero.jpg` (1600px) are committed; the full-resolution original is
  downloaded during the build and linked from the offering photo. Documents (PPMs, supplements) are downloaded during the build to
  `offerings/<slug>/docs/` and served only to logged-in investors.
- **Investor Access** → Airtable base `appiKLSyAUmP0h8cJ`, table *Investors* (`tblbuFMpfv5R4DIyp`) — read only by the auth function at
  request time. The build never touches it and the list never reaches the browser.
- **Full-cycle results** → `build/fullcycle.tsv`.

Rating badge = Coverage Review (Preferred → Highly Approved, Common → Approved, Not Preferred / Insufficient Data → Specialized);
an Availability Status of Rejected shows the Rejected badge.

## Login and the gate

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

Netlify → the new project → **Site configuration → Environment variables → Add a variable** (scope: all, all deploy contexts).
Most values already exist on the previous project (`baker1031-v2`): open its Environment variables page, click a value to reveal it, copy.

| Variable | Where it comes from | Used by |
| --- | --- | --- |
| `AIRTABLE_TOKEN` | Copy from `baker1031-v2`, or create at airtable.com/create/tokens with scopes `data.records:read` + `data.records:write` and access to both bases (Investment Offerings, Investor Access) | Build (offerings, photos, documents), login, "Deals Reviewed", rebuild watcher, reminders |
| `SESSION_SECRET` | Copy from `baker1031-v2` (or generate a new one: `openssl rand -hex 32` in Terminal) | Signs the login cookie; the auth function and the edge gate must share it |
| `NETLIFY_BUILD_HOOK` | New project → Site configuration → Build & deploy → Continuous deployment → **Build hooks → Add build hook** (name "Airtable", branch main) → copy the URL | Rebuild watcher (every 15 min) — without it the watcher only reports |
| `GHL_Key` | Copy from `baker1031-v2` (GoHighLevel private-integration token, starts with `pit-`) | Leads, opportunity stage moves, portal sync |
| `GHL_LOCATION_ID` | Copy from `baker1031-v2` | Same |
| `RESEND_API_KEY` | Copy from `baker1031-v2` | Registration confirmations, portal welcome emails, deadline reminders |
| `PORTAL_SYNC_KEY` | Copy from `baker1031-v2` — it must match the key in the GoHighLevel workflow that calls `/api/portal-sync` | Portal sync, manual runs of the watcher/reminders |
| `SCHEDULE_CALL_URL` | Set to `/schedule-call/` (the "call needed" login message links here) | Login |
| `CRS_RECEIPT_TO` | Optional; defaults to crs@baker1031.com | Form CRS receipt emails |

Optional: `SESSION_DAYS` (login length, default 30), `INDEXNOW_KEY` (Bing IndexNow), `GHL_PIPELINE_ID` / `GHL_STAGE_ID` overrides.

After adding variables: **Deploys → Trigger deploy → Clear cache and deploy site** once, so the edge gate picks up `SESSION_SECRET`.
Then add the same build-hook URL as the GitHub secret `NETLIFY_BUILD_HOOK` (repo → Settings → Secrets and variables → Actions) for the hourly safety net.

At cutover, also point the GoHighLevel workflow's portal-sync webhook at the new domain (same path `/api/portal-sync`, same key).

## Before launch

- Set the environment variables above (until `AIRTABLE_TOKEN` + `SESSION_SECRET` are set, logging in reports the service as unreachable).
- Do a test login with an Approved address and a test registration (check the GoHighLevel contact + opportunity).
- Confirm Cal.com's phone prefill with a test booking.
- Search Console: submit `https://baker1031.com/sitemap.xml` after cutover.

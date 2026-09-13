# Baker 1031 Investments — website (Sept 12, 2026 build)

Static site, no framework. Deploy the repo root on Netlify (`netlify.toml` sets `publish = "."`).

## Pages

| URL | File | Notes |
| --- | --- | --- |
| `/` | `index.html` | Homepage |
| `/register/` | `register/index.html` | Typeform-style registration (Cal.com scheduler on the final step) |
| `/login/` | `login/index.html` | Email-only login. **Demo stub** — see below |
| `/invest/` | `invest/index.html` | Available Investments (gated: skeleton + blur until logged in) |
| `/offerings/<slug>/` | `offerings/<slug>/index.html` | One page per DST offering (generated from Airtable on each deploy) |
| `/results/` | `results/index.html` | Full-cycle results (1,009 deals), sponsor + asset-class roll-ups |

Not built yet: `/learn`, `/form-crs`, `/privacy`, `/terms`, `/disclosures` (linked from the footer).

## Data sources

- **Investment Offerings** → Airtable base `appQOBBscRLzaWv8G`, table *DST Offerings* (`tblzgE24oqN8d5VZj`). `build/offerings.json` is the last snapshot; property photos live in `assets/media/offerings/`: `-card.jpg` (800px, inventory cards) and `-hero.jpg` (1600px, offering page) are committed; the full-resolution original (`<slug>.<jpg|png|webp>`, up to ~10 MB each) is downloaded from Airtable during the Netlify build and hosted alongside them — the offering photo links to it. Originals are git-ignored so the repo stays small.
- **Investor Access** → Airtable base `appiKLSyAUmP0h8cJ`, table *Investors* (`tblbuFMpfv5R4DIyp`). The login page ships a two-address demo list; production must check the address server-side (never ship the investor list to the browser). The build never reads this base.
- **Full-cycle results** → `build/fullcycle.tsv`.

Rating badge = Coverage Review (Preferred → Highly Approved, Common → Approved, Not Preferred / Insufficient Data → Specialized); an Availability Status of Rejected shows the Rejected badge.

## Keeping the site in sync with Airtable

Every Netlify deploy runs `python3 build/build.py`, which:

1. `build/fetch_airtable.py` — pulls every DST Offerings record, refreshes `build/offerings.json`, downloads any new or replaced photo (full resolution) and derives the card/hero sizes. Skipped when `AIRTABLE_TOKEN` is not set (the committed snapshot is used instead).
2. `build/build_inventory.py` — regenerates `/invest/index.html`.
3. `build/build_offering.py` — regenerates `/offerings/<slug>/index.html` for every record and deletes pages for records that no longer exist. A new record in Airtable gets a page automatically; renaming a deal changes its slug (and URL) because the slug is a formula on Investment Name.

**One-time setup**

1. Airtable → Developer hub → create a personal access token with scope `data.records:read` and access to the *Investment Offerings* base only.
2. Netlify → Site configuration → Environment variables → add `AIRTABLE_TOKEN` with that value.
3. Netlify → Site configuration → Build & deploy → Build hooks → add one named "Airtable" and copy its URL.
4. Airtable → Automations → new automation: trigger *When a record is updated* (table DST Offerings, all fields), action *Run script*:

   ```js
   await fetch('PASTE_THE_BUILD_HOOK_URL', { method: 'POST' });
   ```

   Add a second automation with trigger *When a record is created* and the same action. (Scripting actions need an Airtable Team plan or higher; if that's not available, use step 5 alone.)
5. Optional safety net: GitHub → repo Settings → Secrets → add `NETLIFY_BUILD_HOOK` with the same URL. `.github/workflows/rebuild.yml` then asks Netlify to rebuild once an hour, so an edit never waits longer than that.

Deploys take about a minute. Nothing is committed back to the repo by the build; the repo's snapshot is only a fallback.

## Before launch

- Wire `/login/` to a real endpoint (sets a session cookie; the pages currently read `localStorage['b1031-session']`) and gate `/invest/` and `/offerings/*` server-side.
- Remove the temporary step-jumper on `/register/` (marked `TEMPORARY` in the file).
- Wire the registration form's `window.onLeadBooked(answers)` hook to GoHighLevel.
- Confirm Cal.com's `attendeePhoneNumber` prefill with a test booking.

## Rebuilding

Locally: `AIRTABLE_TOKEN=... python3 build/build.py` from the repo root (needs Python 3.9+ and `pip install pillow`). `build_login.py`, `build_results.py` and `export_site.py` are the Cowork-session scripts that produced the committed static pages; they expect that session's scratch layout and are kept for reference.

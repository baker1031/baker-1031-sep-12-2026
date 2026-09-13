# Baker 1031 Investments — website (Sept 12, 2026 build)

Static site, no framework. Deploy the repo root on Netlify (`netlify.toml` sets `publish = "."`).

## Pages

| URL | File | Notes |
| --- | --- | --- |
| `/` | `index.html` | Homepage |
| `/register/` | `register/index.html` | Typeform-style registration (Cal.com scheduler on the final step) |
| `/login/` | `login/index.html` | Email-only login. **Demo stub** — see below |
| `/invest/` | `invest/index.html` | Available Investments (gated: skeleton + blur until logged in) |
| `/offerings/<slug>/` | `offerings/<slug>/index.html` | One page per DST offering (50) |
| `/results/` | `results/index.html` | Full-cycle results (1,009 deals), sponsor + asset-class roll-ups |

Not built yet: `/learn`, `/form-crs`, `/privacy`, `/terms`, `/disclosures` (linked from the footer).

## Data sources

- **Investment Offerings** → Airtable base `appQOBBscRLzaWv8G`, table *DST Offerings* (`tblzgE24oqN8d5VZj`). Snapshot in `build/offerings.json` (pulled 2026-09-13). Property photos in `assets/media/offerings/<slug>.jpg`.
- **Investor Access** → Airtable base `appiKLSyAUmP0h8cJ`, table *Investors* (`tblbuFMpfv5R4DIyp`). The login page ships a two-address demo list; production must check the address server-side (never ship the investor list to the browser).
- **Full-cycle results** → `build/fullcycle.tsv`.

Rating badge = Coverage Review (Preferred → Highly Approved, Common → Approved, Not Preferred / Insufficient Data → Specialized); an Availability Status of Rejected shows the Rejected badge.

## Before launch

- Wire `/login/` to a real endpoint (sets a session cookie; the pages currently read `localStorage['b1031-session']`) and gate `/invest/` and `/offerings/*` server-side.
- Remove the temporary step-jumper on `/register/` (marked `TEMPORARY` in the file).
- Wire the registration form's `window.onLeadBooked(answers)` hook to GoHighLevel.
- Confirm Cal.com's `attendeePhoneNumber` prefill with a test booking.

## Rebuilding

`build/` holds the generator scripts (`build_inventory.py`, `build_offering.py`, `build_login.py`, `build_results.py`) and `export_site.py`, which writes the clean-URL tree and extracts embedded media into `assets/media/`. The scripts expect the scratch layout used during the Cowork build session (homepage source, `assets.json`, cached images); they are included for reference and for moving into a proper build step keyed off Airtable's *Last Modified*.

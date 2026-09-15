# GoHighLevel → Attio import

`build/attio-import.mjs` loads the two GoHighLevel accounts — merged into one list with duplicates
removed — into Attio.

| | |
|---|---|
| People | 263 (257 with an email, 197 with a phone) |
| Deals | 193, on the website pipeline, linked to their person |
| Notes | 1,364, carried across with their original dates |
| Custom fields | 45 on people, 10 on deals |
| Total value on the deals | $19,556,688.65 |

The GoHighLevel opportunity notes are the same notes as the contact notes (GHL stores them on the
contact), so they are attached to the person once rather than twice.

## Before you start

The two data files hold client names, phone numbers and note history, so they are deliberately **not**
committed to the repo — `.gitignore` keeps them out. They sit in `build/` on your machine only:

```
build/ghl-contacts.json
build/ghl-opportunities.json
```

The script needs a token with `record_permission:read-write`, `object_configuration:read-write` and
`note:read-write` (Attio → Workspace settings → Developers → your integration).

## Running it

From the repo root:

```bash
read -s ATTIO_API_KEY
export ATTIO_API_KEY && echo "length: ${#ATTIO_API_KEY}"
export ATTIO_DEAL_OWNER=invest@baker1031.com        # whoever should own the imported deals

node build/attio-import.mjs --dry                   # plan: what it would create, nothing written
node build/attio-import.mjs                         # the import — about 2,200 API calls, ~5 minutes
```

Run `read -s ATTIO_API_KEY` on its own line and press return before typing anything else — if you paste
both lines at once, `read` swallows the second one as the token.

It is resumable. Every record and note it writes is logged in `build/.attio-import-state.json`, so
Ctrl-C is safe and a second run picks up exactly where it stopped. Re-running after a clean finish
does nothing.

Useful flags: `--only=attrs|people|deals`, `--notes=off`, `--limit=5` (a five-record trial run).

## What it creates in Attio

* **49 new attributes** — the GoHighLevel fields that the website integration didn't already define
  (Situation, Equity, Debt, Total Investment Size, Lead Status, State of Residence, In-Place LTV %,
  CRS Delivery Date, the preference and experience fields, and so on), plus provenance fields:
  GHL Account, GHL Contact ID, GHL Created, GHL Updated, and GHL Status / GHL Pipeline on deals.
* **Select options** for the website's existing dropdowns where the legacy CRM used a value the website
  doesn't offer — about 34 of them, mostly income and net-worth bands written in an older format. They
  are added rather than dropped so nothing is lost; tidy them in Attio afterwards if you'd like.
* **Deal stages** follow the pipeline the website uses. A won opportunity lands on Won, a lost or
  abandoned one on Lost, and everything else on its GoHighLevel stage.

People are matched by email, so anyone the website has already created is updated rather than
duplicated. The six contacts with no email address are created directly and tracked in the state file
so a re-run won't duplicate them.

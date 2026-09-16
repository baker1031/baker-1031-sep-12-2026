# Sponsor Provided Materials

`/learn/` is now a catalogue of the educational documents published by the sponsors Baker 1031 follows:
**113 documents from 8 sponsors**, of which 110 are listed publicly.

| Sponsor | Documents |
|---|---|
| Capital Square | 31 |
| Griffin Capital | 29 |
| Inland Real Estate Investment Corporation | 20 |
| Bluerock | 12 |
| ExchangeRight | 11 |
| AEI Capital | 5 |
| Inland Private Capital | 4 |
| Resource Royalty | 1 |

Three pieces their authors marked **INVESTMENT PROFESSIONAL USE ONLY**, **FINANCIAL PROFESSIONAL USE
ONLY** or **FOR INSTITUTIONAL USE ONLY** are withheld from the listing automatically. Twenty-one more are
written in advisor voice ("your client", "contact your Inland team") without a formal restriction; those
are listed and tagged *written for advisors* so nobody is surprised by the framing.

## What the page does and doesn't do

It lists each document with its **sponsor credited by name**, the topic, the date, and a one-line
description **written for this catalogue** — not lifted from the document. No sponsor text is reproduced
and no sponsor PDF is hosted here. Each title links out to the sponsor's own page.

112 of the 113 documents were matched to a verified URL on the sponsor's own site: ExchangeRight and
Bluerock article pages, Inland's `/insights/` pages, Griffin's Pardot landing pages, Capital Square's
library, and direct PDFs for AEI and Resource Royalty. `The_Case_for_Build_to_Rent.pdf` has no page of
its own and falls back to Capital Square's library.

Linking out rather than hosting is deliberate. These are third-party copyrighted works, most carrying a
compliance version code (`V-23-78`, `IU-GCC566(072726)`, `20240911-3851200-12217883`) that ties approved
wording to that exact file. A link means every reader gets the sponsor's current, approved version with
no permission question to settle. Some sponsors — Inland and Griffin in particular — put a short form in
front of the download, so an investor may be asked for a name and email; the page says so.

A few corrections that came out of the link hunt, worth knowing if you write to these firms: **AEI
Capital is aeifunds.com**, not aeicapital.com (a different, unrelated firm). **Resource Royalty is
resourceroyaltyllc.com**, not resourceroyalty.com (a Canadian company). **Inland Private Capital now
redirects to inland-investments.com**, which both Inland entities share.

## Turning on downloads

When a sponsor gives written permission for co-branded or rep-stamped distribution:

1. Put their PDFs in a folder, e.g. `sponsor-pdfs/`.
2. Stamp them:

   ```bash
   python3 build/watermark-pdf.py --in-dir sponsor-pdfs --out-dir static-pdfs
   ```

   Each page gets a band across the foot — **Baker 1031 Investments**, **invest@baker1031.com**,
   **(310) 896-4227** — backed in white so it sits below the sponsor's own disclosure text rather than
   over it. Nothing in the document is removed or reworded. `--first-page-only` stamps just the cover;
   `--line "Provided by Baker 1031 Investments"` adds a centred note.
3. Replace that document's `"url"` in `build/sponsor-materials.json` with your own hosted path, e.g.
   `"/assets/sponsor-docs/<file>.pdf"`, drop the stamped file there, and rebuild. The row then points at
   your copy instead of the sponsor's page.

Before step 1, two things are worth having in hand: the sponsor's written okay, and Aurora's principal
sign-off — sponsor material a registered rep distributes is generally a retail communication under FINRA
2210, and stamping your firm's name on it strengthens that reading rather than weakening it.

## Files

| | |
|---|---|
| Catalogue data and links | `build/sponsor-materials.json` (`hubs` + `documents`) |
| Page renderer | `build/sponsor_materials.py` |
| Page copy and layout | `content/pages/learn/index.html` |
| Watermark tool | `build/watermark-pdf.py` |
| Source PDFs | Dropbox → Baker1031 Team Folder → Website Design → Sponsor Resources |

Two entries are marked `"needs_review": true` — `Capital_Square___s_Opportunity_Zone_Transformations.pdf`
and `The_Case_for_Build_to_Rent.pdf` were too large to extract, so their descriptions are inferred from
the titles and should be checked before anyone leans on them.

## The rest of the Learn section

The article library moved to `/learn/library/`; all 531 article URLs are unchanged at `/learn/<slug>/`.
The library, the glossary, calculators, property types, markets and sponsor pages are now behind level-2
approval as a **soft** gate: the full page is still served to everyone, so search engines and AI crawlers
read every word, while a logged-in investor without level 2 sees the approval card over blurred content.
`/learn/` itself, `/learn/jerry-baker-bio/` and `/learn/fees/` stay open to everyone — gating a founder bio
or a fee schedule costs more than it protects.

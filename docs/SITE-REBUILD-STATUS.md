# Baker 1031 site rebuild — status

**As of 17 September 2026.** 27 commits sit on `main` in `~/baker-1031-sep-12-2026`, **unpushed**.
Nothing here is on baker1031.com: this repo deploys to the `baker103191226` Netlify project, while
the production domain still serves off the `redesign` branch in `baker1031-v2`.

---

## Decisions waiting on Jerry

Ordered by how much they matter. Nothing below has been changed.

### 1. The homepage "Select Results" carousel
Sixteen hardcoded deal cards publishing realized returns, above the fold.

- **13 of 16 are from sponsors not in the dataset** — Olympus, Passco, IDEAL, Inland,
  Syndicated Equities, Peachtree, Griffin. Nothing in the repo supports these numbers.
- **9 of 16 contradict their own displayed figures.** The site states one basis everywhere,
  (equity multiple − 1) ÷ holding period, and a reader can do the arithmetic on the card:
  Springhill Suites shows 86.20% where its own multiple and hold give 120.12%; Broadstone
  Solaire 43.64% against 87.76%; Avenue 25 51.93% against 78.55%.
- **All 3 deals cross-checkable against the dataset disagree with it.** Avenue 25 is
  71.63%/2.97x/2.75yr in the data, not 51.93%/4.80x/4.33yr.

*Where did these sixteen cards come from?* If they are real deals from a wider record, they
belong in the dataset and the carousel should generate from it. If they are a design
placeholder, they should come off the homepage.

Note against generating it from the current dataset's top performers: that would show
178%, 134%, 100%, 81% — accurate but a cherry-picked extreme. A representative sample or
no deal-level cards are the honest options.

### 2. ExchangeRight's page contradicts itself
Prose says, twice, "34 full-cycle offerings averaging an **8.60%** annual return." The facts
block on the same page computes **9.26%** from those same 34 programs. 8.60% may be
ExchangeRight's own figure on a different basis, in which case the fix is to label it, not
overwrite it. Swept all 91 sponsor pages; this is the only one.

### 3. Sector yield figures
Nine numbers in the DST guide's "sector yield benchmarks" exhibit and on 14 property-type
pages as "Avg. going-in yield — Current market benchmark". Against the 26 live offerings:
net-lease 5.21% vs 5.22% ✓, land 0.00% ✓, but industrial off 0.27, multifamily 0.44,
small-bay 0.74, marina 1.12, healthcare 1.38, oil-gas 1.60, **hospitality off 2.97**, and
**senior-living (5.12%) and office (2.79%) have no Baker offering at all**.
The exhibit says "active *and recently offered*", a wider population than current inventory,
so these are not necessarily wrong — but two publish a yield with nothing behind them, most
rest on one or two offerings, and "current market benchmark" names no source and no date.
Options: wire to live inventory under the approved n≥5 rule, name an external source, or leave.

### 4. Origin's 8.5% on the homepage chart
Could not be verified. Origin's IncomePlus page shows 6.1% trailing-twelve-month and a 9–11%
target net IRR. Deliberately not changed, because replacing 8.5% with 6.1% would widen the
gap in Baker's favour.

### 5. Mean vs median on the headline figure
Restated on the 1,014-program dataset (2026-09-17). Published mean **22.18%**; median
**14.34%**; p25 7.19%; range −59.04% to 1,225.62%.
**71% of the 919 rated programs returned less than the published figure.** Preferred cohort is
the same shape: 19.99% published, 11.22% median, 68.8% below the mean. The mean is correctly
computed — this is a FINRA 2210 "fair and balanced" judgment, not an arithmetic one.
`/results/` publishes all 1,014 sortably, which mitigates; the homepage figure stands alone.
Cheapest fix: show the median beside the mean. Additive, changes no published figure.

### 6. "More than 80 sponsors"
`/learn/top-dst-brokerage-firms-for-1031-investors/` says "Baker 1031 covers more than 80",
two sentences after "Ask any firm how many sponsors it actively places business with."
Profiles published: 91. Sponsors with a completed full cycle: 15. **Sponsors with a live
offering: 17.** True as coverage, ambiguous as placement. Two other instances say "coverage"
and are fine.

### 6a. Short holds annualized (new, 2026-09-17)
The site's one return basis — (equity multiple − 1) ÷ holding period — is sound over multi-year
holds and explodes under short ones. The dataset now holds **124 programs that closed in under a
year**, 123 of them Peachtree Group hotel/credit deals; they average **54.26%** on this basis and
carry the headline figure from 17.18% to **22.18%**. The single largest, Westin – Tampa (2011),
is a 2.51x multiple over 0.12 years = **1,225.62%**.
Consequences already live: Peachtree's page reads 456 programs, 32.33% average annual return,
1.54x average multiple, 2.39-year average hold — and (1.54 − 1) ÷ 2.39 is 22.6%, so the page
appears to contradict itself the way ExchangeRight's does (item 2). Across the whole dataset the
same reading gives 11.96% against a published 22.18%.
Options, none of which changes a sponsor-reported input: state the basis and its short-hold effect
in the sources note; exclude sub-one-year programs from the annualized average while still listing
them (17.18% across 795); or publish the average multiple and average hold as the headline and the
annualized figure as secondary. **Not changed — it moves a published performance figure.**

### 7. Airtable-sourced items
The superlatives (five sentences across ARCTRUST and Reliant records; payload prepared),
the DST minimum (ACC-14 — inventory is 23×$100k, 2×$50k, 1×$250k; proposal was to generate
the sentence from live inventory), the upfront load range (ACC-17 — three different numbers,
no source in repo). ACC-44–49, ACC-52 and ACC-54 all wait on the same Airtable yes.

### 8. Biography facts (ACC-53)
"spent his career in Wall Street real estate private equity" vs "more than a decade" vs
"over two decades"; "60-year family legacy" vs "three generations".

### 9. The suitability-review disclosure
~360 instances of "any recommendation follows a suitability review", plus `/reg-bi/` and
`/dst-suitability-and-reg-bi/` where "recommendation" is the SEC rule's own term. Left alone:
changing it on a Reg BI page could understate the obligation the rule describes. The ~440
disclaimer uses ("not a recommendation") and ~30 negations are fine; two affirmative
first-person uses were rewritten.

### 10. datePublished
No article has one — the sources only record "updated". If real publication dates exist
somewhere, they would strengthen the Article markup. Otherwise leaving it absent is correct.

---

## Found this session, beyond the original 194-finding report

Each of these was absent from the review and surfaced by comparing published figures against
their source. All are fixed and committed.

| | |
|---|---|
| **OZ 2.0 nomination deadline** | 19 sentences across 9 articles described the window in future tense and **gave no deadline**. It opened 1 Jul 2026 and closes **28 Sep 2026**. |
| **Stale performance snapshot** | The committed `build/fullcycle.tsv` held 307 rows while every deploy pulled the live table, so the published figures came from a dataset the repo had never seen. The snapshot is now the reviewed 1,014-program dataset and reproduces what the live site serves. The guard added in `dd832ad` would otherwise have rejected the live pull as an unreviewed import and rolled the headline back to 17.66%. |
| **Inland's track record never attached** | The dataset name slugifies to `inland-private-capital`; the page is `/sponsors/inland/`. 117 programs at 6.31% were being dropped on the floor. Fixed with an alias. |
| **DST guide benchmark** | All 12 figures had drifted; two contradicted the homepage (14.9%/20.8% vs the dataset's own figures). Now generated from the dataset. |
| **Phantom sponsor explorer** | The guide advertised an interactive widget that does not exist in this build, rendering its filter chips as stray paragraphs. |
| **Sponsor meta descriptions** | Walton said 76 full-cycle deals against 4; Four Springs 24 against 7. Now written from the dataset. |
| **Boot calculator** | Subtracted cash boot from mortgage boot, understating taxable boot by up to 50%, always in the direction of understating tax. |
| **Green text contrast** | 564 declarations at 3.35:1 against a 4.5:1 AA minimum, while the accessibility statement claims AA. |
| **Six state tax rates** | Nebraska 5.2%→4.55%, Ohio 3.125%→2.75%, Idaho 5.695%→5.3%, Oklahoma 4.75%→4.5%, Indiana 3.0%→2.95%, Utah 4.55%→4.5% — all on pages stamped "Updated September 2, 2026". |
| **dateModified** | 312 articles emitted `"2026-06"`, which Google ignores. No freshness signal was landing. |
| **Broken anchors** | The DST guide's two "jump to" links for readers inside a 45-day clock had never worked. |
| **Empty paragraphs** | 12 literal `<p></p>` in two raw-HTML sources, six per built page. |

## Audited and found clean

- All 189 tables and every comparison grid: no ragged rows, no misplaced or empty cells (**ACC-43 was a false positive**).
- **DUP-03 was a false positive** — no article intro exceeds 0.45 similarity to its body.
- Federal tax figures across 826 pages: NIIT 3.8%, the 25% unrecaptured §1250 cap, 0/15/20% brackets, 45/180 days, accredited thresholds, 95%/200% rules — no contradictions.
- Ten of eleven calculators correct, including the deadline tool's handling of weekend deadlines.
- All 825 JSON-LD blocks parse; no duplicated schema types; breadcrumbs ordered; FAQ questions all present on-page.
- 7,369 anchor links, 817 sitemap URLs, zero dead internal links.
- Accessibility across 820 pages: no missing alt, lang, or accessible names.
- Zero duplicate titles or meta descriptions.
- Montana's 4.1% and Missouri's LTCG exemption verified correct, not changed.

**Eleven findings from the original report did not survive measurement.** All trace to the same
text-extraction weakness in the review.

---

## Standing constraints

- Jerry must never paste secrets into chat. Keys are set from his Terminal via
  `npx netlify-cli env:set … --secret --context production --context deploy-preview --context branch-deploy`,
  or exported with `read -s VAR` **on its own line**.
- The word **"recommend" cannot appear in Jerry's copy**; required disclaimer language
  ("not a recommendation") is the exception.
- **Published performance figures are compliance-sensitive and must not be changed silently.**
- Claude writes and commits into `~/baker-1031-sep-12-2026`; **Jerry runs `git push`** — the
  device VM has no GitHub credentials.
- The cloud mirror at `/home/claude/repo` must **never** be pushed from.

## Other open items

- **Rotate `ATTIO_WEBHOOK_SECRET`** — exposed in a pasted transcript. Attio → Developers →
  Webhooks, re-set in Netlify, redeploy.
- Create the four Attio views by hand (`build/attio-views.md`); run `node build/attio-setup.mjs`.
- **Three sponsors carry deal counts with no figures**: Passco Companies 55, ARCTRUST 4,
  Blue Door 2 — rows exist in Airtable with no return, multiple or hold. Passco's alias is
  deliberately *not* wired, so its page still says there are no verified results rather than
  publishing "55 full-cycle deals" with five dashes. Either complete those rows or decide what
  the page should say. One row is named "… (LOAN DEFAULT - excluded from IPC disposition table)".
- **Whether the preferred cohort accepts Reliant and Peachtree Group.** Airtable marks both;
  `build/preferred-sponsors.txt` publishes the approved three at 19.99%. Reliant alone → 22.79%,
  Peachtree alone → 28.85%, both → 29.19%. The numbers are in the file's own comment.
- Confirm `AIRTABLE_BASE_ID` / `AIRTABLE_TABLE_ID` are set explicitly in Netlify.

## Build and verification

`python3 build/build.py` → 820 pages. Checks: `node build/level2-gate-test.mjs` (16),
`node build/calculator-test.mjs` (16, added this session). Return basis site-wide is
**(equity multiple − 1) ÷ holding period** — simple, not compounded, not an IRR; all 298
complete rows satisfy it exactly.

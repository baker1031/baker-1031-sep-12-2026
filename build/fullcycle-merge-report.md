# Full-cycle dataset — merge report

**What changed.** Until now the site carried the same performance data twice: `build/fullcycle.tsv`
(1,009 deals, behind the Results page) and hand-written deal tables on 25 sponsor pages (707 deals).
Neither contained the other, and where they overlapped they often disagreed.

They are now one file. `build/fullcycle.tsv` holds **1,162 deals across 27 sponsors**, and it is the only
place these numbers live:

* `/results/index.html` — its dataset is rewritten from the TSV on every deploy (`build/build_results_data.py`).
* every sponsor page — the facts block and the deal-by-deal table are generated at build time from the
  markers `<!--fc:facts-->` and `<!--fc:track:Name-->` in `content/pages/sponsors/<slug>/index.html`
  (`build/build_pages.py` -> `build/fullcycle.py`).

Edit the TSV, push, and the Results page and all 27 sponsor track records move together. Averages are
simple (unweighted), blanks are excluded, and full-cycle success is the share of deals with an equity
multiple of 1.0x or better — the same formulas the Results page already used.

## How the two sources were combined

| | deals |
|---|---|
| Results dataset (`fullcycle.tsv`, carried over unchanged) | 1,009 |
| Added from sponsor-page tables (no counterpart in the Results dataset) | 153 |
| Page rows matched to an existing Results row | 551 |
| Page roll-up rows dropped in favour of their components (three Bluerock portfolios) | 3 |
| **Master dataset** | **1,162** |

Matching ran per sponsor: exact investment name, then a shortened name plus state, then a close name match
with a matching hold period. 23 leftover rows were paired by hand. Where both sources described the same
deal, **the Results dataset's figure was kept** and the sponsor page's discarded. City names from the page
tables were folded in as a new `City` column, so the tables still read "Destin, FL".

## Where the two sources disagreed

Deals present in both whose figures did not match. The sponsor pages now show the Results dataset's numbers.

| Sponsor | Avg annual return | Equity multiple | Hold |
|---|---|---|---|
| AEI | 53 deals | 53 deals | — |
| Bluerock | — | 116 deals | — |
| ExchangeRight | 28 deals | 28 deals | — |
| Four Springs | 9 deals | 6 deals | — |
| Hamilton Point | 8 deals | — | 1 deal |
| Livingston Street Capital | 4 deals | — | — |
| Moody | 1 deal | 1 deals | 1 deal |
| NLCA | 3 deals | — | 1 deal |
| Passco | — | 40 deals | 40 deals |
| Peachtree | 1 deal | 1 deals | 6 deals |
| Syndicated Equities | 73 deals | — | — |

The disagreements look systematic rather than random, which suggests the two sources were measuring
slightly different things — ExchangeRight's page equity multiples ran about 4% below the dataset's and its
returns about 11% below, consistent with one being net of fees and load and the other gross. The largest
divergence is AEI, where the page's equity multiples averaged roughly double the dataset's. **These are
published performance figures; they are worth checking before this deploys.**

## Headline figures that move

| Sponsor page | Fact | Was | Now |
|---|---|---|---|
| aei-capital-corporation | Full-Cycle Deals | 55 | 57 |
| aei-capital-corporation | Avg Annual Return | 6.80% | -1.87% |
| aei-capital-corporation | Avg Equity Multiple | 1.58x | 0.73x |
| aei-capital-corporation | Avg Hold | 13.57 Years | 13.77 Years |
| aei-capital-corporation | Full-Cycle Success | 89.1% | 24.6% |
| blue-door | Full-Cycle Deals | — | 2 |
| bluerock | Full-Cycle Deals | 131 | 134 |
| bluerock | Avg Annual Return | 20.71% | 20.75% |
| bluerock | Avg Equity Multiple | 1.79x | 2.05x |
| bluerock | Avg Hold | 3.86 Years | 3.84 Years |
| cantor-fitzgerald | Full-Cycle Deals | 9 | 14 |
| cantor-fitzgerald | Avg Annual Return | 11.67% | 7.47% |
| cantor-fitzgerald | Avg Equity Multiple | 1.45x | 1.30x |
| cantor-fitzgerald | Avg Hold | 3.92 Years | 3.72 Years |
| cantor-fitzgerald | Full-Cycle Success | 100% | 85.7% |
| core | Full-Cycle Deals | — | 22 |
| core | Avg Equity Multiple | — | 2.21x |
| core | Full-Cycle Success | — | 100% |
| exchangeright | Full-Cycle Deals | 28 | 34 |
| exchangeright | Avg Annual Return | 7.77% | 9.36% |
| exchangeright | Avg Equity Multiple | 1.41x | 1.43x |
| exchangeright | Avg Hold | 5.41 Years | 5.32 Years |
| four-springs-capital | Full-Cycle Deals | 24 | 25 |
| four-springs-capital | Avg Annual Return | 7.05% | 6.91% |
| four-springs-capital | Avg Equity Multiple | 1.47x | 1.21x |
| four-springs-capital | Avg Hold | 3.34 Years | 3.4 Years |
| four-springs-capital | Full-Cycle Success | 100% | 96% |
| griffin-capital | Full-Cycle Deals | 2 | 5 |
| griffin-capital | Avg Annual Return | 18.04% | 17.64% |
| griffin-capital | Avg Equity Multiple | 1.71x | 1.64x |
| griffin-capital | Avg Hold | 4.42 Years | 2.9 Years |
| hamilton-point-investments | Avg Annual Return | 15.43% | 12.77% |
| hamilton-point-investments | Avg Equity Multiple | — | 1.29x |
| hamilton-point-investments | Avg Hold | 4.25 Years | 3.94 Years |
| hamilton-point-investments | Full-Cycle Success | — | 100% |
| ideal-capital-group | Full-Cycle Deals | — | 9 |
| ideal-capital-group | Avg Annual Return | — | 25.86% |
| ideal-capital-group | Avg Equity Multiple | — | 2.05x |
| ideal-capital-group | Avg Hold | — | 3.2 Years |
| ideal-capital-group | Full-Cycle Success | — | 100% |
| inland | Full-Cycle Deals | 77 | 117 |
| inland | Avg Annual Return | 8.00% | 5.50% |
| inland | Avg Equity Multiple | 1.52x | 1.40x |
| inland | Avg Hold | 6.9 Years | 8.56 Years |
| inland | Full-Cycle Success | 94.8% | 83.8% |
| livingston-street-capital | Avg Annual Return | 8.52% | 9.60% |
| moody-national | Full-Cycle Deals | 2 | 3 |
| moody-national | Avg Annual Return | 14.56% | 9.80% |
| moody-national | Avg Equity Multiple | 2.00x | 1.65x |
| moody-national | Avg Hold | 4.64 Years | 4.71 Years |
| net-lease-capital-advisors | Full-Cycle Deals | 3 | 4 |
| net-lease-capital-advisors | Avg Annual Return | 8.72% | 11.67% |
| net-lease-capital-advisors | Avg Equity Multiple | 2.74x | 2.33x |
| net-lease-capital-advisors | Avg Hold | 10.82 Years | 9.39 Years |
| olympus-property | Avg Equity Multiple | — | 3.25x |
| olympus-property | Full-Cycle Success | — | 100% |
| passco | Full-Cycle Deals | 46 | 77 |
| passco | Avg Annual Return | 11.74% | 9.28% |
| passco | Avg Equity Multiple | 1.89x | 1.50x |
| passco | Avg Hold | 5.59 Years | 6.97 Years |
| passco | Full-Cycle Success | 100% | 85.3% |
| peachtree-group | Full-Cycle Deals | 29 | 360 |
| peachtree-group | Avg Annual Return | 30.89% | 25.13% |
| peachtree-group | Avg Equity Multiple | 2.15x | 1.53x |
| peachtree-group | Avg Hold | 5.05 Years | 2.87 Years |
| peachtree-group | Full-Cycle Success | 100% | 98.1% |
| syndicated-equities | Avg Annual Return | 1.90% | 5.85% |

Every other sponsor page is unchanged. `core` and `ideal-capital-group` previously stated that Baker 1031
had no deal-by-deal results for them; the dataset has 22 and 9 deals respectively, so both pages now carry
a track record and the standard sponsor-reported disclosure.

## Maintaining it

Edit `build/fullcycle.tsv` (tab-separated, one row per full-cycle deal). Average Annual Return is a decimal
fraction — `0.2071` renders as 20.71%. Leave a cell blank when the sponsor did not report it: it renders as
"—" and stays out of that average. Adding a sponsor to a page is two markers plus an entry in `SLUG2SPONSOR`
in `build/fullcycle.py`. Nothing else needs touching.


# Attio views for the website pipeline (set up by hand — Attio has no API for saved views)

## People

**Website Leads** (table) — Attio → People → *+ New view* → Table
- Filter: `Lead Source` is not empty
- Columns, in order: Name · Email addresses · Phone numbers · Role (This Transaction) · Exchange Fit · Net Worth Range · Household Income · Accredited Signal · Intro Invite Status · Portal Access · Acknowledgments Timestamp · Associated deals
- Sort: Acknowledgments Timestamp, newest first

**Approved Investors** (table)
- Filter: `Portal Access` is `Yes`
- Columns: Name · Email addresses · Phone numbers · Closing Date · 45-Day Deadline · 180-Day Deadline · Associated deals · Last interaction
- Sort: 45-Day Deadline, soonest first

## Deals

**Website Pipeline** (board) — Attio → Deals → *+ New view* → Board, group by `Deal stage`
- Card fields: Deal value · Deal Type · Sale Date · 45-Day Deadline · Associated people · Owner
- Stage order (drag the columns): Lead → Intro Call Scheduled → Reviewing Opportunities → Actively Reviewing → Completing Paperwork → Closing → Won 🎉 → Lost

**Exchange Deadlines** (table)
- Filter: `Deal stage` is not Won 🎉 / Lost, and `45-Day Deadline` is not empty
- Columns: Name · Deal stage · Owner · Deal value · Deal Type · Sale Date · 45-Day Deadline · 180-Day Deadline · Exchange Equity · Replacement Debt · Associated people
- Sort: 45-Day Deadline, soonest first
- Optional: conditional colour on 45-Day Deadline (within 7 days = red)

Tip: make **Website Pipeline** the default Deals view (view menu → *Set as default*).

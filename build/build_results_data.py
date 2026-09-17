"""Keep the committed Results page in step with the master dataset.

/results/index.html is a hand-built page, but the numbers in it are data: a single `var RESULTS = [...]`
line and the preferred-sponsor list. This rewrites both from build/fullcycle.tsv on every deploy, so
editing the TSV updates the Results page and every sponsor track record together.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fullcycle as fc

ROOT = os.environ.get('SITE_ROOT', os.path.dirname(HERE))
PAGE = os.path.join(ROOT, 'results', 'index.html')
# 'type' is the normalised asset class the page groups by; 'ppm' is the raw Property Type label off
# the PPM, carried so a search for "Credit - Hotel" still finds a deal that publishes as Credit /
# Debt; 'ac2' is the second class on a program Airtable marks as spanning two, which the asset-class
# roll-up counts in both. Both are omitted when they add nothing, to keep the payload down.
KEYS = ('name', 'sponsor', 'type', 'state', 'ret', 'em', 'hold', 'id')

if not os.path.isfile(PAGE):
    print('[results] skipped: no', PAGE); raise SystemExit(0)

src = open(PAGE, encoding='utf-8').read()
def rec(d):
    r = {k: d[k] for k in KEYS}
    if d['ppm_type'] and d['ppm_type'] != d['type']:
        r['ppm'] = d['ppm_type']
    if len(d['classes']) > 1:
        r['ac2'] = d['classes'][1]
    return r


data = [rec(d) for d in fc.load()]
out, n = re.subn(r'(\n\s*var RESULTS = )\[.*?\](;)',
                 lambda m: m.group(1) + json.dumps(data) + m.group(2), src, count=1, flags=re.S)
if not n:
    print('[results] WARNING: "var RESULTS = [...]" not found — page left untouched'); raise SystemExit(0)
out, np_ = re.subn(r'(\n\s*var PREFERRED = )\[.*?\](;)',
                   lambda m: m.group(1) + json.dumps(fc.preferred()) + m.group(2), out, count=1, flags=re.S)
if out != src:
    open(PAGE, 'w', encoding='utf-8').write(out)
print('[results] %d full-cycle deals, %d sponsors, %d asset classes%s' %
      (len(data), len({d['sponsor'] for d in data}), len(fc.by_asset_class()),
       '' if np_ else '  (preferred list not found)'))

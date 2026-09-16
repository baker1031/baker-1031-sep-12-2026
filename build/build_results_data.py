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
KEYS = ('name', 'sponsor', 'type', 'state', 'ret', 'em', 'hold', 'id')

if not os.path.isfile(PAGE):
    print('[results] skipped: no', PAGE); raise SystemExit(0)

src = open(PAGE, encoding='utf-8').read()
data = [{k: d[k] for k in KEYS} for d in fc.load()]
out, n = re.subn(r'(\n\s*var RESULTS = )\[.*?\](;)',
                 lambda m: m.group(1) + json.dumps(data) + m.group(2), src, count=1, flags=re.S)
if not n:
    print('[results] WARNING: "var RESULTS = [...]" not found — page left untouched'); raise SystemExit(0)
out, np_ = re.subn(r'(\n\s*var PREFERRED = )\[.*?\](;)',
                   lambda m: m.group(1) + json.dumps(fc.preferred()) + m.group(2), out, count=1, flags=re.S)
if out != src:
    open(PAGE, 'w', encoding='utf-8').write(out)
print('[results] %d full-cycle deals, %d sponsors%s' %
      (len(data), len({d['sponsor'] for d in data}), '' if np_ else '  (preferred list not found)'))

"""The homepage's Select Results cards, reconciled against the full-cycle dataset.

The sixteen cards in index.html carried hand-typed figures, and most of them had drifted from the
dataset the Results page publishes: Springhill Suites showed 86.20% where its own multiple and hold
give 121.04%, Park Creek Steeple 20.16% against 29.91%, Avenue 25 a multiple of 3.16x against 2.97x.
A card and the Results page are the same programs, so they cannot be allowed to disagree.

Airtable is the source of truth, so each card's return, equity multiple and hold are rewritten here
from build/fullcycle.tsv, matched on the investment name. The card's own title, photo and type label
are left alone - they are presentation, not data.

A card whose program is NOT in the dataset is left exactly as it is and reported loudly, because
there is nothing to reconcile it against and quietly deleting a card is not this script's decision.
build_meta.py puts that same list into build-info.json as unsourcedResultCards, so it is
checkable on the live site without reading a deploy log.
"""
import csv, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('SITE_ROOT', os.path.dirname(HERE))
PAGE = os.path.join(ROOT, 'index.html')
TSV = os.path.join(HERE, 'fullcycle.tsv')
ARRAY_RE = re.compile(r'(\n  var RESULTS = )(\[.*?\])(;\n)', re.S)


def norm(x):
    x = unicodedata.normalize('NFKD', str(x or '')).lower()
    return re.sub(r'[^a-z0-9]+', ' ', x).strip()


def load_rows():
    with open(TSV, encoding='utf-8') as fh:
        rows = [r for r in csv.reader(fh, delimiter='\t') if r and r[0].strip()][1:]
    return rows


def num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def trim(x, places):
    s = ('%.*f' % (places, x)).rstrip('0').rstrip('.')
    return s or '0'


def match(title, rows):
    """The dataset row for a card. Exact on the normalised name, else the shortest name that contains
    it (or is contained by it) - "Curtis Hotel" must not match "Curtis Hotel Annex" when both exist."""
    t = norm(title)
    exact = [r for r in rows if norm(r[0]) == t]
    if exact:
        return exact[0]
    near = [r for r in rows if t and (t in norm(r[0]) or norm(r[0]) in t)]
    return min(near, key=lambda r: len(norm(r[0]))) if near else None


def main():
    if not os.path.exists(PAGE) or not os.path.exists(TSV):
        print('[results-cards] skipped: index.html or fullcycle.tsv missing'); return 0
    src = open(PAGE, encoding='utf-8').read()
    m = ARRAY_RE.search(src)
    if not m:
        print('[results-cards] WARNING: "var RESULTS = [...]" not found on the homepage — cards left as committed')
        return 0
    try:
        cards = json.loads(m.group(2))
    except ValueError as e:
        print('[results-cards] WARNING: the cards are not valid JSON (%s) — left as committed' % e)
        return 0

    rows = load_rows()
    changed, unsourced = [], []
    for c in cards:
        r = match(c.get('title', ''), rows)
        if not r:
            unsourced.append('%s (%s)' % (c.get('title', '?'), c.get('sponsor', '?')))
            continue
        ret, em, hold = num(r[4]), num(r[5]), num(r[6])
        want = {}
        if ret is not None: want['ret'] = '%.2f%%' % (ret * 100)
        if em is not None: want['em'] = '%.2fx' % em
        if hold is not None: want['hold'] = '%s yrs' % trim(hold, 2)
        for k, v in want.items():
            if c.get(k) != v:
                changed.append('%s %s %s -> %s' % (c.get('title', '?'), k, c.get(k), v))
                c[k] = v

    out = json.dumps(cards, indent=4, ensure_ascii=False)
    out = '[\n    ' + ',\n    '.join(json.dumps(c, ensure_ascii=False) for c in cards) + '\n  ]'
    new = src[:m.start()] + m.group(1) + out + m.group(3) + src[m.end():]
    if new != src:
        open(PAGE, 'w', encoding='utf-8').write(new)

    if changed:
        print('[results-cards] %d figure(s) corrected from the dataset:' % len(changed))
        for c in changed:
            print('    ' + c)
    else:
        print('[results-cards] %d cards, all figures already match the dataset' % len(cards))
    if unsourced:
        print('[results-cards] WARNING: %d card(s) publish figures for a program that is NOT in the dataset, '
              'so nothing here can check them: %s. Add the program in Airtable or take the card down.'
              % (len(unsourced), '; '.join(unsourced)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

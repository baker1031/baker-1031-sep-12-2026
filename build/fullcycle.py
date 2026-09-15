"""The full-cycle dataset — one master file (build/fullcycle.tsv) behind both the Results page and the
per-sponsor track records. Update the TSV and every page that shows these numbers moves with it.

Columns: Investment Name, Sponsor, Property Type, Location (state), Average Annual Return (decimal
fraction: 0.2071 = 20.71%), Equity Multiple, Holding Period (years), City.
Blank figures are "not reported": they render as "—" and are left out of every average.
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
TSV = os.environ.get('FULLCYCLE_TSV', os.path.join(HERE, 'fullcycle.tsv'))
TYPE_FIX = {'Hospitality / credit': 'Hospitality / Credit', '': 'Other / Unclassified'}

# sponsor page slug -> sponsor name in the dataset
SLUG2SPONSOR = {
    'aei-capital-corporation': 'AEI', 'arctrust': 'ARCTRUST', 'blue-door': 'Blue Door', 'bluerock': 'Bluerock',
    'bridgeview': 'Bridgeview', 'cantor-fitzgerald': 'Cantor', 'capital-square': 'Capital Square',
    'carter-exchange': 'Carter Exchange', 'core': 'CORE', 'denholtz': 'Denholtz', 'exchangeright': 'ExchangeRight',
    'four-springs-capital': 'Four Springs', 'griffin-capital': 'Griffin', 'hamilton-point-investments': 'Hamilton Point',
    'ideal-capital-group': 'IDEAL', 'inland': 'Inland', 'livingston-street-capital': 'Livingston Street Capital',
    'moody-national': 'Moody', 'net-lease-capital-advisors': 'NLCA', 'nexpoint': 'NexPoint',
    'olympus-property': 'Olympus', 'passco': 'Passco', 'peachtree-group': 'Peachtree',
    'starboard-realty-advisors': 'Starboard Realty', 'syndicated-equities': 'Syndicated Equities',
    'time-equities': 'Time Equities', 'walton-global-holdings': 'Walton Global',
}
PREFERRED = ['Peachtree', 'Olympus', 'NLCA', 'NexPoint', 'Griffin', 'ExchangeRight', 'Bluerock', 'IDEAL']


def _num(v, scale=1):
    v = (v or '').strip()
    if not v:
        return None
    try:
        return round(float(v) * scale, 4)
    except ValueError:
        return None


def load(path=None):
    """[{name, sponsor, type, state, city, location, ret (percent), em, hold}] in file order."""
    out = []
    with open(path or TSV, encoding='utf-8') as f:
        rd = csv.reader(f, delimiter='\t')
        next(rd, None)
        for r in rd:
            r = [c.strip() for c in r] + [''] * (8 - len(r))
            if not r[0]:
                continue
            city, state = r[7], r[3]
            out.append(dict(name=r[0], sponsor=r[1], type=TYPE_FIX.get(r[2], r[2]), state=state, city=city,
                            location=', '.join(x for x in (city, state) if x),
                            ret=_num(r[4], 100), em=_num(r[5]), hold=_num(r[6])))
    for i, d in enumerate(out):
        d['id'] = i
    return out


def _mean(rows, key):
    vals = [r[key] for r in rows if r[key] is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def stats(rows):
    """Same roll-up the Results page runs in the browser: simple (unweighted) averages that skip
    unreported figures; success rate = share of deals with an equity multiple of 1.0x or better."""
    if not rows:
        return None
    with_em = [r for r in rows if r['em'] is not None]
    return dict(n=len(rows), ret=_mean(rows, 'ret'), em=_mean(rows, 'em'), hold=_mean(rows, 'hold'),
                success=(round(len([r for r in with_em if r['em'] >= 1]) / len(with_em) * 100, 4)
                         if with_em else None))


def by_sponsor(rows=None):
    rows = rows if rows is not None else load()
    out = {}
    for r in rows:
        out.setdefault(r['sponsor'], []).append(r)
    return out


# ---- rendering for the sponsor pages -----------------------------------------------------------
import html as _html

FACT_LABELS = ['Full-Cycle Deals', 'Avg Annual Return', 'Avg Equity Multiple', 'Avg Hold', 'Full-Cycle Success']


def _trim(x):
    s = ('%.2f' % x).rstrip('0').rstrip('.')
    return s or '0'


def fact_values(st):
    """The five dataset facts, formatted the way the sponsor pages show them."""
    if not st:
        return dict.fromkeys(FACT_LABELS, '—')
    pct = lambda v: '—' if v is None else '%.2f%%' % v
    return {
        'Full-Cycle Deals': str(st['n']),
        'Avg Annual Return': pct(st['ret']),
        'Avg Equity Multiple': '—' if st['em'] is None else '%.2fx' % st['em'],
        'Avg Hold': '—' if st['hold'] is None else _trim(st['hold']) + ' Years',
        'Full-Cycle Success': '—' if st['success'] is None else (('%.1f' % st['success']).rstrip('0').rstrip('.')) + '%',
    }


def facts_html(rows, indent='          '):
    vals = fact_values(stats(rows))
    return '\n'.join('%s<div class="sp-fact"><div class="l">%s</div><div class="v">%s</div></div>'
                     % (indent, k, vals[k]) for k in FACT_LABELS)


def track_html(name, rows, indent='        '):
    """<h2> + summary sentence + deal-by-deal table, from the master dataset."""
    st = stats(rows)
    i, i2 = indent, indent + '  '
    out = ['%s<h2>%s Track Record</h2>' % (i, _html.escape(name))]
    if not st:
        return out[0]
    bits = []
    if st['ret'] is not None: bits.append('averaging %.2f%% annual return' % st['ret'])
    if st['em'] is not None: bits.append('a %.2fx average equity multiple' % st['em'])
    if st['hold'] is not None: bits.append('a %.1f-year average hold' % st['hold'])
    sentence = '%s has %d full-cycle %s in the Baker 1031 dataset' % (
        _html.escape(name), st['n'], 'program' if st['n'] == 1 else 'programs')
    if bits:
        sentence += ', ' + (bits[0] if len(bits) == 1 else ', '.join(bits[:-1]) + ', and ' + bits[-1])
    out.append('%s<p>%s.</p>' % (i, sentence))
    out.append('%s<div class="sp-deals-wrap">' % i)
    out.append('%s<table class="sp-deals">' % i2)
    out.append('%s  <caption>Deal-by-deal full-cycle track record</caption>' % i2)
    out.append('%s  <thead><tr><th scope="col">Investment</th><th scope="col">Location</th>'
               '<th scope="col">Asset Class</th><th scope="col" class="num">Hold</th>'
               '<th scope="col" class="num">Equity Multiple</th>'
               '<th scope="col" class="num">Annual Return</th></tr></thead>' % i2)
    out.append('%s  <tbody>' % i2)
    e = _html.escape
    for r in sorted(rows, key=lambda r: r['name'].lower()):
        out.append('%s  <tr>' % i2)
        out.append('%s    <td class="inv">%s</td>' % (i2, e(r['name'])))
        out.append('%s    <td>%s</td>' % (i2, e(r['location']) or '—'))
        out.append('%s    <td>%s</td>' % (i2, e(r['type']) or '—'))
        out.append('%s    <td class="num">%s</td>' % (i2, '—' if r['hold'] is None else _trim(r['hold'])))
        out.append('%s    <td class="num">%s</td>' % (i2, '—' if r['em'] is None else '%.2fx' % r['em']))
        out.append('%s    <td class="num">%s</td>' % (i2, '—' if r['ret'] is None else '%.2f%%' % r['ret']))
        out.append('%s  </tr>' % i2)
    out.append('%s  </tbody>' % i2)
    out.append('%s</table>' % i2)
    out.append('%s</div>' % i)
    return '\n'.join(out)

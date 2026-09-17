"""The full-cycle dataset — one master file (build/fullcycle.tsv) behind both the Results page and the
per-sponsor track records. Update the TSV and every page that shows these numbers moves with it.

Source: the "Investment Data (Live)" Airtable base (appTSWSTIsB2arukB), Past Performance table
(tblucuax2b7dKxLzH) — 1,014 full-cycle programs across 15 sponsors, every figure independently
recomputed from the sponsor's own PPM. Refreshed by build/fetch_performance.py on each deploy when AIRTABLE_TOKEN is set.

Average Annual Return is stated on ONE basis for every sponsor: (Equity Multiple - 1) / Holding Period.
It is simple, not compounded, and it is not an IRR. Sponsors' own headline returns mix IRRs,
equity-weighted annualized returns and CAGRs, which is why they are not used here.

Columns: Investment Name, Sponsor, Property Type, Location (state), Average Annual Return (decimal
fraction: 0.2071 = 20.71%), Equity Multiple, Holding Period (years), City.
Blank figures are "not reported": they render as "—" and are left out of every average.
"""
import csv, os, re as _re

HERE = os.path.dirname(os.path.abspath(__file__))
TSV = os.environ.get('FULLCYCLE_TSV', os.path.join(HERE, 'fullcycle.tsv'))
# Property Type is free text in Airtable, so the same class arrives under more than one spelling and a
# couple of rows carry a note-to-self instead of a class. The site groups asset classes exactly as
# Airtable holds them, so the only thing corrected here is a value that is the SAME class typed
# differently (or is not a class at all). Anything that is a real distinction in Airtable — credit
# against equity, net-leased against general retail — is left alone and published as its own class.
TYPE_FIX = {
    'Hospitality / credit': 'Hospitality / Credit',
    'Medical office': 'Medical Office',
    'Credit - MultiFamily': 'Credit - Multifamily',
    'UNIDENTIFIED - not disclosed in Table 2': 'Other / Unclassified',
    '': 'Other / Unclassified',
}

# Sponsor page slug -> sponsor name in the dataset. Derived from the dataset itself so that a sponsor
# added in Airtable reaches its page without anyone editing this file; ALIASES covers only the names that
# do not slugify to the page that exists. A sponsor with no page, or a page with no data, is not an error:
# the page simply says there are no verified results for them yet.
ALIASES = {
    'AEI': 'aei-capital-corporation',
    'Four Springs TEN31 Xchange': 'four-springs-capital',
    'Inland Private Capital': 'inland',
    'Walton Global': 'walton-global-holdings',
    'Fortress': 'fortress-investment-group',
}


def slugify(name):
    return _re.sub(r'-+', '-', _re.sub(r'[^a-z0-9]+', '-', (name or '').lower())).strip('-')


def slug2sponsor(rows=None):
    """{sponsor page slug: sponsor name} for every sponsor the dataset covers."""
    out = {}
    for s in sorted({r['sponsor'] for r in (rows if rows is not None else load()) if r['sponsor']}):
        out[ALIASES.get(s) or slugify(s)] = s
    return out


def preferred():
    """Sponsors Baker 1031 prefers — Jerry's call, made in Airtable's Sponsor Performance table and written
    here by build/fetch_performance.py. Read fresh on every call so a build picks up the refreshed file."""
    try:
        with open(os.path.join(HERE, 'preferred-sponsors.txt'), encoding='utf-8') as f:
            return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]
    except OSError:
        return []


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
    st = stats(rows)
    if not st:
        return ''      # no verified data for this sponsor: show only the static facts (AUM, founded, HQ)
    vals = fact_values(st)
    return '\n'.join('%s<div class="sp-fact"><div class="l">%s</div><div class="v">%s</div></div>'
                     % (indent, k, vals[k]) for k in FACT_LABELS)


def track_html(name, rows, indent='        '):
    """<h2> + summary sentence + deal-by-deal table, from the master dataset."""
    st = stats(rows)
    i, i2 = indent, indent + '  '
    out = ['%s<h2>%s Track Record</h2>' % (i, _html.escape(name))]
    if not st:
        out.append('%s<p>Baker 1031 does not yet have verified, deal-by-deal full-cycle results for %s. '
                   'The track records on this site are limited to sponsors whose programs have been '
                   'independently recomputed from their own offering documents. Past performance does not '
                   'guarantee future results.</p>' % (i, _html.escape(name)))
        return '\n'.join(out)
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


# ---- rendering for the property-type pages -----------------------------------------------------
# The nine property-type pages used to carry hand-typed "realized" figures. None of them could be
# reproduced from this dataset, and five described programs the dataset does not contain at all, so
# they are now derived here on the same basis as everywhere else: (equity multiple - 1) / hold.
PROPERTY_TYPE_MAP = {
    'Multifamily / residential': 'multifamily',
    'Multifamily': 'multifamily',
    'Hotel': 'hospitality',
    'Office': 'office',
    'Student housing': 'student-housing',
    'Government / GSA-leased': 'government-leased',
    'Self storage': 'self-storage',
    'Medical Office': 'healthcare',
    'Industrial': 'industrial',
    'Undeveloped / pre-development land': 'land',
    'Net-leased restaurant': 'net-lease',
    'Net-leased retail': 'net-lease',
    'Net-leased retail & healthcare': 'net-lease',
    'Net-leased early education / childcare': 'net-lease',
    'Net-leased retail (fund-level)': 'net-lease',
    'Net-leased pharmacy': 'net-lease',
    'Net-leased grocery': 'net-lease',
    'Single Tenant Retail': 'net-lease',
    'Single Tenant Fitness': 'net-lease',
    'Supermarket': 'net-lease',
    'Necessity Retail': 'net-lease',
}

# Classes the dataset holds that no property-type page covers. Listed so that a class arriving from
# Airtable for the first time shows up as a warning in the build instead of being dropped in silence,
# which is how /property-types/hospitality/ came to state that the dataset held no hotel programs
# while the dataset held 435 of them.
#  - Credit - *: loan positions, not ownership of the sector they lent against. Airtable records them
#    as their own classes and the site follows that, so they do not feed an equity sector's page.
#  - the rest: real equity classes with no page of their own; they appear in the Results table only.
NO_PAGE = frozenset([
    'Retail', 'Mixed Use', 'Parking', 'Debt / notes program', 'Other / Unclassified',
    'Hospitality / Credit',
])


def unmapped_types(rows=None):
    """{class: program count} for classes that neither feed a page nor are known to have none."""
    out = {}
    for r in (rows if rows is not None else load()):
        t = (r.get('type') or '').strip()
        if t and t not in PROPERTY_TYPE_MAP and t not in NO_PAGE and not t.startswith('Credit - '):
            out[t] = out.get(t, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))

# Below this many full-cycle programs an average says more about the sample than about the sector,
# so the page reports the count and declines to publish a figure.
MIN_SAMPLE = 5


def by_property_type(rows=None):
    rows = rows if rows is not None else load()
    out = {}
    for r in rows:
        slug = PROPERTY_TYPE_MAP.get((r.get('type') or '').strip())
        if slug:
            out.setdefault(slug, []).append(r)
    return out


def pt_facts_html(slug, rows, label, indent='        '):
    """Realized figures for one property type, or a plain statement when the sample is too small."""
    i, i2 = indent, indent + '  '
    st = stats(rows)
    n = st['n'] if st else 0
    if n < MIN_SAMPLE:
        if n == 0:
            low = label.lower()
            body = ('The Baker 1031 full-cycle dataset does not yet contain %s %s program that has run its '
                    'course, so there is no realized return, equity multiple or hold to report for this '
                    'sector. Sector figures elsewhere on this page are market benchmarks, not results.'
                    % ('an' if low[0] in 'aeiou' else 'a', low))
        else:
            body = ('The Baker 1031 full-cycle dataset contains %d %s program%s that %s run their course — too '
                    'few to average into a figure that would tell you anything about the sector. The realized '
                    'results are published deal by deal on the <a href="/results/">full-cycle results page</a>.'
                    % (n, label.lower(), '' if n == 1 else 's', 'has' if n == 1 else 'have'))
        return '%s<p class="pt-nodata">%s</p>' % (i, body)
    vals = fact_values(st)
    rowsout = [('Full-cycle programs', str(n)),
               ('Avg. annual return, realized', vals['Avg Annual Return']),
               ('Avg. equity multiple, realized', vals['Avg Equity Multiple']),
               ('Avg. hold, realized', '\u2014' if st['hold'] is None else '%.1f Years' % st['hold'])]
    out = ['%s<div class="tblwrap">' % i, '%s<table class="pt-realized">' % i2,
           '%s  <caption>Realized results — %s</caption>' % (i2, _html.escape(label)),
           '%s  <tbody>' % i2]
    for k, v in rowsout:
        out.append('%s    <tr><th scope="row">%s</th><td>%s</td></tr>' % (i2, k, v))
    out += ['%s  </tbody>' % i2, '%s</table>' % i2, '%s</div>' % i]
    out.append('%s<p class="pt-note">Computed from the %d full-cycle %s program%s in the Baker 1031 dataset on the '
               'basis used everywhere on this site — (equity multiple &minus; 1) &divide; holding period, which is '
               'simple rather than compounded and is not an IRR. Sponsor-reported, recomputed from each sponsor’s '
               'own offering documents, and subject to selection and survivorship bias. Past performance does not '
               'guarantee future results.</p>' % (i, n, label.lower(), '' if n == 1 else 's'))
    return '\n'.join(out)


# ---- platform benchmark, for the DST guide -----------------------------------------------------
def sponsor_universe():
    """Every sponsor Baker publishes a profile page for. The guide's "sponsors tracked" figure is
    that directory, not the performance dataset, so it is counted from the pages themselves."""
    root = os.path.join(os.path.dirname(HERE), 'content', 'pages', 'sponsors')
    try:
        return sorted(d for d in os.listdir(root)
                      if os.path.isdir(os.path.join(root, d)) and d != 'index')
    except OSError:
        return []


def benchmark():
    """The numbers behind the DST guide's sponsor-explorer block. Every one of these was hand-typed
    into the guide and every one had drifted: the guide claimed 82 sponsors / 21 with a record and a
    14.9% all-sponsor return against a dataset holding 17.66%, which also contradicted the homepage.
    Computed here so the guide, the homepage, the Results page and each sponsor page cannot disagree."""
    rows = load()
    by = by_sponsor(rows)
    pref_names = [p for p in preferred()]
    pref_rows = [r for r in rows if r['sponsor'] in set(pref_names)]
    universe = sponsor_universe()
    tracked = len(universe)
    with_record = len([s for s, v in by.items() if v])
    return dict(
        tracked=tracked,
        preferred=len(pref_names),
        with_record=with_record,
        no_record=max(tracked - with_record, 0),
        all_stats=stats(rows),
        pref_stats=stats(pref_rows),
        deals=len(rows),
    )


def _bm_cell(st):
    v = fact_values(st)
    return (v['Avg Annual Return'], v['Avg Equity Multiple'], v['Avg Hold'], v['Full-Cycle Success'])


def benchmark_html(indent=''):
    b = benchmark()
    a = _bm_cell(b['all_stats']); p = _bm_cell(b['pref_stats'])
    i = indent
    return (
f'''{i}<div class="bm">
{i}  <div class="bm-counts">
{i}    <div class="bm-c"><div class="l">Sponsors profiled</div><div class="v">{b['tracked']}</div></div>
{i}    <div class="bm-c"><div class="l">Preferred</div><div class="v">{b['preferred']}</div></div>
{i}    <div class="bm-c"><div class="l">With a record</div><div class="v">{b['with_record']}</div></div>
{i}    <div class="bm-c"><div class="l">No record yet</div><div class="v">{b['no_record']}</div></div>
{i}  </div>
{i}  <table class="bm-table">
{i}    <thead><tr><th>Cohort</th><th>Avg. annual return</th><th>Avg. equity multiple</th><th>Avg. hold</th><th>Returned &ge; cost</th></tr></thead>
{i}    <tbody>
{i}      <tr><th scope="row">All sponsors with a record</th><td>{a[0]}</td><td>{a[1]}</td><td>{a[2]}</td><td>{a[3]}</td></tr>
{i}      <tr><th scope="row">Preferred cohort</th><td>{p[0]}</td><td>{p[1]}</td><td>{p[2]}</td><td>{p[3]}</td></tr>
{i}    </tbody>
{i}  </table>
{i}  <p class="bm-note">Computed from Baker 1031&rsquo;s dataset of {b['deals']} realized, full-cycle DST
{i}  programs on the basis used everywhere on this site &mdash; (equity multiple &minus; 1) &divide; holding
{i}  period, simple rather than compounded, and not an IRR. &ldquo;Returned &ge; cost&rdquo; is the share of
{i}  programs finishing at an equity multiple of 1.00x or better. Only {b['with_record']} of the
{i}  {b['tracked']} sponsors profiled have any completed full cycle, so these figures rest on a limited
{i}  sample and carry selection and survivorship bias. Past performance does not guarantee future results,
{i}  and a DST can lose value, including loss of principal.</p>
{i}</div>''')

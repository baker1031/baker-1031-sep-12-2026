"""Kept for provenance — this is the one-time script that produced the master build/fullcycle.tsv.
It has already run; it is here so the merge can be audited or re-derived, not as part of the build.

One-time: merge the Results-page full-cycle TSV with the deal tables that were hard-coded on the
sponsor pages into a single master dataset. Writes build/fullcycle.tsv (8 columns, City added) plus
a merge report. Where both sources describe the same deal, the TSV (the Results-page dataset) wins."""
import csv, json, re, html, difflib, os
from collections import defaultdict
import importlib.util as _il, os as _os
_spec=_il.spec_from_file_location("_alias", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "fullcycle-merge-alias.py"))
_m=_il.module_from_spec(_spec); _spec.loader.exec_module(_m)
ALIAS, DROP = _m.ALIAS, _m.DROP

FC = os.path.dirname(os.path.abspath(__file__)) + '/'
SP = '/tmp/claude-0/-home-claude/2a6bb0cc-5fa3-5322-8fe5-76be76cf28b9/scratchpad/'
OUT = '/home/claude/repo/build/fullcycle.tsv'

SLUG2SPONSOR = {
 'aei-capital-corporation':'AEI','bluerock':'Bluerock','cantor-fitzgerald':'Cantor','exchangeright':'ExchangeRight',
 'four-springs-capital':'Four Springs','griffin-capital':'Griffin','hamilton-point-investments':'Hamilton Point',
 'inland':'Inland','livingston-street-capital':'Livingston Street Capital','moody-national':'Moody',
 'net-lease-capital-advisors':'NLCA','nexpoint':'NexPoint','olympus-property':'Olympus','passco':'Passco',
 'peachtree-group':'Peachtree','syndicated-equities':'Syndicated Equities','core':'CORE','ideal-capital-group':'IDEAL',
 'arctrust':'ARCTRUST','blue-door':'Blue Door','bridgeview':'Bridgeview','capital-square':'Capital Square',
 'carter-exchange':'Carter Exchange','denholtz':'Denholtz','starboard-realty-advisors':'Starboard Realty',
 'time-equities':'Time Equities','walton-global-holdings':'Walton Global'}

def clean(s): return html.unescape(s or '').replace('–','-').replace('—','-').strip()
def norm(s):  return re.sub(r'[^a-z0-9]','',clean(s).lower())
def stem(s):
    s = re.split(r'\s+-\s+', clean(s))[0]
    s = re.sub(r'\b(dst|llc|l\.l\.c\.|inc\.?|lp|l\.p\.|fund|the)\b','',s,flags=re.I)
    return re.sub(r'[^a-z0-9]','',s.lower())
def num(s):
    s = re.sub(r'[^0-9.\-]','',str(s or ''))
    try: return float(s)
    except ValueError: return None

# ---- source A: the Results dataset ----
deals, bysp = [], defaultdict(list)
for i, r in enumerate(csv.reader(open(FC+'fullcycle.orig.tsv'), delimiter='\t')):
    if i == 0: continue
    r = [c.strip() for c in r] + ['']*(7-len(r))
    if not r[0]: continue
    d = dict(name=r[0], sponsor=r[1], type=r[2], state=r[3], ret=num(r[4]), em=num(r[5]), hold=num(r[6]),
             city='', src='results', used=False)
    deals.append(d); bysp[r[1]].append(d)

# ---- source B: the sponsor-page tables ----
pages = json.load(open(SP+'page_deals.json'))
def pagerow(d):
    name, loc, ac, hold, em, ret = (list(d)+['']*6)[:6]
    loc = clean(loc); loc = '' if loc in ('-','') else loc
    city, sep, st = loc.rpartition(',')
    if not sep: city, st = ('', loc) if len(loc) == 2 else (loc, '')
    return dict(name=clean(name), city=city.strip(), state=st.strip(), type=clean(ac),
                hold=num(hold), em=num(em), ret=(num(ret)/100 if num(ret) is not None else None))

added, pairs, dropped, unmapped = [], [], 0, []
for slug in sorted(pages):
    sponsor = SLUG2SPONSOR[slug]
    cand = bysp[sponsor]
    rows = [pagerow(d) for d in pages[slug]]
    def take(pool, p):
        if len(pool) > 1 and p['hold'] is not None:
            pool = sorted(pool, key=lambda c: abs((c['hold'] if c['hold'] is not None else 1e9) - p['hold']))
        t = pool[0]; t['used'] = True
        if not t['city'] and p['city']: t['city'] = p['city']
        if not t['state'] and p['state']: t['state'] = p['state']
        if not t['type'] and p['type']: t['type'] = p['type']
        for f in ('ret','em','hold'):
            if t[f] is None and p[f] is not None: t[f] = p[f]
        pairs.append((sponsor, p, t))
    rest = []
    for p in rows:
        if (sponsor, p['name']) in DROP: dropped += 1; continue
        want = ALIAS.get((sponsor, p['name']))
        pool = [c for c in cand if not c['used'] and norm(c['name']) == norm(want or p['name'])]
        if pool and p['state'] and not want:
            byst = [c for c in pool if c['state'] == p['state']]
            if byst: pool = byst
        if pool: take(pool, p)
        else: rest.append(p)
    rest2 = []
    for p in rest:
        pool = [c for c in cand if not c['used'] and stem(c['name']) == stem(p['name'])
                and (not p['state'] or not c['state'] or c['state'] == p['state'])]
        if pool: take(pool, p)
        else: rest2.append(p)
    for p in rest2:
        pool = [c for c in cand if not c['used']
                and difflib.SequenceMatcher(None, norm(c['name']), norm(p['name'])).ratio() >= 0.70
                and (p['hold'] is None or c['hold'] is None or abs(c['hold']-p['hold']) <= max(0.15, 0.02*p['hold']))]
        if pool:
            pool.sort(key=lambda c: -difflib.SequenceMatcher(None, norm(c['name']), norm(p['name'])).ratio())
            take(pool, p)
        else:
            d = dict(name=p['name'], sponsor=sponsor, type=p['type'], state=p['state'], ret=p['ret'],
                     em=p['em'], hold=p['hold'], city=p['city'], src='sponsor-page', used=True)
            deals.append(d); bysp[sponsor].append(d); added.append(d)

def fmt(v, nd=6):
    return '' if v is None else (('%.*f' % (nd, v)).rstrip('0').rstrip('.') or '0')
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['Investment Name','Sponsor','Property Type','Location','Average Annual Return','Equity Multiple','Holding Period','City'])
    for d in deals:
        w.writerow([d['name'], d['sponsor'], d['type'], d['state'], fmt(d['ret']), fmt(d['em']), fmt(d['hold']), d['city']])

print('master dataset: %d deals across %d sponsors' % (len(deals), len({d['sponsor'] for d in deals})))
print('  %d rows carried over from the Results dataset' % (len(deals)-len(added)))
print('  %d rows added from sponsor-page tables' % len(added))
print('  %d page rows matched an existing Results row (%d page roll-ups dropped in favour of their components)' % (len(pairs), dropped))

# ---- conflict report ----
TOL = {'ret':0.0015,'em':0.02,'hold':0.06}
conf = defaultdict(lambda: defaultdict(list))
for sponsor, p, t in pairs:
    for f in ('ret','em','hold'):
        if p[f] is not None and t[f] is not None and abs(p[f]-t[f]) > TOL[f]:
            conf[sponsor][f].append((t['name'], p[f], t[f]))
json.dump({'added':[{k:v for k,v in d.items() if k!='used'} for d in added],
           'conflicts':{s:{f:v for f,v in d.items()} for s,d in conf.items()}}, open(FC+'merge_detail.json','w'), indent=1)
print('\nsponsors where the page table and the Results dataset disagreed (page value replaced by the Results value):')
print('  %-24s %-14s %-14s %-14s' % ('sponsor','avg return','equity multiple','hold'))
for s in sorted(conf):
    c = conf[s]
    cell = lambda f: ('%d deals' % len(c[f])) if c.get(f) else '—'
    print('  %-24s %-14s %-14s %-14s' % (s, cell('ret'), cell('em'), cell('hold')))

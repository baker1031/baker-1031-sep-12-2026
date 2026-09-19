"""Pull the live inventory from the Opportunities tool (opportunities.baker1031.com) into build/offerings.json,
in exactly the record shape the page builders already use, and cache each property photo and offering document.

This replaced fetch_airtable.py on 2026-09-19: the Opportunities tool is now the source of truth for offerings
(it computes Availability Status and Coverage Rating itself, and keeps the documents in Dropbox). Every change
made there marks the site dirty and the tool fires this site's build hook about a minute after edits settle.

Env:
  OPPORTUNITIES_FEED      defaults to https://opportunities.baker1031.com/api/public/opportunities
  OPPORTUNITIES_FEED_KEY  the tool's FEED_KEY — required to download offering documents (they stay behind this
                          site's investor login; the feed itself never hands out public document links)
  SITE_ROOT               repo root (defaults to the parent of this file)

Only offerings with "Show on website" on reach the feed, and only documents toggled to Website are listed.
If the feed is unreachable or empty, the committed offerings.json snapshot is kept, so a bad pull never
takes the inventory down.
"""
import json, os, re, sys, time, urllib.request, urllib.parse, urllib.error
from us_spelling import americanise
from fetch_airtable import derive, safe_name, download, hold_years, EXT, IMG_DIR, PROSE_FIELDS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('SITE_ROOT') or os.path.dirname(HERE)
FEED = os.environ.get('OPPORTUNITIES_FEED', 'https://opportunities.baker1031.com/api/public/opportunities')
KEY = (os.environ.get('OPPORTUNITIES_FEED_KEY') or '').strip()
OUT_JSON = os.path.join(HERE, 'offerings.json')


def get_json(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'baker1031-site-build'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < 3: time.sleep(2 * (attempt + 1)); continue
            raise


def money(n):
    return '' if n is None else '${:,.0f}'.format(n)


def to_record(o):
    """Feed opportunity -> the offerings.json shape the builders read (same keys fetch_airtable.py produced)."""
    def ext(name):
        m = re.search(r'\.[A-Za-z0-9]{1,6}$', name or '')
        return m.group(0) if m else '.pdf'
    r = {
        'id': o['id'], 'name': o['name'], 'sponsor': o.get('sponsor') or '', 'status': o.get('status'),
        'registration': o.get('registration') or '', 'equity': o.get('equity'), 'debt': o.get('debt') or 0,
        'total': o.get('total'), 'ltv': o.get('ltv') or 0, 'lender': o.get('lender') or '',
        'rate': o.get('rate') or ('{:.2f}% fixed'.format(o['interestRate'] * 100) if o.get('interestRate') else ''),
        'amort': o.get('amortization') or '', 'loanTerm': o.get('loanTerm'), 'holdLabel': o.get('holdLabel') or '',
        'coverage': o.get('coverageReview'), 'cfBasis': o.get('cashFlowBasis') or '', 'postForecast': o.get('postForecast') or '',
        'cfDisclosure': o.get('cashFlowDisclosure') or '', 'purchasePrice': o.get('purchasePrice'),
        'reserves': o.get('initialReserves'), 'addresses': o.get('addresses') or '', 'slug': o.get('slug'),
        'modified': o.get('updatedAt'), 'sourceNotes': o.get('sourceNotes') or '', 'numProperties': o.get('numProperties'),
        'numTenants': o.get('numTenants') or '', 'walt': o.get('walt') or '', 'minPurchase': money(o.get('minInvestment')),
        'exit721Route': o.get('exit721Route') or '', 'types': o.get('assetClasses') or [], 'locations': o.get('locations') or [],
        'exit721': o.get('exchange721') or 'None', 'description': o.get('description') or '', 'notes': o.get('notes') or '',
        'highlights': [h for h in (o.get('highlights') or []) if h],
    }
    if not r['holdLabel'] and o.get('holdPeriod'): r['holdLabel'] = '%d Years' % o['holdPeriod']
    r['hold'] = hold_years(r['holdLabel'])
    inc = list(o.get('incomeYears') or [])[:10]
    r['income'] = inc + [None] * (10 - len(inc))
    for k in PROSE_FIELDS:
        if isinstance(r.get(k), str): r[k] = americanise(r[k])
    r['highlights'] = [americanise(h) for h in r['highlights']]
    r['image'] = [{'url': o['photoUrl'], 'v': str(o.get('photoV') or '1')}] if o.get('photoUrl') else []
    # Documents are named on the house convention "<Investment Name> - <Type>.<ext>", whatever the file is
    # called in Dropbox; the page builder shows the name without its extension.
    r['docs'] = [{'filename': f"{o['name']} - {d.get('type') or 'Document'}{ext(d.get('name'))}", 'url': d['url'], 'size': d.get('size')}
                 for d in (o.get('documents') or [])]
    return r


def fetch_photo(r):
    if not r['image']: return False
    im = r['image'][0]
    stamp = os.path.join(IMG_DIR, r['slug'] + '.src')
    if os.path.exists(stamp) and open(stamp).read().strip() == 'opp:' + im['v'] and \
       os.path.exists(os.path.join(IMG_DIR, r['slug'] + '-card.jpg')):
        return False
    try:
        with urllib.request.urlopen(urllib.request.Request(im['url'], headers={'User-Agent': 'baker1031-site-build'}), timeout=120) as resp:
            ext = EXT.get((resp.headers.get('content-type') or '').split(';')[0], 'jpg')
            data = resp.read()
    except Exception as e:
        print('  photo download failed:', r['slug'], e); return False
    dest = os.path.join(IMG_DIR, f"{r['slug']}.{ext}")
    with open(dest, 'wb') as fh: fh.write(data)
    derive(dest, r['slug'])
    open(stamp, 'w').write('opp:' + im['v'])
    return True


def localize_docs(recs):
    """Same contract as fetch_airtable.localize_docs: files land in offerings/<slug>/docs/ (hard-gated at the edge)
    and each doc gets d['rel']. Downloads go through the feed with the site's key."""
    if os.environ.get('SKIP_DOCS'): return 0
    if not KEY:
        print('WARNING: OPPORTUNITIES_FEED_KEY not set — offering documents are listed but not downloaded.'); return 0
    n = 0
    for o in recs:
        if not o['docs']: continue
        ddir = os.path.join(ROOT, 'offerings', o['slug'], 'docs'); os.makedirs(ddir, exist_ok=True)
        used = set()
        for d in o['docs']:
            name = safe_name(d['filename'])
            while name.lower() in used:
                stem, ext = os.path.splitext(name); name = stem + '_1' + ext
            used.add(name.lower())
            dest = os.path.join(ddir, name)
            if not (os.path.exists(dest) and d.get('size') and os.path.getsize(dest) == d['size']):
                if not download(d['url'] + ('&' if '?' in d['url'] else '?') + 'key=' + urllib.parse.quote(KEY), dest):
                    continue
            d['rel'] = f"/offerings/{o['slug']}/docs/{urllib.parse.quote(name)}"; n += 1
    return n


def main():
    try:
        feed = get_json(FEED)
    except Exception as e:
        print(f'WARNING: Opportunities feed unreachable ({e}). Keeping the committed offerings.json snapshot.'); return 0
    recs = [to_record(o) for o in feed.get('opportunities', []) if o.get('name') and o.get('slug')]
    if not recs:
        print('WARNING: the Opportunities feed returned no publishable offerings. Keeping the committed offerings.json snapshot.')
        return 0
    recs.sort(key=lambda o: o['name'].lower())
    dupes = sorted({o['slug'] for o in recs if [x['slug'] for x in recs].count(o['slug']) > 1})
    if dupes: print('WARNING: two offerings share a slug, so one will overwrite the other: ' + ', '.join(dupes))
    os.makedirs(IMG_DIR, exist_ok=True)
    fetched = sum(1 for o in recs if fetch_photo(o))
    ndocs = localize_docs(recs)
    for o in recs:
        for d in o['docs']: d.pop('url', None)     # the feed URL stays out of the build output
    json.dump(recs, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'offerings (from the Opportunities tool): {len(recs)} records, {fetched} photos refreshed, {ndocs} documents')
    return 0


if __name__ == '__main__':
    sys.exit(main())

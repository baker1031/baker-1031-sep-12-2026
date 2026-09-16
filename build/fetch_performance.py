"""Refresh build/fullcycle.tsv — the full-cycle dataset behind the Results page, the homepage chart and every
sponsor-page track record — from the "Investment Data (Live)" Airtable base at build time.

Env:
  AIRTABLE_TOKEN        personal access token with data.records:read on the Investment Data (Live) base (required)
  PERFORMANCE_BASE      defaults to appTSWSTIsB2arukB   (Investment Data (Live))
  PERFORMANCE_TABLE     defaults to tblucuax2b7dKxLzH   (Past Performance)
  SITE_ROOT             repo root (defaults to the parent of this file)

Published performance figures are compliance-sensitive, so this script never fails the build and never
publishes a partial pull: without a token, on any Airtable error, or if the pull comes back materially
smaller than the committed snapshot, it keeps the committed build/fullcycle.tsv and says so loudly.
The committed file is therefore always a valid, reviewed dataset — Airtable only ever moves it forward.

Average Annual Return comes from the base's own comparable-return field, which is
(Equity Multiple - 1) / Holding Period for every sponsor: simple, not compounded, and not an IRR.
"""
import csv, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('SITE_ROOT') or os.path.dirname(HERE)
TOKEN = (os.environ.get('AIRTABLE_TOKEN') or '').strip()
BASE = os.environ.get('PERFORMANCE_BASE', 'appTSWSTIsB2arukB')
TABLE = os.environ.get('PERFORMANCE_TABLE', 'tblucuax2b7dKxLzH')
OUT = os.path.join(HERE, 'fullcycle.tsv')

# Airtable field id -> TSV column. Return is a percent field: Airtable hands it back as a decimal
# fraction (0.2071 = 20.71%), which is exactly what fullcycle.py expects.
F_NAME   = 'fldFUEZ5c2n8Os5bR'
F_SPONSOR= 'fldnTsVdueGIaIjij'
F_TYPE   = 'fldCJEHrHi7SuuMXx'
F_LOC    = 'fldIReVDzcPwjZQSj'
F_RET    = 'flduMdFTmX8XwcSnB'
F_EM     = 'fldZUF33USheQ1XIR'
F_HOLD   = 'fldgNZUMjiU8bbh2p'

HEADER = ['Investment Name', 'Sponsor', 'Property Type', 'Location', 'Average Annual Return',
          'Equity Multiple', 'Holding Period', 'City', 'Location Note']
CITY_STATE = re.compile(r'^(.+),\s*([A-Z]{2})$')
# Below this share of the committed row count the pull is treated as broken rather than as a real shrink.
MIN_SHARE = 0.8


def api(url):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(2 * (attempt + 1)); continue
            raise


def fetch_records():
    records, offset = [], None
    while True:
        q = {'returnFieldsByFieldId': 'true', 'pageSize': 100}
        if offset: q['offset'] = offset
        data = api(f'https://api.airtable.com/v0/{BASE}/{TABLE}?' + urllib.parse.urlencode(q))
        records += data.get('records', [])
        offset = data.get('offset')
        if not offset: break
    return records


def txt(v):
    if isinstance(v, dict) and 'name' in v: v = v['name']
    if isinstance(v, list): v = ', '.join(txt(x) for x in v)
    return re.sub(r'\s+', ' ', str(v if v is not None else '')).strip()


def num(v, places):
    if v is None or v == '': return ''
    try: return ('%.*f' % (places, float(v))).rstrip('0').rstrip('.')
    except (TypeError, ValueError): return ''


def row(rec):
    """One TSV row. Location splits into City + Location (state) when it reads "City, ST"; anything else
    ("Not disclosed in PPM", "Canada - Ontario") is kept verbatim in Location Note so nothing is invented."""
    f = rec.get('fields', {})
    loc, city, state, note = txt(f.get(F_LOC)), '', '', ''
    m = CITY_STATE.match(loc)
    if m: city, state = m.group(1).strip(), m.group(2)
    elif loc: note = loc
    return [txt(f.get(F_NAME)), txt(f.get(F_SPONSOR)), txt(f.get(F_TYPE)), state,
            num(f.get(F_RET), 6), num(f.get(F_EM), 6), num(f.get(F_HOLD), 6), city, note]


def committed_rows():
    if not os.path.exists(OUT): return 0
    with open(OUT, encoding='utf-8') as fh:
        return sum(1 for r in csv.reader(fh, delimiter='\t') if r and r[0].strip()) - 1


def keep(msg):
    print('WARNING: %s Keeping the committed build/fullcycle.tsv.' % msg)
    return 0


def main():
    have = committed_rows()
    if not TOKEN:
        print('AIRTABLE_TOKEN not set — keeping the committed fullcycle.tsv snapshot (%d deals).' % have)
        return 0
    try:
        recs = fetch_records()
    except urllib.error.HTTPError as e:
        hint = {401: 'the token is invalid or expired',
                403: 'the token has no access to the Investment Data (Live) base or lacks data.records:read',
                404: 'base/table id not found for this token'}.get(e.code, '')
        return keep('Airtable returned HTTP %d%s.' % (e.code, ' — ' + hint if hint else ''))
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return keep('Airtable unreachable (%s).' % e)

    rows = [row(r) for r in recs]
    rows = [r for r in rows if r[0] and r[1]]          # a deal needs a name and a sponsor to be publishable
    if not rows:
        return keep('Airtable returned no usable rows.')
    if have and len(rows) < have * MIN_SHARE:
        return keep('Airtable returned only %d rows against %d committed — that looks like a bad pull, '
                    'not a real change.' % (len(rows), have))

    buf = io.StringIO()
    w = csv.writer(buf, delimiter='\t', lineterminator='\n', quoting=csv.QUOTE_NONE, escapechar=None)
    w.writerow(HEADER)
    for r in rows:
        w.writerow([c.replace('\t', ' ') for c in r])
    with open(OUT, 'w', encoding='utf-8', newline='') as fh:
        fh.write(buf.getvalue())

    sponsors = sorted({r[1] for r in rows})
    print('performance: %d full-cycle deals, %d sponsors (%s)%s'
          % (len(rows), len(sponsors), ', '.join(sponsors),
             '' if not have else ' — was %d' % have))
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Pull the Offering Data table from the "Investment Data (Live)" Airtable base into build/offerings.json and
cache each property photo under assets/media/offerings/ — the full-resolution original (<slug>.<ext>) plus
-card.jpg (800px) and -hero.jpg (1600px) derived with Pillow (see requirements.txt). Standard library
otherwise, so it runs on Netlify's build image as-is.

Env:
  AIRTABLE_TOKEN  personal access token with data.records:read on the Investment Data (Live) base (required)
  AIRTABLE_BASE   defaults to appTSWSTIsB2arukB   (Investment Data (Live))
  AIRTABLE_TABLE  defaults to tblMiNHG8EGFcvngt   (Offering Data)
  SITE_ROOT       repo root (defaults to the parent of this file)

This replaced the older Investment Offerings base (appQOBBscRLzaWv8G / DST Offerings) on 2026-09-16. That
base held 50 offerings whose figures came from several vintages of review; this one holds the 19 whose
numbers were independently recomputed from the sponsor's own PPM, which is why the cutover shrinks the
published inventory. Offerings that were published from the old base and are not in this one are redirected
to /invest/ by netlify/edge-functions/gate.js rather than being left to 404.

The Investor Access base is deliberately NOT read here — nothing about investors belongs in a static build.
"""
import json, os, re, sys, time, urllib.request, urllib.parse, urllib.error
from us_spelling import americanise  # sponsor copy arrives with British spellings; this is a US site

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('SITE_ROOT') or os.path.dirname(HERE)
TOKEN = (os.environ.get('AIRTABLE_TOKEN') or '').strip()
BASE = os.environ.get('AIRTABLE_BASE', 'appTSWSTIsB2arukB')
TABLE = os.environ.get('AIRTABLE_TABLE', 'tblMiNHG8EGFcvngt')
OUT_JSON = os.path.join(HERE, 'offerings.json')
IMG_DIR = os.path.join(ROOT, 'assets', 'media', 'offerings')

# Airtable field id -> key used by the build scripts
FIELDS = {
    'fldFlxiyklPqF4T0a':'name', 'fldYEtjEv7kQSZFAy':'sponsor', 'fld9jh52kuZ2zVhDC':'status',
    'fldBRCkfs1QG6BJsN':'registration', 'fldjmcRLhP0FBcIO1':'locationsRaw', 'fldGqXfGKD69OgZla':'typesRaw',
    'fldgZqPdhKZyfyhbb':'exit721Raw', 'fldiPlvm7WgbdvCvX':'equity', 'fldn9Gv1errQk8VaO':'debt',
    'fldWU6alOuFcx90Md':'total', 'fldskeVquYXGI6GEV':'ltv', 'fldGg6yuEgKRhGHAS':'lender',
    'fldthme58Hpkncy6t':'rate', 'fld9siCPbF95cjHJG':'amort', 'fld9RUkGMXITeqa2R':'loanTerm',
    'fld1YYB7aTI9SjJlP':'holdLabel', 'fldkVeNqsx73FWx0O':'description', 'fldHUCuo3VtJDoKyW':'notes',
    'fldOAGADWecOUeKzm':'coverage', 'fldGJPHMRLgPvssxh':'cfBasis', 'fldxX3mLiMAneAji7':'postForecast',
    'fldqrpWHZ1poKEtTJ':'cfDisclosure', 'fldcZNbjVjiROffMz':'purchasePrice', 'fldmAEAwUzSCVQUGt':'reserves',
    'fldYadYU5kykRbr4s':'addresses', 'fldCwzRd8LQDMhIc1':'slug', 'fldGrBxWmK0zm4Qe5':'modified',
    'fldpl3EhHv5ZMLETv':'sourceNotes', 'fldYJ1OOaoRkBJrSg':'numProperties', 'fldsKY6HGRePNZGWA':'numTenants',
    'fldyzgCTy0JCVkv0I':'walt', 'fldao25VojerpK35s':'minPurchase', 'fldiAkefsGLaWKeI0':'exit721Route',
}
INCOME = ['fld4G8ys3a8AZ5l2b','fld6QuTKjblRihzvc','fldrQbQvEBviPN80h','fldbcNZmUTVUYFUqg','flduFGbkRST1TD8HR',
          'fld04PHjh8cgJCqVo','fldG6EeJNogAJeU4K','fldLQzFaRFJmGZkQ3','fldji03bIBSKGskgP','fld6ttlu9qrlEXQpc']
HIGHLIGHTS = ['fldlczAjckoxwoQwc','fldueo5r7KGWsZ5XQ','fldKU0v1rrsAllc0z','fldhci7I6revPgxsC','fldyjLMoR8kySZ6KC']
IMAGE, DOCS = 'fldMtlBCSmxEie2Gl', 'fldgAkYFT8J3y9nLF'

# The inventory page filters and sorts on three values (mandatory / optional / none); Airtable says
# Required / Optional / None. "Required" and "mandatory" are the same thing — a forced exchange at exit.
EXIT721 = {'required': 'Mandatory', 'mandatory': 'Mandatory', 'optional': 'Optional', 'none': 'None'}


def api(url):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3: time.sleep(2 * (attempt + 1)); continue
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

def norm(v):
    if isinstance(v, dict) and 'name' in v: return v['name']
    if isinstance(v, list): return [norm(x) for x in v]
    return v

def split_types(s):
    """"Net-Lease Retail, Healthcare" -> two types; "Marina (two marina / boatyard facilities)" -> one.
    Commas inside brackets are part of the label, not separators."""
    out, depth, cur = [], 0, ''
    for ch in str(s or ''):
        if ch in '([': depth += 1
        elif ch in ')]': depth = max(0, depth - 1)
        if ch == ',' and depth == 0:
            out.append(cur); cur = ''
        else:
            cur += ch
    out.append(cur)
    return [t.strip() for t in out if t.strip()]

def hold_years(label):
    """Numeric hold for the inventory's sort and filters. A range takes its upper bound, because that is the
    length an investor has to be able to sit through; "No Fixed Hold" has no number and stays None."""
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', str(label or ''))]
    return max(nums) if nums else None

# Long-form fields the sponsor copy lands in. Their British spellings are normalised on the way in, so
# the fix survives every re-fetch instead of having to be reapplied to Airtable by hand.
PROSE_FIELDS = ('name', 'description', 'notes', 'sourceNotes', 'cfDisclosure', 'cfBasis', 'amort',
                'exit721Route', 'postForecast', 'addresses', 'holdLabel', 'lender', 'rate')


def normalize(rec):
    f = rec.get('fields', {})
    o = {'id': rec['id']}
    for fid, key in FIELDS.items():
        v = norm(f.get(fid))
        o[key] = americanise(v) if key in PROSE_FIELDS else v
    o['types'] = split_types(o.pop('typesRaw'))
    o['locations'] = [x.strip() for x in str(o.pop('locationsRaw') or '').split(';') if x.strip()]
    o['exit721'] = EXIT721.get(str(o.pop('exit721Raw') or 'none').strip().lower(), 'None')
    o['hold'] = hold_years(o['holdLabel'])
    o['income'] = [f.get(x) for x in INCOME]
    o['highlights'] = [americanise(f.get(x)) for x in HIGHLIGHTS if f.get(x)]
    o['image'] = [{'url': i['url'], 'large': (i.get('thumbnails') or {}).get('large', {}).get('url'),
                   'filename': i.get('filename'), 'type': i.get('type')} for i in (f.get(IMAGE) or [])]
    o['docs'] = [{'filename': d.get('filename'), 'url': d.get('url'), 'size': d.get('size')} for d in (f.get(DOCS) or [])]
    return o

def download(url, dest):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=180) as r, open(dest, 'wb') as fh:
                fh.write(r.read())
            return True
        except Exception as e:
            if attempt == 2: print('  image download failed:', dest, e); return False
            time.sleep(2)

EXT = { 'image/png':'png', 'image/jpeg':'jpg', 'image/webp':'webp', 'image/gif':'gif' }

def derive(original, slug):
    """Write <slug>-card.jpg (800px, inventory cards) and <slug>-hero.jpg (1600px, offering page) next to the
    full-resolution original. Needs Pillow (requirements.txt); without it the pages fall back to the original."""
    try:
        from PIL import Image
    except ImportError:
        print('  Pillow not installed — pages will use the original image'); return
    im = Image.open(original)
    if im.mode not in ('RGB', 'L'):
        bg = Image.new('RGB', im.size, (255, 255, 255)); bg.paste(im.convert('RGBA'), mask=im.convert('RGBA').split()[-1]); im = bg
    else:
        im = im.convert('RGB')
    for suffix, width, q in (('-card', 800, 80), ('-hero', 1600, 85)):
        w, h = im.size
        out = im if w <= width else im.resize((width, round(h * width / w)), Image.LANCZOS)
        out.save(os.path.join(IMG_DIR, f'{slug}{suffix}.jpg'), 'JPEG', quality=q, optimize=True, progressive=True)

def safe_name(s):
    return re.sub(r'\s+', ' ', re.sub(r'[\/\\:*?"<>|#%]+', '_', str(s or 'document'))).strip()[:120]

def localize_docs(recs):
    """Offering documents (PPMs, supplements) are served from offerings/<slug>/docs/<file> so the edge gate can
    hard-gate them behind a login. Airtable attachment URLs expire within hours, so the files are downloaded at
    build time (skipped when a file of the same size is already present). Each record gets docs[i]['rel']."""
    if os.environ.get('SKIP_DOCS'): return 0
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
                if not download(d['url'], dest):
                    continue
            d['rel'] = f"/offerings/{o['slug']}/docs/{urllib.parse.quote(name)}"; n += 1   # URL-safe (file names carry spaces)
    return n

def main():
    if not TOKEN:
        print('AIRTABLE_TOKEN not set — keeping the committed offerings.json snapshot.'); return 0
    try:
        recs = [normalize(r) for r in fetch_records()]
    except urllib.error.HTTPError as e:
        # A bad or under-scoped token must not take the site down: keep the committed snapshot and say so loudly.
        hint = {401: 'the token is invalid or expired (legacy Airtable API keys no longer work — create a personal access token)',
                403: 'the token has no access to the Investment Data (Live) base or lacks the data.records:read scope',
                404: 'base/table id not found for this token'}.get(e.code, '')
        print(f'WARNING: Airtable returned HTTP {e.code}{" — " + hint if hint else ""}. Keeping the committed offerings.json snapshot; fix AIRTABLE_TOKEN in Netlify to resume Airtable-driven builds.')
        return 0
    except (urllib.error.URLError, TimeoutError) as e:
        print(f'WARNING: Airtable unreachable ({e}). Keeping the committed offerings.json snapshot.'); return 0
    # An offering with no slug has no address to be published at, so it is held back rather than guessed at.
    noslug = [o['name'] for o in recs if o.get('name') and not o.get('slug')]
    if noslug:
        print('WARNING: no Slug set in Airtable, so these are not published: ' + '; '.join(noslug))
    recs = [o for o in recs if o.get('name') and o.get('slug')]
    if not recs:
        print('WARNING: Airtable returned no publishable offerings. Keeping the committed offerings.json snapshot.')
        return 0
    recs.sort(key=lambda o: o['name'].lower())
    dupes = sorted({o['slug'] for o in recs if [x['slug'] for x in recs].count(o['slug']) > 1})
    if dupes:
        print('WARNING: two offerings share a slug, so one will overwrite the other: ' + ', '.join(dupes))
    norating = [o['name'] for o in recs if not o.get('coverage')]
    if norating:
        print('NOTE: no Coverage Rating set, so these publish as Specialized: ' + '; '.join(norating))
    os.makedirs(IMG_DIR, exist_ok=True)
    fetched = 0
    for o in recs:
        if not o['image']: continue
        im = o['image'][0]
        ext = EXT.get(im.get('type') or '') or (os.path.splitext(im.get('filename') or '')[1].lstrip('.').lower() or 'jpg')
        dest = os.path.join(IMG_DIR, f"{o['slug']}.{ext}")
        stamp = os.path.join(IMG_DIR, o['slug'] + '.src')
        src_id = im['url'].split('/')[-1]            # attachment ids change when the photo is replaced in Airtable
        if os.path.exists(dest) and os.path.exists(stamp) and open(stamp).read().strip() == src_id \
           and os.path.exists(os.path.join(IMG_DIR, o['slug'] + '-card.jpg')):
            continue
        if download(im['url'], dest):                # full-resolution original, as uploaded to Airtable
            derive(dest, o['slug'])
            open(stamp, 'w').write(src_id); fetched += 1
    ndocs = localize_docs(recs)
    json.dump(recs, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'offerings: {len(recs)} records, {fetched} photos refreshed, {ndocs} documents')
    return 0

if __name__ == '__main__':
    sys.exit(main())

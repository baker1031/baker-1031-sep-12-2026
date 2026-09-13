"""Pull the DST Offerings table from Airtable into build/offerings.json and cache each property photo
under assets/media/offerings/ — the full-resolution original (<slug>.<ext>) plus -card.jpg (800px) and -hero.jpg (1600px)
derived with Pillow (see requirements.txt). Standard library otherwise, so it runs on Netlify's build image as-is.

Env:
  AIRTABLE_TOKEN  personal access token with data.records:read on the Investment Offerings base (required)
  AIRTABLE_BASE   defaults to appQOBBscRLzaWv8G   (Investment Offerings)
  AIRTABLE_TABLE  defaults to tblzgE24oqN8d5VZj   (DST Offerings)
  SITE_ROOT       repo root (defaults to the parent of this file)

The Investor Access base is deliberately NOT read here — nothing about investors belongs in a static build.
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('SITE_ROOT') or os.path.dirname(HERE)
TOKEN = os.environ.get('AIRTABLE_TOKEN')
BASE = os.environ.get('AIRTABLE_BASE', 'appQOBBscRLzaWv8G')
TABLE = os.environ.get('AIRTABLE_TABLE', 'tblzgE24oqN8d5VZj')
OUT_JSON = os.path.join(HERE, 'offerings.json')
IMG_DIR = os.path.join(ROOT, 'assets', 'media', 'offerings')

# Airtable field id -> key used by the build scripts
FIELDS = {
    'fld3mj3JrNOrlYSTP':'name', 'fldzHclKwUjC9FWs9':'sponsor', 'fld9x6OUZctsnfaUa':'status', 'fldEq9QAZ756bcPVh':'registration',
    'fldrKSI6lSzC2viOV':'locations', 'flddQfzyic6srg1dW':'types', 'fldW0gX9y9atvyunA':'exit721', 'fldFoOMNNJIAlyQ2l':'equity',
    'fldHFrsuOAWNLkp4T':'debt', 'fldUEn7Y1eZYcwIoT':'total', 'fldPX1y0caLZto3bw':'ltv', 'fldszEYHQEyNXKT8z':'lender',
    'fldNenQLbjVeZZt0S':'rate', 'fldj3VLiCqOsnOE3d':'amort', 'fld0VD4t9cgkkMTFh':'loanTerm', 'fldGzTyKWomvLjrHd':'incomeAvg',
    'fldtR2nA0uDPUMnYH':'hold', 'fld8sYZXysmWis1G1':'description', 'fldD9Ew3ZhAmFQNnl':'notes', 'fld7aDH0ASO7a9KJE':'coverage',
    'fld9NuzTtvNQb5sTm':'cfBasis', 'fldVk8cc6qchP234d':'cfThrough', 'fldmw7weROo2ugGSV':'postForecast', 'fldH33Q8nHPvWiIhI':'cfDisclosure',
    'fldUwOgFDWLIfk6eq':'purchasePrice', 'fldB86oZCUV4NLUL4':'reserves', 'fldzEkCGZujSBzBWQ':'load', 'fldjyg5z9wK7V2xuo':'loadYears',
    'fldKd14gcHp0E3jib':'addresses', 'fldso3riT9A6eqlps':'slug', 'fld45JlTWioHALWKg':'modified',
}
INCOME = ['flddVrtTP6W9nKlLn','fldW23lo8a6k9Q98H','fld6ProsoeKQspxzv','fld3jaWeFjKVRg6gU','fldmXRyMzo65doWP5',
          'fldMg6weMO3xj8mrP','fldcyqyKc0As77VZx','fldatzmxcABw7CBOQ','fldDbXnB3WYsugIRU','fldfKhgCxRfRNYZma']
HIGHLIGHTS = ['fldrcBjr5YEPLqXiH','fldjOjluCGPIDyqgS','fldIQwtS1WbSe0Jjd','fldyLYja6NM9dOGaX','fldzF3Y3JulNrSSPs']
IMAGE, DOCS = 'fldxvcaGAsAFf2PaA', 'fldd3kAtEFgv1v0v4'

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

def normalize(rec):
    f = rec.get('fields', {})
    o = {'id': rec['id']}
    for fid, key in FIELDS.items(): o[key] = norm(f.get(fid))
    o['income'] = [f.get(x) for x in INCOME]
    o['highlights'] = [f.get(x) for x in HIGHLIGHTS if f.get(x)]
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
    import re
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
            d['rel'] = f"/offerings/{o['slug']}/docs/{name}"; n += 1
    return n

def main():
    if not TOKEN:
        print('AIRTABLE_TOKEN not set — keeping the committed offerings.json snapshot.'); return 0
    recs = [normalize(r) for r in fetch_records()]
    recs = [o for o in recs if o.get('name') and o.get('slug')]
    recs.sort(key=lambda o: o['name'].lower())
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

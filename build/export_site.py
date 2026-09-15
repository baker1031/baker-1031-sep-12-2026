"""Export the built pages into the deployable repo tree (/home/claude/site):
- committed pages: index.html, /register/, /login/, /results/ (base64 media extracted to /assets/media/<name>.<ext>)
- content sources: content/pages/** (section-page fragments), content/articles/*.md (Learn library)
- build tooling in build/ (the same scripts Netlify runs), Netlify functions + edge gate, netlify.toml, README
- then runs build/build.py exactly the way Netlify does, so /invest, /offerings/*, the content sections, /learn and
  the crawl files are generated locally too (for verification; they are build products and are git-ignored).
"""
import re, os, base64, hashlib, shutil, json, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo
SRC = '/home/claude'
OUT = '/home/claude/site'
SP = os.path.dirname(os.path.abspath(__file__)) + '/'
V2 = '/home/claude/v2'
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT + '/assets/media/offerings', exist_ok=True)

EXT = { 'image/png':'png', 'image/jpeg':'jpg', 'image/webp':'webp', 'image/svg+xml':'svg', 'image/gif':'gif', 'video/mp4':'mp4', 'video/webm':'webm', 'font/woff2':'woff2' }
seen = {}
DATA_RE = re.compile(r'data:(image/(?:png|jpeg|webp|gif)|video/(?:mp4|webm));base64,([A-Za-z0-9+/=]+)')
NAMED = {}   # well-known assets get readable names

def extract(html):
    def sub(m):
        mime, b64 = m.group(1), m.group(2)
        raw = base64.b64decode(b64)
        h = hashlib.sha1(raw).hexdigest()[:12]
        name = NAMED.get(h, h) + '.' + EXT[mime]
        path = OUT + '/assets/media/' + name
        if h not in seen:
            open(path, 'wb').write(raw); seen[h] = name
        return '/assets/media/' + name
    return DATA_RE.sub(sub, html)

a = json.load(open(SP + 'assets.json'))
for key, nm in [('logo', 'logo'), ('jerry', 'jerry-baker'), ('skyline', 'sf-skyline')]:
    m = DATA_RE.match(a[key])
    if m: NAMED[hashlib.sha1(base64.b64decode(m.group(2))).hexdigest()[:12]] = nm

# ---- committed pages -------------------------------------------------------------------------------------------
S = seo.SITE
def _swap(html, old_title, block):
    assert html.count(old_title) == 1, old_title
    return html.replace(old_title, block, 1)
SEO = {
    'hero-jerry.html': lambda h: _swap(h, '<title>Baker 1031 Investments — Hero</title>', seo.head(
        title='Baker 1031 Investments — 1031 Exchange & DST Investments with Jerry Baker',
        desc='Work directly with Jerry Baker to evaluate 1031 exchange investments: Delaware Statutory Trusts, 721 exchanges, Opportunity Zone funds and more, matched to your income needs and deadlines. Offices in San Francisco and Los Angeles.',
        canonical=S + '/', graph=[seo.organization(), seo.person(), seo.website(),
            seo.webpage(S + '/', 'Baker 1031 Investments', 'Independent 1031 exchange brokerage founded by Jerry Baker.')])),
    'register.html': lambda h: _swap(h, '<title>Get Started with Jerry — Baker 1031 Investments</title>', seo.head(
        title='Get Started — Register with Baker 1031 Investments',
        desc='Tell Jerry Baker about your 1031 exchange — timeline, equity and goals — and schedule your introductory call. Registration takes a few minutes; approved investors get access to current offerings.',
        canonical=S + '/register/', graph=[seo.webpage(S + '/register/', 'Get Started', 'Register with Baker 1031 Investments and schedule an introductory call.'),
            seo.breadcrumbs([('Home', S + '/'), ('Get Started', None)])])),
    'login.html': lambda h: _swap(h, '<title>Log in — Baker 1031 Investments</title>', seo.head(
        title='Investor Log In — Baker 1031 Investments', desc='Log in with the email address on your Baker 1031 account to view current 1031 exchange investments.',
        canonical=S + '/login/', noindex=True)),
    'results.html': lambda h: _swap(h, '<title>Full-Cycle Results — Baker 1031 Investments</title>', seo.head(
        title='Full-Cycle DST Results: 1,000+ Completed 1031 Exchange Investments — Baker 1031',
        desc='Sponsor-reported results for more than 1,000 completed (full-cycle) DST and 1031 exchange investments: average annual return, equity multiple and hold period by sponsor and property type, sortable and searchable.',
        canonical=S + '/results/', graph=[seo.webpage(S + '/results/', 'Full-Cycle Results', 'Sponsor-reported results for completed DST and 1031 exchange investments.',
            {'mainEntity': {'@type': 'Dataset', 'name': 'Full-cycle DST investment results tracked by Baker 1031', 'description': 'Completed DST and 1031 exchange investments with sponsor, property type, location, average annual return, equity multiple and hold period, as reported by each sponsor.', 'creator': {'@id': seo.ORG_ID}, 'license': S + '/terms/', 'isAccessibleForFree': True}}),
            seo.breadcrumbs([('Home', S + '/'), ('Results', None)])])),
}
PAGES = { 'hero-jerry.html':'index.html', 'register.html':'register/index.html',
          'login.html':'login/index.html', 'results.html':'results/index.html' }
for src, dst in PAGES.items():
    html = open(f'{SRC}/{src}', encoding='utf-8').read()
    html = extract(html)
    # single-file preview placeholders -> real routes
    html = html.replace('href="#request-access"', 'href="/register/"')
    if src == 'register.html':   # dev step-jumper is for the Cowork preview only; the page is indexable (it replaces /request-access/)
        html = html.replace('<meta name="robots" content="noindex">\n', '')
        html = re.sub(r'  /\* ===== TEMPORARY: dev step-jumper.*?/\* ===== /TEMPORARY ===== \*/\n', '', html, flags=re.S)
        html = re.sub(r'  /\* TEMPORARY dev step-jumper — delete before launch \*/\n.*?\n\n', '\n', html, count=1, flags=re.S)
        assert 'devjump' not in html, 'step-jumper not fully removed'
    html = SEO[src](html)
    p = f'{OUT}/{dst}'; os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(html)

# ---- standalone utility page from the previous site (linked from investor emails) -------------------------------
umi = open(f'{V2}/static/update-my-info/index.html', encoding='utf-8').read()
umi = umi.replace('<script src="/assets/auth-client.js"></script>', '').replace('<script src="/assets/auth-client.js" defer></script>', '')
os.makedirs(f'{OUT}/update-my-info', exist_ok=True); open(f'{OUT}/update-my-info/index.html', 'w', encoding='utf-8').write(umi)
os.makedirs(f'{OUT}/assets/css', exist_ok=True)
shutil.copy(f'{V2}/static/assets/css/design-2026.css', f'{OUT}/assets/css/design-2026.css')   # only update-my-info uses it

# ---- shared static assets the content references (photos, sponsor logos, PDFs, videos, page scripts, fonts) ---
for d in ('img', 'sponsors', 'docs', 'video', 'js', 'fonts'):
    s = f'{V2}/static/assets/{d}'
    if os.path.isdir(s): shutil.copytree(s, f'{OUT}/assets/{d}', dirs_exist_ok=True)
# icons (from the brand mark) + Open Graph card + web manifest
os.makedirs(f'{OUT}/assets/icons', exist_ok=True)
for f in os.listdir(SP + 'icons'):
    if f.startswith('favicon-') and f.endswith('.png'): shutil.copy(SP + 'icons/' + f, f'{OUT}/assets/icons/{f}')
shutil.copy(SP + 'icons/favicon.ico', f'{OUT}/favicon.ico')
shutil.copy(SP + 'icons/apple-touch-icon.png', f'{OUT}/apple-touch-icon.png')
shutil.copy(SP + 'icons/og-card.png', f'{OUT}/assets/media/og-card.png')
open(f'{OUT}/site.webmanifest', 'w').write(json.dumps({'name': 'Baker 1031 Investments', 'short_name': 'Baker 1031', 'start_url': '/', 'display': 'browser',
    'background_color': '#ffffff', 'theme_color': '#005499',
    'icons': [{'src': '/assets/icons/favicon-192.png', 'sizes': '192x192', 'type': 'image/png'}, {'src': '/assets/icons/favicon-512.png', 'sizes': '512x512', 'type': 'image/png'}]}, indent=1))
for f in ('favicon-32.png', 'favicon-48.png'):   # the old site's favicons, still referenced by update-my-info
    shutil.copy(f'{V2}/static/assets/{f}', f'{OUT}/assets/{f}')

# ---- content sources ---------------------------------------------------------------------------------------------
shutil.copytree(SP + 'content_pages', f'{OUT}/content/pages')
shutil.copytree(f'{V2}/content/articles', f'{OUT}/content/articles')

# ---- build tooling -------------------------------------------------------------------------------------------------
os.makedirs(f'{OUT}/build', exist_ok=True)
for f in ['build.py', 'fetch_airtable.py', 'build_inventory.py', 'build_offering.py', 'build_pages.py', 'build_articles.py',
          'build_meta.py', 'content_shell.py', 'seo.py', 'content.css', 'extract_pages.py', 'build_login.py', 'build_results.py',
          'export_site.py', 'offerings.json', 'fullcycle.tsv', 'hugeicons.json', 'register_template.html']:
    if os.path.exists(SP + f): shutil.copy(SP + f, f'{OUT}/build/{f}')

# ---- Netlify: functions, edge gate, config ---------------------------------------------------------------------------
subprocess.run([sys.executable, SP + 'port_netlify.py'], check=True, env=dict(os.environ, SITE_ROOT=OUT, V2_SRC=V2))
shutil.copy(SP + 'netlify.toml', f'{OUT}/netlify.toml')
shutil.copy(SP + 'README.md', f'{OUT}/README.md')
open(f'{OUT}/requirements.txt', 'w').write('pillow>=10\nmarkdown-it-py>=3\n')
open(f'{OUT}/.gitignore', 'w').write('''.DS_Store
node_modules/
__pycache__/
# Build products — regenerated by `python3 build/build.py` on every Netlify deploy (see README)
/invest/
/offerings/
/learn/
/sponsors/
/markets/
/glossary/
/property-types/
/calculators/
/audiences/
/strategies/
/contact/
/schedule-call/
/schedule-consultation/
/process/
/privacy/
/terms/
/disclosures/
/reg-bi/
/ccpa/
/accessibility/
/commitment-to-privacy/
/assets/css/site.css
/sitemap.xml
/robots.txt
/llms.txt
/build-info.json
/404.html
# full-resolution property photos are downloaded from Airtable during the build; only the derived sizes are committed
assets/media/offerings/*
!assets/media/offerings/*-card.jpg
!assets/media/offerings/*-hero.jpg
''')

# ---- property photos: originals + derived sizes, with stamps so Netlify only re-downloads changed photos ----------
sys.path.insert(0, SP)
os.environ['SITE_ROOT'] = OUT
import importlib; fa = importlib.import_module('fetch_airtable'); fa.IMG_DIR = f'{OUT}/assets/media/offerings'
for o in json.load(open(SP + 'offerings.json')):
    if not o.get('image'): continue
    src = [f for f in os.listdir(SP + 'at_orig') if f.rsplit('.', 1)[0] == o['slug']]
    if not src: continue
    shutil.copy(SP + 'at_orig/' + src[0], f"{OUT}/assets/media/offerings/{src[0]}")
    fa.derive(f"{OUT}/assets/media/offerings/{src[0]}", o['slug'])
    open(f"{OUT}/assets/media/offerings/{o['slug']}.src", 'w').write(o['image'][0]['url'].split('/')[-1])

# ---- GitHub safety-net rebuild ------------------------------------------------------------------------------------
os.makedirs(f'{OUT}/.github/workflows', exist_ok=True)
open(f'{OUT}/.github/workflows/rebuild.yml', 'w').write('''# Safety net: ask Netlify to rebuild every hour so Airtable edits show up even if the watcher misses one.
# Add the Netlify build-hook URL as a repository secret named NETLIFY_BUILD_HOOK; without it this workflow does nothing.
name: Rebuild site from Airtable
on:
  schedule:
    - cron: "17 * * * *"
  workflow_dispatch:
jobs:
  trigger:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Netlify build hook
        env:
          HOOK: ${{ secrets.NETLIFY_BUILD_HOOK }}
        run: |
          if [ -z "$HOOK" ]; then echo "NETLIFY_BUILD_HOOK secret not set - nothing to do"; exit 0; fi
          curl -fsS -X POST -d '{}' "$HOOK"
''')

# ---- generate everything exactly the way the Netlify build does (no token here -> snapshot + no doc download) -------
subprocess.run([sys.executable, f'{OUT}/build/build.py'], check=True, env=dict(os.environ, SITE_ROOT=OUT))
# keep only the legacy assets something still references (the old homepage's hero videos and photos are not)
refs = set()
for root, dirs, files in os.walk(OUT):
    dirs[:] = [d for d in dirs if d not in ('assets', 'build', 'netlify', 'content')]
    for f in files:
        if f.endswith(('.html', '.md', '.mjs', '.js', '.css')):
            refs.update(re.findall(r'/assets/(?:img|video|docs|js|sponsors)/[A-Za-z0-9_./-]+', open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()))
for d in ('img', 'video', 'docs', 'sponsors'):
    for root, _, files in os.walk(f'{OUT}/assets/{d}'):
        for f in files:
            rel = '/' + os.path.relpath(os.path.join(root, f), OUT)
            if rel not in refs: os.remove(os.path.join(root, f))
total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs)
n = sum(len(fs) for _, _, fs in os.walk(OUT))
print('files', n, 'MB', round(total / 1e6, 1), 'media', len(seen))

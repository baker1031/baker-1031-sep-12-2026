"""Export the built pages into a deployable static site folder:
- clean directory URLs (index.html, /invest/, /register/, /login/, /results/, /offerings/<slug>/)
- every base64 data URI (images, videos) extracted to /assets/media/<hash>.<ext> and referenced by path
"""
import re, os, base64, hashlib, shutil, json
SRC = '/home/claude'
OUT = '/home/claude/site'
SP = '/tmp/claude-0/-home-claude/2a6bb0cc-5fa3-5322-8fe5-76be76cf28b9/scratchpad/'
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(OUT + '/assets/media', exist_ok=True)

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

# readable names for the shared brand assets
a = json.load(open(SP + 'assets.json'))
for key, nm in [('logo', 'logo'), ('jerry', 'jerry-baker'), ('skyline', 'sf-skyline')]:
    m = DATA_RE.match(a[key])
    if m: NAMED[hashlib.sha1(base64.b64decode(m.group(2))).hexdigest()[:12]] = nm
# offering photos keep their slug
for f in os.listdir(SP + 'at_imgs'):
    raw = open(SP + 'at_imgs/' + f, 'rb').read()
    NAMED[hashlib.sha1(raw).hexdigest()[:12]] = 'offerings/' + f[:-4]
os.makedirs(OUT + '/assets/media/offerings', exist_ok=True)

PAGES = { 'hero-jerry.html':'index.html', 'register.html':'register/index.html', 'inventory.html':'invest/index.html',
          'login.html':'login/index.html', 'results.html':'results/index.html' }
for src, dst in PAGES.items():
    html = open(f'{SRC}/{src}', encoding='utf-8').read()
    html = extract(html)
    p = f'{OUT}/{dst}'; os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(html)
for f in sorted(os.listdir(f'{SRC}/offerings')):
    html = extract(open(f'{SRC}/offerings/{f}', encoding='utf-8').read())
    slug = f[:-5]; os.makedirs(f'{OUT}/offerings/{slug}', exist_ok=True)
    open(f'{OUT}/offerings/{slug}/index.html', 'w', encoding='utf-8').write(html)
# the /offerings sample page -> /offerings/ index redirects to invest
open(f'{OUT}/netlify.toml', 'w').write('''[build]
  publish = "."

# clean URLs are directories with index.html; keep a couple of friendly aliases
[[redirects]]
  from = "/offerings"
  to = "/invest/"
  status = 301
[[redirects]]
  from = "/index.html"
  to = "/"
  status = 301

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
''')
# build tooling + data alongside the site so the pages can be regenerated
os.makedirs(f'{OUT}/build', exist_ok=True)
for f in ['build_inventory.py', 'build_offering.py', 'build_login.py', 'build_results.py', 'export_site.py', 'offerings.json', 'fullcycle.tsv', 'hugeicons.json', 'deal_imgs.json']:
    if os.path.exists(SP + f): shutil.copy(SP + f, f'{OUT}/build/{f}')
shutil.copy(SP + 'register_template.html', f'{OUT}/build/register_template.html')
open(f'{OUT}/.gitignore', 'w').write('.DS_Store\nnode_modules/\n')
total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) for f in fs)
n = sum(len(fs) for _, _, fs in os.walk(OUT))
print('files', n, 'MB', round(total / 1e6, 1), 'media', len(seen))

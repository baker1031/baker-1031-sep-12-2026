"""Shared page shell for the content sections (Learn, sponsors, markets, glossary, calculators, policies…).
Nav + footer come from the homepage so every page stays in lockstep with it; the interior styling is
content.css (the previous site's interior stylesheet re-tokenized to this design).

Works in both layouts: SITE_ROOT set (repo) -> reads ROOT/index.html; otherwise the Cowork scratch layout.
"""
import re, os, json, html as _html
import seo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('SITE_ROOT')

def load_home():
    if ROOT: return open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    return open('/home/claude/hero-jerry.html', encoding='utf-8').read()

def assets():
    if ROOT: return { 'logo':'/assets/media/logo.png', 'jerry':'/assets/media/jerry-baker.jpg', 'skyline':'/assets/media/sf-skyline.png' }
    return json.load(open(os.path.join(HERE, 'assets.json')))

_cache = {}
def shell():
    if _cache: return _cache
    h = load_home()
    def between(start, end, src=h):
        i = src.index(start); j = src.index(end, i); return src[i:j]
    navcss = between('  /* ---------- Sticky nav ---------- */', '  /* section anchors land below the sticky bar */')
    nav_mobile = between('    .nav__inner{ gap:16px; height:54px; }', '    .ctabar__inner{')
    footcss = between('  /* ---------- Footer ---------- */', '  /* ---------- Sticky nav ---------- */')
    navhtml = re.search(r'<header class="nav" id="nav">.*?</header>', h, flags=re.S).group(0)
    navhtml = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', navhtml)
    foot = re.search(r'<footer class="footer">.*?</footer>', h, flags=re.S).group(0)
    foot = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', foot)
    for old, new in [('href="#top"', 'href="/"'), ('href="#type-1031"', 'href="/invest/"'), ('href="#results"', 'href="/results/"'), ('href="#request-access"', 'href="/register/"')]:
        navhtml = navhtml.replace(old, new); foot = foot.replace(old, new)
    navjs = between("  // Nav: shadow once scrolled; mobile menu toggle", "})();\n</script>")
    a = assets()
    _cache.update(navcss=navcss, nav_mobile=nav_mobile, footcss=footcss,
                  navhtml=navhtml.replace('{{LOGO}}', a['logo']), foot=foot.replace('{{LOGO}}', a['logo']),
                  navjs=navjs, skyline=a['skyline'], jerry=a['jerry'])
    return _cache

CONTENT_CSS = open(os.path.join(HERE, 'content.css'), encoding='utf-8').read() if os.path.exists(os.path.join(HERE, 'content.css')) else ''

def site_css():
    """The shared stylesheet for every content page: content.css + the homepage's nav/footer rules."""
    s = shell()
    return f'''{CONTENT_CSS}
/* ---------- Sticky nav (from the homepage) ---------- */
{s['navcss']}  .nav__links a[aria-current="page"] .nav__word{{ color:var(--black); }}
/* ---------- Footer (from the homepage) ---------- */
{s['footcss']}
@media (max-width:900px){{
{s['nav_mobile']}    .footer__inner{{ grid-template-columns:1fr 1fr; padding:40px 20px 32px; }}
    .skyline{{ padding-top:32px; }}
    .footer__brand{{ grid-column:1 / -1; }}
    .footer__offices{{ grid-column:1 / -1; display:grid; grid-template-columns:1fr 1fr; column-gap:24px; }}
    .footer__offices .footer__label{{ grid-column:1 / -1; }}
}}
'''

def write_css():
    """Write /assets/css/site.css into the site root (repo mode) or next to the scratch pages."""
    root = ROOT or '/home/claude/site'
    d = os.path.join(root, 'assets', 'css'); os.makedirs(d, exist_ok=True)
    css = site_css()
    open(os.path.join(d, 'site.css'), 'w', encoding='utf-8').write(css)
    return len(css)

def esc(s): return _html.escape(str(s if s is not None else ''), quote=True)

def page(*, title, desc, canonical, main_html, head_extra='', body_end='', body_attrs='', current=None, noindex=False, og_type='website', image=None, image_alt=None, graph=None):
    """Wrap a <main>…</main> fragment in the site chrome. `current` marks the active nav item (invest|results|learn)."""
    s = shell()
    nav = s['navhtml']
    if current:
        nav = nav.replace(f'<a href="/{current}/">', f'<a href="/{current}/" aria-current="page">', 1)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{seo.head(title=title, desc=desc, canonical=canonical, og_type=og_type, image=image or seo.OG_IMAGE, image_alt=image_alt or 'Baker 1031 Investments', noindex=noindex, graph=graph)}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400..700&display=swap" rel="stylesheet">
<script>/* session hint set by /api/auth so the header renders logged-in before first paint */
try{{ var c=document.cookie;
 if(/(?:^|;\\s*)b31_ui=/.test(c)) document.documentElement.classList.add('is-logged-in');
 if(/(?:^|;\\s*)b31_lvl=2(?:;|$)/.test(c)) document.documentElement.classList.add('is-level2'); }}catch(e){{}}</script>
<link rel="stylesheet" href="/assets/css/site.css">
{head_extra}
</head>
<body id="top"{(' ' + body_attrs) if body_attrs else ''}>

{nav}

{main_html}

<div class="rule rule--strong" aria-hidden="true"></div>
{s['foot']}

<div class="skyline" aria-hidden="true">
  <img src="{s['skyline']}" alt="" width="2000" height="459">
</div>

<script>
(function(){{
{s['navjs']}}})();
</script>
{body_end}
</body>
</html>
'''

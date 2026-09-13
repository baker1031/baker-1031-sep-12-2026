"""One-time extraction: the previous site's static section pages (baker1031-site-v2/static) -> content/pages/<rel>.html
fragments. Each fragment is the page's <main> plus a small metadata comment; build/build_pages.py wraps it in the
2026 shell on every build. Editing a fragment edits the page.

Fragment format:
  <!--meta
  title: …
  description: …
  nav: learn            (optional: which nav item is current — invest | results | learn)
  body: data-gated      (optional: attributes for <body>)
  noindex: true         (optional)
  -->
  <!--head-->…</head extras: JSON-LD, page styles…<!--/head-->        (optional)
  <main>…</main>
  <!--scripts-->…inline/page scripts…<!--/scripts-->                  (optional)
"""
import re, os, sys, shutil, html as _html

V2 = os.environ.get('V2_SRC', '/home/claude/v2')
STATIC = os.path.join(V2, 'static')
OUT = os.environ.get('PAGES_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content_pages'))

SKIP_DIRS = {'assets', 'css', 'request-access', 'update-my-info'}
SKIP_FILES = {'index.html', '404.html'}

def fix_links(main):
    main = main.replace('>Insights<', '>Learn<').replace('href="/offerings/"', 'href="/invest/"')
    main = re.sub(r'<a href="/request-access/([^"]*)">', r'<a href="/register/\1">', main)
    main = main.replace('href="/request-access/"', 'href="/register/"').replace('href="/request-access"', 'href="/register/"')
    main = main.replace('>Current Offerings<', '>Available Investments<').replace('>Request Access<', '>Get Started<').replace('>Request access<', '>Get started<')
    # source bug on the preferred-sponsor pages: the eyebrow <span> is never closed, so the H1 inherited its uppercase
    main = re.sub(r'(<span class="eyebrow">Sponsor Profile <span class="sp-chip">[^<]*</span>)\s*\n(\s*<h1)', r'\1</span>\n\2', main)
    return main

def extract(src_path, rel):
    s = open(src_path, encoding='utf-8').read()
    title = _html.unescape((re.search(r'<title>(.*?)</title>', s, re.S) or [None, ''])[1]).strip()
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', s); desc = _html.unescape(m.group(1)) if m else ''
    noindex = bool(re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', s))
    m = re.search(r'<main[^>]*>(.*?)</main>', s, re.S)
    if not m: print('  no <main>:', rel); return None
    main = fix_links(m.group(1)).strip('\n')
    ld = '\n'.join(re.findall(r'<script type="application/ld\+json">.*?</script>', s, re.S))
    ld = ld.replace('https://baker1031.com/offerings/', 'https://baker1031.com/invest/').replace('https://baker1031.com/request-access/', 'https://baker1031.com/register/')
    styles = '\n'.join(re.findall(r'<style[^>]*>.*?</style>', s, re.S))
    tail = s[m.end():]
    scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>.*?</script>', tail, re.S)
    srcs = [x for x in re.findall(r'<script[^>]*\bsrc="([^"]+)"', s) if x.startswith('/assets/js/')]
    scripts += [f'<script src="{x}" defer></script>' for x in srcs]
    bt = re.search(r'<body([^>]*)>', s); battrs = (bt.group(1).strip() if bt else '')
    battrs = ' '.join(a for a in re.findall(r'[a-z-]+(?:="[^"]*")?', battrs) if a.startswith('data-'))
    top = rel.split('/')[0]
    nav = 'learn' if top in ('glossary', 'markets', 'property-types', 'audiences', 'strategies', 'sponsors', 'calculators') else ('results' if top == 'performance' else '')
    meta = [f'title: {title}', f'description: {desc}']
    if nav: meta.append(f'nav: {nav}')
    if battrs: meta.append(f'body: {battrs}')
    if noindex: meta.append('noindex: true')
    out = '<!--meta\n' + '\n'.join(meta) + '\n-->\n'
    head = (ld + '\n' + styles).strip()
    if head: out += '<!--head-->\n' + head + '\n<!--/head-->\n'
    out += '<main>\n' + main + '\n</main>\n'
    if scripts: out += '<!--scripts-->\n' + '\n'.join(scripts) + '\n<!--/scripts-->\n'
    return out

def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    n = 0
    for root, dirs, files in os.walk(STATIC):
        rel_root = os.path.relpath(root, STATIC)
        if rel_root == '.': dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if not f.endswith('.html'): continue
            rel = os.path.normpath(os.path.join(rel_root, f)).replace('\\', '/')
            if rel_root == '.' and f in SKIP_FILES: continue
            frag = extract(os.path.join(root, f), rel)
            if frag is None: continue
            dst = os.path.join(OUT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'w', encoding='utf-8').write(frag); n += 1
    print('extracted page fragments:', n, '->', OUT)

if __name__ == '__main__':
    main()

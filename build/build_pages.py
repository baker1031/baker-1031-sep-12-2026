"""Content pages: content/pages/<rel>.html fragments -> <rel>.html wrapped in the site shell (nav, footer, site.css).
Covers sponsors, markets, glossary, property types, calculators, audiences, strategies, contact, scheduling,
performance, process and the policy pages. See build/extract_pages.py for the fragment format.

Env: SITE_ROOT (output root; default /home/claude/site), CONTENT_SRC (default <SITE_ROOT>/content).
"""
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content_shell as cs
import seo

OUT = os.environ.get('SITE_ROOT', '/home/claude/site')
CONTENT = os.environ.get('CONTENT_SRC', os.path.join(OUT, 'content'))
PAGES = os.path.join(CONTENT, 'pages')
SITE = 'https://baker1031.com'

def parse(frag):
    meta = {}
    m = re.match(r'<!--meta\n(.*?)\n-->\n', frag, re.S)
    if m:
        for line in m.group(1).split('\n'):
            k, _, v = line.partition(':'); meta[k.strip()] = v.strip()
        frag = frag[m.end():]
    def block(name):
        mm = re.search(rf'<!--{name}-->\n?(.*?)\n?<!--/{name}-->\n?', frag, re.S)
        return mm.group(1) if mm else ''
    head, scripts = block('head'), block('scripts')
    mm = re.search(r'<main[^>]*>.*?</main>', frag, re.S)
    main = mm.group(0) if mm else '<main></main>'
    # every data table scrolls inside its own box on narrow screens (the page itself never scrolls sideways)
    if 'class="tblwrap"' not in main:
        main = re.sub(r'<table\b', '<div class="tblwrap"><table', main).replace('</table>', '</table></div>')
    return meta, head, main, scripts

def build():
    if not os.path.isdir(PAGES):
        print('[pages] skipped: no', PAGES); return []
    urls = []
    for root, _, files in os.walk(PAGES):
        for f in files:
            if not f.endswith('.html'): continue
            rel = os.path.relpath(os.path.join(root, f), PAGES).replace('\\', '/')
            meta, head, main, scripts = parse(open(os.path.join(root, f), encoding='utf-8').read())
            url_path = '/' + rel[:-len('index.html')] if rel.endswith('index.html') else '/' + rel
            graph = None
            if 'application/ld+json' not in head and url_path != '/404.html':
                crumbs = [('Home', SITE + '/')]
                parts = [x for x in url_path.strip('/').split('/') if x]
                acc = ''
                for i, part in enumerate(parts):
                    acc += '/' + part
                    label = part.replace('-', ' ').title() if i < len(parts) - 1 else (meta.get('title') or part).split(' | ')[0].split(' — ')[0]
                    crumbs.append((label, SITE + acc + '/' if i < len(parts) - 1 else None))
                graph = [seo.webpage(SITE + url_path, meta.get('title', ''), meta.get('description', '')), seo.breadcrumbs(crumbs)]
            html = cs.page(title=meta.get('title') or 'Baker 1031 Investments', desc=meta.get('description', ''),
                           canonical=SITE + url_path, main_html=main, head_extra=head, body_end=scripts,
                           body_attrs=meta.get('body', ''), current=meta.get('nav') or None,
                           noindex=meta.get('noindex', '').lower() == 'true', graph=graph)
            dst = os.path.join(OUT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'w', encoding='utf-8').write(html)
            if meta.get('noindex', '').lower() != 'true': urls.append(url_path)
    print(f'[pages] wrote {len(urls)} content pages')
    return sorted(urls)

if __name__ == '__main__':
    cs.write_css()
    build()

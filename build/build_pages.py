"""Content pages: content/pages/<rel>.html fragments -> <rel>.html wrapped in the site shell (nav, footer, site.css).
Covers sponsors, markets, glossary, property types, calculators, audiences, strategies, contact, scheduling,
performance, process and the policy pages. See build/extract_pages.py for the fragment format.

Env: SITE_ROOT (output root; default /home/claude/site), CONTENT_SRC (default <SITE_ROOT>/content).
"""
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content_shell as cs
import seo
import fullcycle as fc
import sponsor_materials as sm

OUT = os.environ.get('SITE_ROOT', '/home/claude/site')
CONTENT = os.environ.get('CONTENT_SRC', os.path.join(OUT, 'content'))
PAGES = os.path.join(CONTENT, 'pages')
SITE = 'https://baker1031.com'

# Sections that need level-2 approval. SOFT gate only: the page is built and served in full, so search
# engines and AI crawlers read every word; an investor without level 2 sees the approval card over blurred
# content. Hard gating lives in netlify/edge-functions/gate.js (LEVEL2_PREFIXES) and is separate.
LEVEL2_SECTIONS = ['glossary', 'calculators', 'property-types', 'markets', 'sponsors']

LEVEL2_GATE = '''<div class="gate gate--l2" role="region" aria-label="Approval required">
  <div class="gate__card">
    <h2>Not yet approved for this section</h2>
    <p>Email or call and I will open it up for you.</p>
    <div class="gate__actions">
      <a class="btn" href="mailto:invest@baker1031.com?subject=Access%20request">Email Baker 1031</a>
      <a class="btn btn--secondary" href="tel:+13108964227">(310) 896-4227</a>
    </div>
    <p class="gate__note">Educational content for approved Baker 1031 investors. Nothing here is an offer to sell or a solicitation to buy any security.</p>
  </div>
</div>'''

LEVEL1_GATE = '''<div class="gate gate--l1" id="gate-l1" role="region" aria-label="Log in to continue">
  <div class="gate__card">
    <h2>Log in to continue</h2>
    <p>This section is available to registered Baker 1031 investors. Log in with the email address on your account, or create one &mdash; it takes a few minutes.</p>
    <div class="gate__actions">
      <a class="btn" href="/login/?next={path}">Log In</a>
      <a class="btn btn--secondary" href="/register/">Create an Account</a>
    </div>
    <p class="gate__note">Educational content for registered investors. Nothing here is an offer to sell or a solicitation to buy any security.</p>
  </div>
</div>'''


def expand_sponsor_materials(frag):
    """<!--sponsor-materials--> becomes the document directory, built from build/sponsor-materials.json."""
    if '<!--sponsor-materials-->' not in frag:
        return frag
    frag = re.sub(r'([ \t]*)<!--sponsor-materials-->', lambda m: sm.render(indent=m.group(1)), frag)
    return frag.replace('<!--SPONSOR-MATERIALS-SCRIPT-->', sm.SCRIPT)


def needs_level2(rel):
    top = rel.split('/')[0]
    return top in LEVEL2_SECTIONS


# Exactly one gate message is true at a time, so exactly one is ever in the document. The log-in card
# is the served default (correct for an unauthenticated visitor and for a crawler); the approval card
# travels inside a <template>, which is inert — not rendered, not read by assistive technology and not
# in the text layer — and GATE_RESOLVE swaps it in for the one state where it applies.
GATE_RESOLVE = '''<script>(function(){try{
 var d=document,h=d.documentElement,l1=d.getElementById('gate-l1'),t=d.getElementById('gate-l2-tpl');
 if(!l1||!t) return;
 var inn=h.classList.contains('is-logged-in'), lvl2=h.classList.contains('is-level2');
 if(inn && !lvl2) l1.parentNode.replaceChild(t.content.cloneNode(true), l1);
 else if(inn && lvl2) l1.parentNode.removeChild(l1);
 t.parentNode.removeChild(t);
}catch(e){}})();</script>'''


def wrap_level2(main, url_path):
    """Wrap <main>'s children in the lock wrapper and add the gate. One card is served; the other is
    held in an inert <template> and swapped in by GATE_RESOLVE when that state is the true one."""
    m = re.search(r'(<main[^>]*>)(.*)(</main>)', main, re.S)
    if not m:
        return main
    inner = (LEVEL1_GATE.replace('{path}', url_path) + '\n'
             + '<template id="gate-l2-tpl">' + LEVEL2_GATE + '</template>\n'
             + GATE_RESOLVE + '\n' + m.group(2))
    return m.group(1) + '\n<div class="lockwrap lockwrap--l2">\n' + inner + '\n</div>\n' + m.group(3)


_FC = None
_SLUGMAP = None
def expand_fullcycle(main, rel):
    """<!--fc:facts--> and <!--fc:track:Name--> on a sponsor page are filled from build/fullcycle.tsv,
    so the Results page and every sponsor track record move together when the dataset is updated."""
    global _FC, _SLUGMAP
    if '<!--fc:' not in main: return main
    if _FC is None: _FC = fc.by_sponsor()
    if _SLUGMAP is None: _SLUGMAP = fc.slug2sponsor()
    slug = rel.split('/')[1] if rel.startswith('sponsors/') else ''
    sponsor = _SLUGMAP.get(slug)
    # A sponsor the dataset does not cover keeps its markers: the facts block drops the five dataset
    # figures and the track section says plainly that there are no verified results for them yet.
    rows = _FC.get(sponsor, []) if sponsor else []
    main = re.sub(r'([ \t]*)<!--fc:facts-->', lambda m: fc.facts_html(rows, m.group(1)), main)
    main = re.sub(r'([ \t]*)<!--fc:track:([^>]*?)-->',
                  lambda m: fc.track_html(m.group(2), rows, m.group(1)), main)
    return main

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
    drafts = []
    for root, _, files in os.walk(PAGES):
        for f in files:
            if not f.endswith('.html'): continue
            rel = os.path.relpath(os.path.join(root, f), PAGES).replace('\\', '/')
            frag = expand_fullcycle(open(os.path.join(root, f), encoding='utf-8').read(), rel)
            frag = expand_sponsor_materials(frag)
            meta, head, main, scripts = parse(frag)
            # `draft: true` keeps a fragment in the repo but off the site. Retail communications that
            # have not had principal approval under FINRA Rule 2210 must not be served at all — not
            # noindexed, not gated, not served. Remove the flag once the page is approved.
            if meta.get('draft', '').lower() == 'true':
                drafts.append(rel); continue
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
            if needs_level2(rel):
                main = wrap_level2(main, url_path)
            html = cs.page(title=meta.get('title') or 'Baker 1031 Investments', desc=meta.get('description', ''),
                           canonical=SITE + url_path, main_html=main, head_extra=head, body_end=scripts,
                           body_attrs=meta.get('body', ''), current=meta.get('nav') or None,
                           noindex=meta.get('noindex', '').lower() == 'true', graph=graph)
            dst = os.path.join(OUT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'w', encoding='utf-8').write(html)
            if meta.get('noindex', '').lower() != 'true': urls.append(url_path)
    print(f'[pages] wrote {len(urls)} content pages')
    if drafts:
        print(f'[pages] held back {len(drafts)} draft page(s), not published: ' + ', '.join(sorted(drafts)))
    return sorted(urls)

if __name__ == '__main__':
    cs.write_css()
    build()

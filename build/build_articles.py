"""Learn library: content/articles/*.md -> /learn/<slug>/ + /learn/ index.
Python port of the article pipeline in the previous site's build.js (front matter, legacy-link rewriting,
category map, FAQ schema, excerpt, disclaimers, hub pages, related rows, JSON-LD), rendered into the 2026 shell.

Env: SITE_ROOT (output root; default /home/claude/site), CONTENT_SRC (dir holding articles/; default <SITE_ROOT>/content).
"""
import re, os, sys, json, html as _html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content_shell as cs
import seo
import fullcycle as fc
from markdown_it import MarkdownIt

OUT = os.environ.get('SITE_ROOT', '/home/claude/site')
CONTENT = os.environ.get('CONTENT_SRC', os.path.join(OUT, 'content'))
ARTICLES = os.path.join(CONTENT, 'articles')
SITE = 'https://baker1031.com'
esc = cs.esc

EDU_DISCLAIMER = 'This article is published for educational purposes only. It may contain errors or information that has become outdated, and it is not tax, investment, legal, or accounting advice. Do not rely on it when making investment or tax decisions: review the offering documents (including the PPM) for any investment you are considering, and speak with your attorney or CPA about your specific situation before acting.'
VERIFIED_DISCLOSURE = 'Securities offered through Aurora Securities, Inc. (ASI), CRD #46147, SEC #8-51322, member FINRA/SIPC. Gerald F. “Jerry” Baker, III is a registered representative of ASI (FINRA CRD #7537416). Baker 1031 Investments, LLC is independent of ASI and is not a registered broker-dealer or investment adviser.'
PLACEHOLDER = '[Placeholder regulatory disclosure — replace with verified entity names, CRD numbers, and registrations.]'

# ---------------------------------------------------------------------------
# Disclosures. One source of truth for the risk paragraph, matched to what the
# page is actually about. The old arrangement pasted an oil & gas + DST
# paragraph into every article, so REIT, Opportunity Zone and estate pages
# disclosed commodity-price risk they do not carry and said nothing about the
# risks they do. Each article carries `risk:` in its front matter (written by
# build/tools/tag_risk.py, overridable by hand); this maps it to the paragraph.
RISK_INTRO = ('This article is published by Baker 1031 Investments, LLC for general educational purposes for '
              'accredited investors and is not an offer to sell or a solicitation of an offer to buy any security, '
              'nor is it tax, legal, accounting, or investment advice or a recommendation. Any securities offering '
              'is made solely through a sponsor\u2019s private placement memorandum (PPM) following a suitability '
              'determination. ' + VERIFIED_DISCLOSURE)

_TAIL = ('Tax results depend on your individual circumstances. Consult your own CPA and attorney before acting. '
         'Past performance does not guarantee future results.')

RISK = {
 'dst': ('DST interests and other 1031 replacement-property programs are speculative, illiquid securities sold only '
         'to verified accredited investors and involve substantial risk, including possible loss of principal, no '
         'control over management or the timing of a sale, dependence on tenants and on the sponsor, financing and '
         'interest-rate risk, and the risk that an intended 1031 exchange fails to qualify for tax deferral. There is '
         'no public market for these interests and none is expected to develop. ' + _TAIL),
 'reit': ('REIT shares involve risk, including possible loss of principal, and their income and value depend on the '
          'performance of the underlying real estate. Distributions are not guaranteed, may exceed earnings, and may '
          'be reduced or suspended at the issuer\u2019s discretion. Listed REITs fluctuate in price and can be '
          'volatile; non-traded REITs are illiquid, have no public market, and their repurchase programs are limited, '
          'discretionary, may be suspended, and may repurchase below the price paid. ' + _TAIL),
 'oz': ('Qualified Opportunity Funds are speculative, illiquid securities sold only to verified accredited investors '
        'and involve substantial risk, including possible loss of principal, development and lease-up risk, a holding '
        'period measured in years, and the risk that an investment fails to qualify for, or later loses, the intended '
        'Opportunity Zone treatment. The tax benefits depend on statutory deadlines and on continuing compliance by '
        'both the fund and the investor. ' + _TAIL),
 'upreit': ('A 721 exchange (UPREIT) contribution is generally one-way: once an interest is contributed to an operating '
            'partnership the investor holds OP units and can no longer complete a 1031 exchange on that interest. OP '
            'units are illiquid securities involving substantial risk, including possible loss of principal; their '
            'value depends on the REIT\u2019s performance, distributions are not guaranteed, and redemption is at the '
            'REIT\u2019s discretion and is normally a taxable event. ' + _TAIL),
 'oilgas': ('Oil and gas mineral and royalty interests are speculative, illiquid securities sold only to verified '
            'accredited investors and involve substantial risk, including possible loss of principal, commodity-price '
            'and production-decline risk, no control over operations, and the risk that an intended 1031 exchange '
            'fails to qualify for tax deferral. Whether a particular interest is like-kind real property is a '
            'fact-specific legal determination that varies by state and by the terms of the instrument. ' + _TAIL),
 'mixed': ('The programs discussed here \u2014 which may include DSTs, REITs, Qualified Opportunity Funds, 721 '
           'exchange (UPREIT) interests and oil and gas royalty interests \u2014 are speculative securities sold only '
           'to verified accredited investors and involve substantial risk, including possible loss of principal, '
           'illiquidity, no control over management, and, where a 1031 exchange or Opportunity Zone election is '
           'intended, the risk that it fails to qualify for the tax treatment sought. The risks differ by structure; '
           'read the risk factors in each offering\u2019s own documents rather than relying on a general summary. ' + _TAIL),
 'general': ('The investments discussed here are speculative, illiquid securities sold only to verified accredited '
             'investors and involve substantial risk, including possible loss of principal and no control over '
             'management. Tax and estate results depend on your individual circumstances and on law that can change. '
             + _TAIL),
}


def ensure_disclosures(md, profile):
    """Every article ends with the same two-part block: who is speaking and on what footing, then the risks
    of the thing the page is actually about. Bespoke wording already in the section is kept."""
    risk = RISK.get(profile) or RISK['general']
    # a narrower substitute for the standard past-performance line narrows the disclaimer; put it back
    md = md.replace('Past projections do not guarantee future results', 'Past performance does not guarantee future results')
    # Two shapes in the corpus: a markdown '## Disclosures' section, and a raw-HTML block left by the
    # legacy importer. Fill whichever one the article uses; only write a new section if it has neither.
    hd = re.search(r'<div class="disclosures">(.*?)</div>', md, re.S)
    if hd:
        if 'Aurora Securities' not in hd.group(1):
            md = md[:hd.start(1)] + '<p>' + RISK_INTRO + '</p>' + md[hd.start(1):]
            hd = re.search(r'<div class="disclosures">(.*?)</div>', md, re.S)
        return md[:hd.end(1)] + '<p>' + risk + '</p>' + md[hd.end(1):]
    m = re.search(r'\n##+\s+(?:\d+\s*[\u00b7.]\s*)?Disclosures?\s*\n', md)
    if not m:
        return md.rstrip() + '\n\n## Disclosures\n\n' + RISK_INTRO + '\n\n' + risk + '\n'
    start = m.end()
    nxt = re.search(r'\n##+\s', md[start:])
    end = start + (nxt.start() if nxt else len(md) - start)
    section = md[start:end]
    # Several drafts left the article's closing paragraph below the Disclosures heading, so the page ended
    # with a conclusion filed under a legal heading. Lift any non-disclosure prose back above the heading.
    keep, lifted = [], []
    for para in re.split(r'\n\s*\n', section):
        t = para.strip()
        if not t:
            continue
        legal = re.search(r'Aurora|accredited|Past performance|speculative|illiquid|PPM|private placement|'
                          r'not (?:tax|investment|legal)|does not guarantee|consult your own', t, re.I)
        (keep if legal else lifted).append(t)
    section = '\n' + '\n\n'.join(keep) + '\n'
    if 'Aurora Securities' not in section:
        section = '\n' + RISK_INTRO + '\n' + section
    section = section.rstrip() + '\n\n' + risk + '\n'
    head = md[:m.start()].rstrip()
    if lifted:
        head = head + '\n\n' + '\n\n'.join(lifted)
    return head + md[m.start():start] + section + md[end:]


HUB_SLUGS = {'about', 'fees', 'jerry-baker-bio', 'methodology', 'for-advisors-cpas', 'for-agents-brokers',
             'top-1031-dst-sponsor-firms', 'delaware-statutory-trusts', '1031-exchanges', 'reits',
             '721-exchange-upreit', 'mineral-royalty-interests', 'opportunity-zone-funds'}
HUB_TYPE = {'about': 'AboutPage', 'jerry-baker-bio': 'ProfilePage'}

md_engine = MarkdownIt('commonmark', {'html': True, 'linkify': False, 'typographer': False}).enable(['table', 'strikethrough'])

def parse_front_matter(text):
    m = re.match(r'^---\n(.*?)\n---\n?', text, re.S)
    if not m: return {}, text
    fm = {}
    for line in m.group(1).split('\n'):
        i = line.find(':')
        if i > 0: fm[line[:i].strip()] = re.sub(r'^["\']|["\']$', '', line[i + 1:].strip())
    return fm, text[m.end():]

CAT_MAP = {
    'REIT': 'REITs', 'Delaware Statutory Trust': 'Delaware Statutory Trusts', 'DST Basics': 'Delaware Statutory Trusts',
    'Opportunity Zones': 'Opportunity Zone Funds', 'Mineral & Royalty': 'Oil & Gas Royalties', 'Oil & Gas': 'Oil & Gas Royalties',
    'UPREIT': '721 Exchange', '1031 Exchange, DSTs': '1031 Exchange', 'Definitive Guide': '1031 Exchange',
    'Definitive Guide · 2026': '1031 Exchange', 'Capital Gains': 'Capital Gains & Tax', 'Tax Forms': 'Capital Gains & Tax',
    'Net Investment Income Tax': 'Capital Gains & Tax', 'Real Estate Tax Center': 'Capital Gains & Tax',
    'Comparison': 'Strategy & Comparisons', 'Strategy': 'Strategy & Comparisons',
    'For Tax Advisors': 'For Advisors', 'For Agents & Brokers': 'For Advisors',
}
def article_category(fm, slug):
    c = re.sub(r'^["\']|["\']$', '', (fm.get('category') or fm.get('source_category') or '')).strip()
    c = CAT_MAP.get(c, c)
    if c: return c
    s = slug.lower()
    if re.search(r'(^|-)dst(-|$)|statutory', s): return 'Delaware Statutory Trusts'
    if re.search(r'721|upreit', s): return '721 Exchange'
    if 'reit' in s: return 'REITs'
    if re.search(r'opportunity|qoz|qof', s): return 'Opportunity Zone Funds'
    if re.search(r'oil|gas|mineral|royalt', s): return 'Oil & Gas Royalties'
    return '1031 Exchange'

MONTHS = {m: f'{i:02d}' for i, m in enumerate(['january','february','march','april','may','june','july','august','september','october','november','december'], 1)}
def iso_date(text):
    """A full ISO 8601 date for schema.org dateModified.

    This used to emit a year-month ("2026-06") or a bare year ("2026"). Google's Article
    documentation asks for a full ISO 8601 date, so both forms were ignored on all 312
    articles that carried one. The sources only ever state a month ("Updated June 2026"),
    and the first of that month is the honest normalisation of it; a bare year is dropped
    rather than given an invented month."""
    text = str(text or '')
    m = re.search(r'([A-Za-z]+)\s+(20\d\d)', text)
    if m and m.group(1).lower() in MONTHS:
        return f'{m.group(2)}-{MONTHS[m.group(1).lower()]}-01'
    return None

def strip_md(t):
    t = re.sub(r'\*\*|__|`', '', t); t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t); return re.sub(r'\s+', ' ', t).strip()

def extract_faq(md):
    m = re.search(r'^##\s+(?:Frequently Asked Questions|FAQs?)[^\n]*\n(.*?)(?=^##\s|\Z)', md, re.M | re.S)
    if not m: return []
    out = []
    for p in re.split(r'^###\s+', m.group(1), flags=re.M)[1:]:
        nl = p.find('\n')
        if nl < 0: continue
        q, a = strip_md(p[:nl]), strip_md(p[nl + 1:])
        if q and a: out.append({'q': q, 'a': a})
    return out

def first_paragraph(md):
    """First real paragraph of prose: skips headings, lists, quotes, tables, raw HTML blocks and the short
    'Category · Category' metadata lines some drafts open with."""
    for block in re.split(r'\n\s*\n', md):
        t = block.strip()
        if not t or re.match(r'^#|^-|^\*|^>|^\||^\d+\.', t): continue
        if t.startswith('<'):                              # a raw-HTML draft: take its first paragraph
            m = re.search(r'<p\b[^>]*>(.*?)</p>', t, re.S)
            if not m: continue
            t = m.group(1)
        t = re.sub(r'<[^>]+>', '', t)                      # inline HTML
        t = re.sub(r'\*\*|__|\*|_|`', '', t); t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
        t = re.sub(r'\s+', ' ', t).strip()
        if len(t) < 60 or (' · ' in t and len(t) < 120): continue
        return t
    return ''

ALIAS = {'1031-exchange-into-dst': '1031-exchange-into-a-dst-passive-option', '1031-exchange': '1031-exchange-guide',
         'glossary': '1031-exchange-glossary-of-terms', 'how-to-invest-in-a-dst': 'how-to-buy-a-dst-step-by-step-process',
         'agent-guide-dst': 'for-agents-brokers', 'cpa-guide-dst': 'for-advisors-cpas', 'sponsors': 'top-1031-dst-sponsor-firms',
         'glossary-step-up-in-basis': '1031-exchange-glossary-of-terms', 'data-center': 'data-center-dsts-explained'}
URL_ALIAS = {'contact': '/contact/', 'investments': '/invest/', 'calculators': '/calculators/',
             '1031-exchange-deadline-calculator-45-180': '/calculators/deadline/',
             '1031-exchange-calculator-estimate-deferred-tax': '/calculators/deferred-tax/',
             'capital-gains-tax-calculator': '/calculators/deferred-tax/',
             'capital-gains-tax-calculator-property-sales': '/calculators/deferred-tax/',
             'depreciation-recapture-calculator': '/calculators/deferred-tax/',
             'sell-vs-1031-exchange-calculator': '/calculators/sell-vs-exchange/',
             'ltv-calculator-1031-debt-matching': '/calculators/replacement-property/',
             'debt-replacement-ltv-calculator': '/calculators/replacement-property/',
             '1031-replacement-property-value-calculator': '/calculators/replacement-property/'}

def clean_article_body(md, slug_set, unresolved):
    schema_desc = None
    # the embedded legacy schema carries several descriptions (Article, Person, Organization); take the first that
    # describes the article rather than its author or publisher
    for sd in re.finditer(r'"description"\s*:\s*"([^"]{40,300})"', md):
        t = sd.group(1)
        if re.search(r'Founder and managing principal|Baker 1031 Investments is|registered representative', t): continue
        schema_desc = t; break
    embedded_title = embedded_desc = None
    if re.search(r'<!DOCTYPE html>', md, re.I):
        et = re.search(r'<title>([^<]+)</title>', md, re.I)
        if et: embedded_title = re.sub(r'\s*\|\s*Baker 1031[^|]*$', '', et.group(1), flags=re.I).strip()
        ed = re.search(r'<meta\s+name="description"\s+content="([^"]{40,300})"', md, re.I)
        if ed: embedded_desc = ed.group(1)
        md = re.sub(r'<!DOCTYPE html>', '', md, flags=re.I)
        md = re.sub(r'<head[^>]*>.*?</head>', '', md, flags=re.I | re.S)
        md = re.sub(r'</?html[^>]*>', '', md, flags=re.I)
        md = re.sub(r'</?body[^>]*>', '', md, flags=re.I)
    md = re.sub(r'^##\s+Structured Metadata.*?(?=^##\s|\Z)', '', md, flags=re.M | re.S)
    md = re.sub(r'<script.*?</script>', '', md, flags=re.S)
    md = re.sub(r'<footer.*?</footer>', '', md, flags=re.S)
    md = re.sub(r'^\[Home\]\([^)]*\).*$', '', md, flags=re.M)
    md = re.sub(r'^Navigation:.*$', '', md, flags=re.M)
    md = re.sub(r'^[-*]?\s*\[?Back to All [A-Za-z ]+\]?\([^)]*\)(\s*(?:·|&middot;)\s*\[[^\]]*\]\([^)]*\))*\s*$', '', md, flags=re.M)
    md = re.sub(r'^[^#\n]{0,90}Updated\s+[A-Z][a-z]+\s+20\d\d[^\n]*min read\s*$', '', md, flags=re.M)
    md = re.sub(r'^[A-Za-z ·]{0,24}Baker 1031 Research\s*(?:·|&middot;)?\s*Updated\s+[A-Z][a-z]+\s+20\d\d\s*$', '', md, flags=re.M)
    md = re.sub(r'^\*\*Author profile note\.\*\*.*$', '', md, flags=re.M)
    md = re.sub(r'^###\s+Author profile note\s*$.*?(?=^#{2,3}\s|\Z)', '', md, flags=re.M | re.S)
    md = md.replace('https://baker1031.com/about/jerry-baker/', 'https://baker1031.com/learn/jerry-baker-bio/')
    md = md.replace('https://baker1031.com/assets/img/jerry-baker.jpg', 'https://baker1031.com/assets/img/jerry-baker.webp')
    # retired paths on the new site
    md = md.replace('](/offerings/)', '](/invest/)').replace('href="/offerings/"', 'href="/invest/"')
    md = md.replace('](/request-access/)', '](/register/)').replace('href="/request-access/"', 'href="/register/"')

    def md_link(m):
        t = m.group(1)
        if t == 'baker1031': return '](/)'
        if t == 'insights': return '](/learn/)'
        if t == 'jerry-baker-bio': return '](/learn/jerry-baker-bio/)'
        if t == 'faq': return '](/#faq)'
        if t in URL_ALIAS: return f']({URL_ALIAS[t]})'
        if t in ALIAS and ALIAS[t] in slug_set: return f'](/learn/{ALIAS[t]}/)'
        if t in slug_set: return f'](/learn/{t}/)'
        unresolved[t] = unresolved.get(t, 0) + 1
        return '](UNRESOLVED)'
    md = re.sub(r'\]\(([a-z0-9-]+)\.html(#[^)]*)?\)', md_link, md)
    md = re.sub(r'\[([^\]]+)\]\(UNRESOLVED\)', r'\1', md)

    def html_link(m):
        t = m.group(1)
        if t == 'baker1031': return 'href="/"'
        if t == 'insights': return 'href="/learn/"'
        if t == 'jerry-baker-bio': return 'href="/learn/jerry-baker-bio/"'
        if t in slug_set: return f'href="/learn/{t}/"'
        return 'href="/learn/"'
    md = re.sub(r'href="([a-z0-9-]+)\.html(#[^"]*)?"', html_link, md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md, schema_desc, embedded_title, embedded_desc

def _slug(t):
    t = re.sub(r'<[^>]+>', '', t); t = re.sub(r'&[a-z]+;|&#\d+;', '', t)
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', t.lower())).strip('-')[:80] or 'section'

def expand_benchmark(html):
    """<!--sg:benchmark--> in an article is replaced with the platform benchmark computed from
    build/fullcycle.tsv. The DST guide carried this block as hand-typed numbers and every one of
    them had drifted away from the dataset and from the homepage."""
    if '<!--sg:benchmark-->' not in html:
        return html
    return re.sub(r'(?:<p>\s*)?<!--sg:benchmark-->(?:\s*</p>)?',
                  lambda m: fc.benchmark_html(), html)


def render_md(body):
    html = md_engine.render(body)
    html = expand_benchmark(html)
    html = re.sub(r'<table\b[^>]*>', lambda m: '<div class="tblwrap">' + m.group(0), html).replace('</table>', '</table></div>')
    # section anchors (deep links) + a contents list on long guides so a section can be cited directly
    seen, heads = {}, []
    def anchor(m):
        attrs, text = m.group(1), m.group(2)
        # a raw-HTML heading may already carry its own id; keep it rather than emitting a second one
        have = re.search(r'\bid="([^"]+)"', attrs)
        if have:
            hid = have.group(1); seen[hid] = seen.get(hid, 0) + 1
        else:
            base = _slug(text); n = seen.get(base, 0); seen[base] = n + 1
            hid = base if n == 0 else f'{base}-{n + 1}'
            attrs = f' id="{hid}"' + attrs
        heads.append((hid, re.sub(r'<[^>]+>', '', text)))
        return f'<h2{attrs}>{text}</h2>'
    html = re.sub(r'<h2([^>]*)>(.*?)</h2>', anchor, html, flags=re.S)
    if len(heads) >= 5:
        toc = '<nav class="toc" aria-label="Contents"><p class="toc__label">Contents</p><ol>' + ''.join(f'<li><a href="#{h}">{t}</a></li>' for h, t in heads) + '</ol></nav>\n'
        # after the opening paragraph(s): before the first h2
        i = html.find('<h2 ')
        html = (html[:i] + toc + html[i:]) if i > 0 else toc + html
    return html

def load_articles(build_date):
    files = sorted(f for f in os.listdir(ARTICLES) if f.endswith('.md'))
    slug_set = {f[:-3] for f in files}
    unresolved = {}
    arts = []
    for f in files:
        slug = f[:-3]
        fm, raw = parse_front_matter(open(os.path.join(ARTICLES, f), encoding='utf-8').read())
        md, schema_desc, emb_title, emb_desc = clean_article_body(raw, slug_set, unresolved)
        body = md.replace(PLACEHOLDER, VERIFIED_DISCLOSURE)
        body = ensure_disclosures(body, re.sub(r'^["\']|["\']$', '', fm.get('risk', '')).strip())
        body = re.sub(r'^\*\*Category:\*\*[^\n]*\n(\*\*(Research|Updated|Reading time|Author|Filed under):\*\*[^\n]*\n?)+', '', body, count=1, flags=re.M)
        h1 = re.search(r'^#\s+(.+)$', body, re.M)
        title = fm.get('title') or fm.get('page_title') or fm.get('seo_title') or emb_title or (h1.group(1).strip() if h1 else slug)
        if h1: body = body.replace(h1.group(0), '', 1).lstrip()
        excerpt_src = first_paragraph(body)
        desc = fm.get('meta_description') or schema_desc or emb_desc or excerpt_src
        if len(desc) > 158: desc = desc[:desc.rfind(' ', 0, 156)] + '…'
        if len(desc) < 100: desc = (re.sub(r'[.\s]+$', '', desc) + '. ' if desc else '') + 'Expert 1031 exchange and DST guidance from Baker 1031 Investments.'
        page_script = re.sub(r'^["\']|["\']$', '', fm.get('page_script', '')).strip()
        updated = fm.get('updated') or fm.get('source_updated') or ''
        read = fm.get('source_read_time', '')
        when = ' · '.join(x for x in [updated, read] if x) or build_date
        excerpt = excerpt_src[:excerpt_src.rfind(' ', 0, 201)] + '…' if len(excerpt_src) > 200 else excerpt_src
        arts.append(dict(slug=slug, title=title, body=body, category=article_category(fm, slug), desc=desc, page_script=page_script,
                         excerpt=excerpt, when=when, updated=updated, read=read, iso=iso_date(updated), faq=extract_faq(body)))
    arts.sort(key=lambda a: a['title'].casefold())
    if unresolved:
        items = sorted(unresolved.items(), key=lambda kv: -kv[1])
        print(f'[articles] NOTE: {len(unresolved)} legacy link targets have no page (links dropped, text kept): ' + ', '.join(f'{t} ({n})' for t, n in items[:12]))
    return arts

# Articles that stay open to everyone: the founder bio and the fee page are trust pages, and gating them
# would cost more than it protects.
# Jerry's bio is the one article that stays open: it is the page people are sent to in order to
# find out who they would be working with, so a gate there defeats its purpose.
PUBLIC_SLUGS = {'jerry-baker-bio'}

def gate_card_l2():
    return '''<div class="gate gate--l2" role="region" aria-label="Approval required">
  <div class="gate__card">
    <p class="gate__title">Not yet approved for this section</p>
    <p>Email or call and I will open it up for you.</p>
    <div class="gate__actions">
      <a class="btn" href="mailto:invest@baker1031.com?subject=Access%20request">Email Baker 1031</a>
      <a class="btn btn--secondary" href="tel:+13108964227">(310) 896-4227</a>
    </div>
    <p class="gate__note">Educational content for approved Baker 1031 investors. Nothing here is an offer to sell or a solicitation to buy any security.</p>
  </div>
</div>'''

# Only one gate message is ever true, so only one is ever in the document: the log-in card is served,
# and the approval card travels in an inert <template> that GATE_RESOLVE swaps in for the one state
# where it applies. See the same arrangement in build_pages.py.
GATE_RESOLVE = '''<script>(function(){try{
 var d=document,h=d.documentElement,l1=d.getElementById('gate-l1'),t=d.getElementById('gate-l2-tpl');
 if(!l1||!t) return;
 var inn=h.classList.contains('is-logged-in'), lvl2=h.classList.contains('is-level2');
 if(inn && !lvl2) l1.parentNode.replaceChild(t.content.cloneNode(true), l1);
 else if(inn && lvl2) l1.parentNode.removeChild(l1);
 t.parentNode.removeChild(t);
}catch(e){}})();</script>'''


def gate_pair(path, title, body):
    return (gate_card(path, title, body) + '\n<template id="gate-l2-tpl">' + gate_card_l2()
            + '</template>\n' + GATE_RESOLVE)


def gate_card(path, title, body):
    return f'''<div class="gate gate--l1" id="gate-l1" role="region" aria-label="Log in to continue">
  <div class="gate__card">
    <p class="gate__title">{title}</p>
    <p>{body}</p>
    <div class="gate__actions">
      <a class="btn" href="/login/?next={path}">Log In</a>
      <a class="btn btn--secondary" href="/register/">Create an Account</a>
    </div>
    <p class="gate__note">Educational content for registered investors. Nothing here is an offer to sell or a solicitation to buy any security.</p>
  </div>
</div>'''

def article_main(a, html, related_rows, is_hub):
    public = a['slug'] in PUBLIC_SLUGS
    byline = '' if is_hub else f'''
    <div class="byline">
      <span class="who">Jerry Baker</span>
      <span class="role">Founder &amp; Managing Principal, Baker 1031 Investments</span>
      <span class="dot">|</span>
      <span class="when">{esc(a['when'])}</span>
    </div>'''
    authorbox = '' if is_hub else '''
  <section class="sec authorbox">
    <div class="label">ABOUT THE AUTHOR</div>
    <div class="who">Jerry Baker</div>
    <p>Jerry Baker is the founder and managing principal of Baker 1031 Investments, a founder-led real estate securities brokerage helping accredited investors evaluate 1031-eligible strategies. His perspective comes from more than a decade in institutional real estate and a 60-year family legacy in the business.</p>
    <div class="links">
      <a href="/learn/jerry-baker-bio/">About Jerry</a>
      <a href="https://brokercheck.finra.org/individual/summary/7537416" target="_blank" rel="noopener">Verify on BrokerCheck</a>
      <a href="/register/">Get started</a>
    </div>
  </section>'''
    more = '' if is_hub else f'''
  <section class="sec more">
    <h2 class="h3">More from Learn</h2>
{related_rows}
  </section>'''
    return f'''<main class="{'main' if public else 'main--gated'}">

  <section class="mast mast--light artmast">
    <div class="crumbs"><a href="/">Home</a> <span>/</span> <a href="/learn/">Learn</a> <span>/</span> {esc(a['title'])}</div>
    <p class="cat">{esc(a['category'])}</p>
    <h1>{esc(a['title'])}</h1>{byline}
  </section>

  <section class="sec bg-white" style="padding-top:48px">
    <div class="{'' if public else 'lockwrap lockwrap--article lockwrap--l2'}">
{'' if public else gate_pair('/learn/' + a['slug'] + '/', 'Log in to keep reading', 'The Learn library is available to registered Baker 1031 investors. Log in with the email address on your account, or create one — it takes a few minutes.')}
    <div class="prose">
{html}
<div class="footnote">{esc(EDU_DISCLAIMER)} Spotted an error? Email <a href="mailto:jerry@baker1031.com">jerry@baker1031.com</a> and it will be corrected.</div>
    </div>
    </div>
  </section>
{authorbox}{more}
  <section class="sec cta-band">
    <span class="eyebrow">Next step</span>
    <h2 class="h2">Questions about your exchange?</h2>
    <p class="p-main">Tell me where you are in the process and I&rsquo;ll tell you, plainly, whether a 1031 into a DST is a fit.</p>
    <div class="btn-row"><a class="btn" href="/register/">Get started</a>
<a class="btn btn--secondary" href="/contact/">Contact</a></div>
  </section>

</main>'''

def article_json(a, canonical, is_hub):
    is_public = a['slug'] in PUBLIC_SLUGS
    graph = [{
        '@type': 'Article', 'headline': a['title'], 'description': a['desc'], 'mainEntityOfPage': canonical,
        **({'isAccessibleForFree': True} if is_public else
           {'isAccessibleForFree': False, 'hasPart': {'@type': 'WebPageElement', 'isAccessibleForFree': False, 'cssSelector': '.lockwrap--article'}}),
        **({'dateModified': a['iso']} if a['iso'] else {}),
        'author': {'@type': 'Person', '@id': SITE + '/#jerry', 'name': 'Jerry Baker', 'jobTitle': 'Founder & Managing Principal',
                   'worksFor': {'@id': SITE + '/#org'}, 'sameAs': ['https://brokercheck.finra.org/individual/summary/7537416']},
        'publisher': {'@type': 'Organization', '@id': SITE + '/#org', 'name': 'Baker 1031 Investments', 'url': SITE + '/',
                      'logo': {'@type': 'ImageObject', 'url': SITE + '/assets/media/logo.png'}},
    }, {
        '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Learn', 'item': SITE + '/learn/'},
            {'@type': 'ListItem', 'position': 3, 'name': a['title'], 'item': canonical}],
    }]
    if is_hub:
        graph[0] = {'@type': HUB_TYPE.get(a['slug'], 'WebPage'), 'name': a['title'], 'description': a['desc'], 'url': canonical,
                    'publisher': {'@type': 'Organization', '@id': SITE + '/#org', 'name': 'Baker 1031 Investments', 'url': SITE + '/'},
                    **({'mainEntity': {'@type': 'Person', '@id': SITE + '/#jerry', 'name': 'Jerry Baker', 'jobTitle': 'Founder & Managing Principal',
                                       'sameAs': ['https://brokercheck.finra.org/individual/summary/7537416']}} if a['slug'] == 'jerry-baker-bio' else {})}
    if a['faq']:
        graph.append({'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': f['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}} for f in a['faq']]})
    return '<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False).replace('</', '<\\/') + '</script>'

INDEX_JS = '''<script>
  // Rows are server-rendered; pills just show/hide them by data-cat.
  (function () {
    var rows = Array.prototype.slice.call(document.querySelectorAll('.art-row'));
    var cats = ['All'];
    rows.forEach(function (r) { var c = r.getAttribute('data-cat'); if (c && cats.indexOf(c) < 0) cats.push(c); });
    var pillsEl = document.getElementById('pills');
    var active = 'All';
    function apply() {
      var n = 0;
      rows.forEach(function (r) {
        var show = active === 'All' || r.getAttribute('data-cat') === active;
        r.style.display = show ? '' : 'none';
        if (show) n++;
      });
      document.getElementById('empty').style.display = n ? 'none' : 'block';
      var fc = document.getElementById('fcount');
      if (fc) fc.textContent = n + ' article' + (n === 1 ? '' : 's');
      Array.prototype.forEach.call(pillsEl.querySelectorAll('.pill'), function (p) {
        p.classList.toggle('active', p.dataset.cat === active);
      });
    }
    pillsEl.innerHTML = cats.map(function (c) {
      return '<button type="button" class="pill" data-cat="' + c + '">' + c + '</button>';
    }).join('') + '<span class="fcount" id="fcount"></span>';
    pillsEl.addEventListener('click', function (e) {
      var p = e.target.closest('.pill');
      if (p) { active = p.dataset.cat; apply(); }
    });
    apply();
  })();
</script>'''

def build(build_date=None):
    import datetime
    build_date = build_date or datetime.date.today().strftime('%B %-d, %Y')
    if not os.path.isdir(ARTICLES):
        print('[articles] skipped: no', ARTICLES); return []
    arts = load_articles(build_date)
    js_dir = os.path.join(OUT, 'assets', 'js')
    for a in arts:
        canonical = f"{SITE}/learn/{a['slug']}/"
        html = render_md(a['body'])
        related = [x for x in arts if x is not a and x['category'] == a['category']][:3] or [x for x in arts if x is not a][:3]
        rows = '\n'.join(f'<a class="more-row" href="/learn/{r["slug"]}/"><span class="t">{esc(r["title"])}</span>\n<span class="c">{esc(r["category"])}</span></a>' for r in related)
        is_hub = a['slug'] in HUB_SLUGS
        t = a['title']
        title_tag = f'{t} | Baker 1031 Investments' if len(t) <= 34 else (f'{t} | Baker 1031' if len(t) <= 47 else t)
        body_end = ''
        if a['page_script']:
            if not os.path.exists(os.path.join(js_dir, a['page_script'])):
                raise SystemExit(f"{a['slug']}: page_script {a['page_script']} does not exist in assets/js")
            body_end = f'<script src="/assets/js/{a["page_script"]}" defer></script>'
        page = cs.page(title=title_tag, desc=a['desc'], canonical=canonical, main_html=article_main(a, html, rows, is_hub),
                       head_extra=article_json(a, canonical, is_hub), body_end=body_end, current='learn', og_type='article')
        d = os.path.join(OUT, 'learn', a['slug']); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(page)
    # remove stale article dirs (renamed/deleted articles)
    keep = {a['slug'] for a in arts} | {'library'}
    learn_dir = os.path.join(OUT, 'learn')
    for name in os.listdir(learn_dir) if os.path.isdir(learn_dir) else []:
        p = os.path.join(learn_dir, name)
        if os.path.isdir(p) and name not in keep:
            import shutil; shutil.rmtree(p)

    featured = next((a for a in arts if a['slug'] == '1031-exchange-guide'), arts[0] if arts else None)
    rows_html = '\n'.join(
        f'<a class="art-row" data-cat="{esc(a["category"])}" href="/learn/{a["slug"]}/"><div class="cat">{esc(a["category"])}</div>'
        f'<div><div class="t">{esc(a["title"])}</div><div class="ex">{esc(a["excerpt"])}</div></div>'
        f'<div class="meta"><b>Jerry Baker</b>{esc(" · ".join(x for x in [a["updated"], a["read"]] if x))}</div></a>' for a in arts)
    featured_html = '' if not featured else (
        f'<a class="wrap" href="/learn/{featured["slug"]}/"><div class="flag">FEATURED · {esc(featured["category"])}</div>'
        f'<h2>{esc(featured["title"])}</h2><p>{esc(featured["excerpt"])}</p>'
        f'<div class="by"><b>Jerry Baker</b> · Founder &amp; Managing Principal · {esc(featured["when"])}</div><div class="read">Read the article</div></a>')
    main = f'''<main>

  <section class="mast mast--light">
    <div class="crumbs"><a href="/">Home</a> <span>/</span> Learn</div>
    <p class="eyebrow">Education</p>
    <h1>Learn</h1>
    <p class="p-main">Plain-English education on 1031 exchanges, DSTs, and the decisions behind them. Written by Jerry Baker; no jargon, no sales pitch.</p>
  </section>

  <div class="featured" id="featured">{featured_html}</div>

  <div class="filterbar">
    <div class="filterbar-in" id="pills"></div>
  </div>

  <div class="lockwrap lockwrap--learn lockwrap--l2">
{gate_pair('/learn/library/', 'Log in to browse the library', 'The Learn library is available to registered Baker 1031 investors. Log in with the email address on your account, or create one — it takes a few minutes.')}
  <div class="artlist">
    <div id="rows">{rows_html}</div>
    <div class="empty" id="empty" style="display:none;">No articles in this category yet.</div>
  </div>
  </div>

</main>'''
    idx_graph = [seo.webpage(SITE + '/learn/library/', 'Learn Library: 1031 Exchange & DST Education', f'{len(arts)} plain-English articles on 1031 exchanges, DSTs and related strategies by Jerry Baker.', page_type='CollectionPage'),
                 seo.breadcrumbs([('Home', SITE + '/'), ('Learn', SITE + '/learn/'), ('Learn Library', None)])]
    index = cs.page(graph=idx_graph, title='Learn Library: 1031 Exchange & DST Education | Baker 1031 Investments',
                    desc=f'{len(arts)} plain-English articles on 1031 exchanges, Delaware Statutory Trusts, 721 exchanges, and the tax decisions behind them, written by Jerry Baker.',
                    canonical=SITE + '/learn/library/', main_html=main, body_end=INDEX_JS, current='learn')
    lib_dir = os.path.join(learn_dir, 'library')
    os.makedirs(lib_dir, exist_ok=True)
    open(os.path.join(lib_dir, 'index.html'), 'w', encoding='utf-8').write(index)
    print(f'[articles] wrote learn/library/ ({len(arts)} articles + index)')
    return arts

if __name__ == '__main__':
    build()

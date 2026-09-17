"""Crawl plumbing written after the pages: sitemap.xml, robots.txt, llms.txt, build-info.json.
The sitemap is derived from the built tree — every index.html that is not marked noindex."""
import csv, os, re, json, datetime

ROOT = os.environ.get('SITE_ROOT', '/home/claude/site')
SITE = 'https://baker1031.com'
SKIP_DIRS = {'content', 'build', 'netlify', 'assets', '.git', '.github', 'node_modules'}
NOINDEX_RE = re.compile(r'<meta\s+name="robots"\s+content="[^"]*noindex', re.I)

def urls():
    out = []
    for root, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(root, ROOT)
        if rel == '.': dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        if 'docs' in dirs and rel.startswith('offerings'): dirs.remove('docs')
        if 'index.html' not in files: continue
        head = open(os.path.join(root, 'index.html'), encoding='utf-8', errors='ignore').read(6000)
        if NOINDEX_RE.search(head): continue
        out.append('/' if rel == '.' else '/' + rel.replace(os.sep, '/') + '/')
    return sorted(set(out), key=lambda u: (u != '/', u.count('/'), u))

ROBOTS = """# Baker 1031 Investments — crawl policy
# Public pages are open to search engines and AI assistants (search, user-fetch and training crawlers alike);
# offering documents and the API are excluded. Edit here (build/build_meta.py), not the generated file.
User-agent: *
Allow: /
Disallow: /offerings/*/docs/
Disallow: /login/?next=
Disallow: /api/

# AI search / assistant crawlers — explicitly allowed
User-agent: OAI-SearchBot
User-agent: ChatGPT-User
User-agent: GPTBot
User-agent: Google-Extended
User-agent: PerplexityBot
User-agent: Perplexity-User
User-agent: Claude-SearchBot
User-agent: Claude-User
User-agent: ClaudeBot
User-agent: anthropic-ai
User-agent: Bingbot
User-agent: Applebot
User-agent: Applebot-Extended
User-agent: DuckAssistBot
User-agent: Amazonbot
User-agent: meta-externalagent
User-agent: cohere-ai
User-agent: YouBot
Allow: /
Disallow: /offerings/*/docs/
Disallow: /api/

Sitemap: {site}/sitemap.xml
"""

LAUNCH = '2026-09-13'   # the rebuild's launch date: the floor for every page's lastmod
MONTHS = {m: i for i, m in enumerate(['january','february','march','april','may','june','july','august','september','october','november','december'], 1)}

def _git_date(path):
    """Last commit date of a committed file (works when the checkout has history); None otherwise."""
    import subprocess
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', path], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        return out or None
    except Exception:
        return None

def lastmod(u, offerings):
    """A date that reflects a meaningful change, never 'today on every deploy':
    articles -> their stated update month; offerings -> Airtable's Last Modified; ported pages -> the 'Updated <date>' they carry;
    committed pages -> their last git commit; everything else -> the launch date."""
    page = os.path.join(ROOT, u.strip('/'), 'index.html') if u != '/' else os.path.join(ROOT, 'index.html')
    src = open(page, encoding='utf-8', errors='ignore').read(20000) if os.path.exists(page) else ''
    if u.startswith('/offerings/'):
        slug = u.strip('/').split('/')[-1]
        m = offerings.get(slug)
        if m: return max(m[:10], LAUNCH)
    m = re.search(r'"dateModified"\s*:\s*"(\d{4}-\d{2})(?:-\d{2})?"', src)
    if m: return m.group(1) + '-01'   # articles state the month they were last revised
    m = re.search(r'Updated\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(20\d\d)', src)
    if m and m.group(1).lower() in MONTHS: return f'{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}'
    for committed in ('index.html', 'register/index.html', 'results/index.html'):
        if u == '/' + committed.replace('index.html', ''):
            return _git_date(committed) or LAUNCH
    return LAUNCH

def main():
    us = urls()
    offerings = {}
    try:
        for o in json.load(open(os.path.join(ROOT, 'build', 'offerings.json'), encoding='utf-8')):
            if o.get('slug') and o.get('modified'): offerings[o['slug']] = o['modified']
    except Exception: pass
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
          '\n'.join(f'  <url><loc>{SITE}{u}</loc><lastmod>{lastmod(u, offerings)}</lastmod></url>' for u in us) + '\n</urlset>\n'
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(xml)
    noindex = os.environ.get('ROBOTS_NOINDEX') == 'true'   # branch / preview deploys must never be indexed
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(
        'User-agent: *\nDisallow: /\n' if noindex else
        ROBOTS.format(site=SITE))
    n_learn = sum(1 for u in us if u.startswith('/learn/') and u != '/learn/')
    open(os.path.join(ROOT, 'llms.txt'), 'w', encoding='utf-8').write(f'''# Baker 1031 Investments

> Real estate securities brokerage founded by Gerald F. "Jerry" Baker, III (FINRA CRD #7537416), specializing in
> 1031 exchange investment solutions: Delaware Statutory Trusts (DSTs), 721 exchange (UPREIT) structures,
> Opportunity Zone funds, oil and gas royalties, REITs and real estate credit. Securities offered through
> Aurora Securities, Inc., member FINRA/SIPC. Educational content only; offers are made solely by PPM.

## Key pages
- [Homepage]({SITE}/): who Jerry is, how he reviews deals, how to get started
- [Available investments]({SITE}/invest/): current DST inventory (details for approved investors)
- [Results]({SITE}/results/): full-cycle track record by sponsor and asset class
- [Learn]({SITE}/learn/): {n_learn} educational articles on 1031 exchanges and DSTs
- [Glossary]({SITE}/glossary/): plain-English definitions of 1031/DST terms
- [Calculators]({SITE}/calculators/): deadline, deferred-tax, boot, recapture, and yield tools
- [Markets]({SITE}/markets/): state-by-state 1031 exchange guides
- [Sponsors]({SITE}/sponsors/): research profiles of DST sponsors
- [Get started]({SITE}/register/): investor registration

## How the site is organized
- Every article, glossary term, market guide and sponsor profile is a plain HTML page with its full text in the markup; nothing is loaded by script.
- Learn articles are written by Jerry Baker and carry an educational disclaimer; they are not investment, tax or legal advice.
- Offerings are described from each sponsor's private placement memorandum; offering documents are available only to logged-in, approved investors.
- Results are sponsor-reported full-cycle figures (average annual return, equity multiple, hold period) and are not a guarantee of future performance.

## Contact
- Jerry Baker, Founder — invest@baker1031.com
- San Francisco: 1700 Montgomery St, Ste 108, San Francisco, CA 94111 — (415) 965-0552
- Los Angeles: 2100 E Grand Ave, 1st Floor, El Segundo, CA 90245 — (310) 896-4227
''')
    # exact build timestamp — the rebuild-watcher function compares it with Airtable's Last Modified.
    # The dataset's shape goes in too: every published performance figure is an average over these
    # rows, and whether the build pulled from Airtable or shipped the committed snapshot was only
    # visible in the build log, where a stale dataset can sit unnoticed for weeks.
    info = {'builtAt': datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')}
    try:
        tsv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fullcycle.tsv')
        with open(tsv, encoding='utf-8') as fh:
            rows = [r for r in csv.reader(fh, delimiter='\t') if r and r[0].strip()][1:]
        info['fullCycle'] = {'deals': len(rows), 'sponsors': len({r[1] for r in rows if len(r) > 1})}
    except OSError:
        pass
    # Any asset class that reaches no property-type page is recorded here too: a sector page that
    # silently drops its programs reads as "no results yet", which is worse than a wrong average.
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import fullcycle as _fc
        stray = _fc.unmapped_types()
        if stray:
            info['unmappedAssetClasses'] = stray
        # Rows Airtable has not given a normalised asset class. They publish under
        # "Other / Unclassified", which is honest but is also a to-do list.
        n = len([r for r in _fc.load() if r['classes'] == [_fc.UNCLASSIFIED]])
        if n:
            info['unclassifiedRows'] = n
    except Exception:
        pass
    # Homepage Select Results cards whose program is not in the dataset: their figures cannot be
    # checked against anything, so they are named here rather than only in the build log.
    try:
        import json as _json, re as _re, sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import build_homepage_results as _cards
        src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
        m = _cards.ARRAY_RE.search(src)
        if m:
            rows = _cards.load_rows()
            stray = ['%s (%s)' % (c.get('title', '?'), c.get('sponsor', '?'))
                     for c in _json.loads(m.group(2)) if not _cards.match(c.get('title', ''), rows)]
            if stray:
                info['unsourcedResultCards'] = stray
    except Exception:
        pass
    open(os.path.join(ROOT, 'build-info.json'), 'w').write(json.dumps(info))
    print(f'[meta] sitemap.xml ({len(us)} urls), robots.txt, llms.txt, build-info.json')

if __name__ == '__main__':
    main()

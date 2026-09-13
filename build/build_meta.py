"""Crawl plumbing written after the pages: sitemap.xml, robots.txt, llms.txt, build-info.json.
The sitemap is derived from the built tree — every index.html that is not marked noindex."""
import os, re, json, datetime

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

def main():
    us = urls()
    today = datetime.date.today().isoformat()
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
          '\n'.join(f'  <url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>' for u in us) + '\n</urlset>\n'
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(xml)
    noindex = os.environ.get('ROBOTS_NOINDEX') == 'true'   # branch / preview deploys must never be indexed
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(
        'User-agent: *\nDisallow: /\n' if noindex else
        f'User-agent: *\nAllow: /\nDisallow: /offerings/*/docs/\nDisallow: /login/?next=\nDisallow: /api/\nSitemap: {SITE}/sitemap.xml\n')
    n_learn = sum(1 for u in us if u.startswith('/learn/') and u != '/learn/')
    open(os.path.join(ROOT, 'llms.txt'), 'w', encoding='utf-8').write(f'''# Baker 1031 Investments

> Real estate securities brokerage founded by Gerald F. "Jerry" Baker, III (FINRA CRD #7537416), specializing in
> 1031 exchange investment solutions: Delaware Statutory Trusts (DSTs), 721 exchange (UPREIT) structures,
> Opportunity Zone funds, oil and gas royalties, REITs and real estate credit. Securities offered through
> Aurora Securities, Inc., member FINRA/SIPC. Educational content only; offers are made solely by PPM.

## Key pages
- [Available investments]({SITE}/invest/): current DST inventory (details for approved investors)
- [Results]({SITE}/results/): full-cycle track record by sponsor and asset class
- [Learn]({SITE}/learn/): {n_learn} educational articles on 1031 exchanges and DSTs
- [Glossary]({SITE}/glossary/): plain-English definitions of 1031/DST terms
- [Calculators]({SITE}/calculators/): deadline, deferred-tax, boot, recapture, and yield tools
- [Markets]({SITE}/markets/): state-by-state 1031 exchange guides
- [Sponsors]({SITE}/sponsors/): research profiles of DST sponsors
- [Get started]({SITE}/register/): investor registration

## Contact
- Jerry Baker, Founder — invest@baker1031.com
- San Francisco: 1700 Montgomery St, Ste 108, San Francisco, CA 94111 — (415) 965-0552
- Los Angeles: 2100 E Grand Ave, 1st Floor, El Segundo, CA 90245 — (310) 896-4227
''')
    # exact build timestamp — the rebuild-watcher function compares it with Airtable's Last Modified
    open(os.path.join(ROOT, 'build-info.json'), 'w').write(json.dumps({'builtAt': datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')}))
    print(f'[meta] sitemap.xml ({len(us)} urls), robots.txt, llms.txt, build-info.json')

if __name__ == '__main__':
    main()

"""Site build entry point (this is what Netlify runs: `python3 build/build.py`).

1. fetch_airtable.py  — refresh build/offerings.json, property photos and offering documents from Airtable
                        (skipped when AIRTABLE_TOKEN is unset: the committed snapshot is used)
1b. fetch_performance.py — refresh build/fullcycle.tsv from the Investment Data (Live) base, same rule
1c. build_homepage_chart.py — redraw the homepage return chart from that dataset, so it cannot drift
                        away from the Results page (it runs before everything that copies index.html's chrome)
1c2. sync_chrome.py      — copy the homepage footer into the committed pages so the site has one footer
1d. build_redirects.py  — refresh the retired-offering 301 list the edge gate imports, from the append-only
                        ledger in build/published-slugs.txt, so a renamed or withdrawn offering never 404s
2. build_inventory.py — regenerate /invest/index.html
3. build_offering.py  — regenerate /offerings/<slug>/index.html for every offering, removing pages for deleted ones
4. build_pages.py     — content/pages/** fragments -> sponsors, markets, glossary, calculators, policies … (+ /assets/css/site.css)
5. build_articles.py  — content/articles/*.md -> /learn/<slug>/ + the /learn/ index
6. build_results_data.py — refresh /results/index.html's dataset from build/fullcycle.tsv
7. build_meta.py      — sitemap.xml, robots.txt, llms.txt, build-info.json

The homepage, registration and login pages are committed as-is and are not touched here; the results page
is committed too, but its dataset is refreshed from build/fullcycle.tsv — the single source behind the
Results page and every sponsor-page track record.
Every generated page takes its nav and footer from index.html, so editing the homepage chrome updates the whole site
on the next build.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
env = dict(os.environ, SITE_ROOT=ROOT)

def run(script):
    print('==>', script, flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE, env=env)
    if r.returncode: sys.exit(r.returncode)

# Netlify installs requirements.txt automatically; make sure the two dependencies are there either way.
try:
    import markdown_it, PIL  # noqa: F401
except ImportError:
    print('==> pip install -r requirements.txt', flush=True)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '-r', os.path.join(ROOT, 'requirements.txt')])

for s in ('fetch_airtable.py', 'fetch_performance.py', 'build_homepage_chart.py', 'sync_chrome.py', 'build_redirects.py', 'build_inventory.py', 'build_offering.py', 'build_results_data.py', 'build_pages.py', 'build_articles.py', 'build_meta.py'):
    run(s)
print('build complete')

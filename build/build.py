"""Site build entry point (this is what Netlify runs: `python3 build/build.py`).

1. fetch_airtable.py  — refresh build/offerings.json, property photos and offering documents from Airtable
                        (skipped when AIRTABLE_TOKEN is unset: the committed snapshot is used)
2. build_inventory.py — regenerate /invest/index.html
3. build_offering.py  — regenerate /offerings/<slug>/index.html for every offering, removing pages for deleted ones
4. build_pages.py     — content/pages/** fragments -> sponsors, markets, glossary, calculators, policies … (+ /assets/css/site.css)
5. build_articles.py  — content/articles/*.md -> /learn/<slug>/ + the /learn/ index
6. build_meta.py      — sitemap.xml, robots.txt, llms.txt, build-info.json

The homepage, registration, login and results pages are committed as-is and are not touched here.
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

for s in ('fetch_airtable.py', 'build_inventory.py', 'build_offering.py', 'build_pages.py', 'build_articles.py', 'build_meta.py'):
    run(s)
print('build complete')

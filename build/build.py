"""Site build entry point (this is what Netlify runs).

1. fetch_airtable.py  — refresh build/offerings.json + property photos from Airtable (skipped when AIRTABLE_TOKEN is unset)
2. build_inventory.py — regenerate /invest/index.html from the offerings
3. build_offering.py  — regenerate /offerings/<slug>/index.html for every offering, removing pages for deleted ones

The homepage, registration, login and results pages are committed as-is and are not touched here.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
env = dict(os.environ, SITE_ROOT=ROOT)

def run(script):
    print('==>', script, flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE, env=env)
    if r.returncode: sys.exit(r.returncode)

run('fetch_airtable.py')
run('build_inventory.py')
run('build_offering.py')
print('build complete')

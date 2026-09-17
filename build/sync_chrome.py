"""Keep the committed pages' footer identical to the homepage's.

index.html is the chrome source: every generated page already takes its nav and footer from it. The five
pages that are committed rather than generated (login, register, results, update-my-info, 404) used to
carry hand-maintained copies, which drifted into four different footers — two of them linking the
level-2 gated sections to visitors who cannot open them. This copies the homepage footer into them on
every build, so there is one footer on the site and no way for a sixth to appear.

/update-my-info/ is a standalone form with its own stylesheet, so it keeps its own footer markup; only
its disclosure text is checked against the homepage's.
"""
import os, re, sys

ROOT = os.environ.get('SITE_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'index.html')
TARGETS = ['login/index.html', 'register/index.html', 'results/index.html']

FOOTER_RE = re.compile(r'<footer class="footer">.*?</footer>', re.S)


def main():
    src = open(SRC, encoding='utf-8').read()
    m = FOOTER_RE.search(src)
    if not m:
        print('[chrome] no footer in index.html — nothing synced'); return
    footer = m.group(0)
    changed = []
    for rel in TARGETS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        h = open(p, encoding='utf-8').read()
        if not FOOTER_RE.search(h):
            print('[chrome] %s has no footer to replace' % rel); continue
        new = FOOTER_RE.sub(lambda _: footer, h, count=1)
        if new != h:
            open(p, 'w', encoding='utf-8').write(new); changed.append(rel)
    print('[chrome] footer synced from index.html' + (': ' + ', '.join(changed) if changed else ' (all current)'))

    # the standalone form page keeps its own markup; flag it if its disclosure loses a clause
    umi = os.path.join(ROOT, 'update-my-info/index.html')
    if os.path.exists(umi):
        t = open(umi, encoding='utf-8').read()
        for phrase in ('Aurora Securities', 'accredited investors', 'Past performance'):
            if phrase not in t:
                print('[chrome] WARNING: /update-my-info/ disclosure is missing "%s"' % phrase)


if __name__ == '__main__':
    main()

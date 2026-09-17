"""Keep the committed pages' nav and footer identical to the homepage's.

index.html is the chrome source: every generated page already takes its nav and footer from it. The
pages that are committed rather than generated (login, register, results, update-my-info, 404) used to
carry hand-maintained copies, which drifted -- into four different footers, two of them linking the
level-2 gated sections to visitors who cannot open them, and into navs that had missed two later
fixes: /results/ and /login/ still printed the hover label as real text inside the link
(<span class="nav__hand">Home</span>) instead of drawing it from data-label in CSS, which puts every
nav word on the page twice for a crawler. This copies the homepage nav and footer into them on every
build, so there is one nav and one footer on the site and no way for a sixth to appear.

The nav's CSS block is synced too, not just its markup. Copying only the markup is what broke the
hover label on /results/ and /login/: the synced markup draws the handwriting from data-label via
::after, their own stylesheets still had the older rule that expected the text inline, and the
label silently rendered as nothing at all on a white bar.

Two things are deliberately per-page and are re-applied after the copy: aria-current on the link for
the page you are on, and the homepage's #top anchors, which become / everywhere else.

/register/ keeps its own nav. It is a multi-step form with a progress bar in the header and no primary
links, on purpose -- a funnel should not offer four ways out of it. Its footer is still synced.

/update-my-info/ is a standalone form with its own stylesheet, so it keeps its own chrome; only its
disclosure text is checked against the homepage's.
"""
import os, re, sys

ROOT = os.environ.get('SITE_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, 'index.html')
FOOTER_TARGETS = ['login/index.html', 'register/index.html', 'results/index.html']
# register is left out: see the module docstring
NAV_TARGETS = {'login/index.html': None, 'results/index.html': '/results/'}

FOOTER_RE = re.compile(r'<footer class="footer">.*?</footer>', re.S)
NAV_RE = re.compile(r'<header class="nav" id="nav">.*?</header>', re.S)

NAVCSS_START = '  /* ---------- Sticky nav ---------- */'
NAVCSS_END_SRC = '  /* section anchors land below the sticky bar */'
# each committed page follows its nav block with its own section comment
NAVCSS_END_RE = re.compile(r'\n\s*/\* -+ [^*]+? -+ \*/')


def navcss_of(src):
    i = src.index(NAVCSS_START)
    j = src.index(NAVCSS_END_SRC, i)
    # normalised to exactly one trailing newline: the homepage block ends in blank lines, and
    # keeping them added one more line to each target on every build, so the committed pages
    # showed a diff after a no-op rebuild.
    return src[i:j].rstrip() + '\n'


def swap_navcss(page, navcss):
    try:
        i = page.index(NAVCSS_START)
    except ValueError:
        return page, False
    m = NAVCSS_END_RE.search(page, i + len(NAVCSS_START))
    if not m:
        return page, False
    return page[:i] + navcss + page[m.start() + 1:], True


def nav_for(nav, current):
    """The homepage nav, retargeted for a subpage."""
    nav = nav.replace('href="#top"', 'href="/"')
    nav = re.sub(r'\saria-current="page"', '', nav)
    if current:
        nav = nav.replace(f'<a href="{current}">', f'<a href="{current}" aria-current="page">', 1)
    return nav


def main():
    src = open(SRC, encoding='utf-8').read()
    fm = FOOTER_RE.search(src)
    nm = NAV_RE.search(src)
    if not fm or not nm:
        print('[chrome] index.html is missing its nav or footer — nothing synced'); return
    footer, nav = fm.group(0), nm.group(0)
    navcss = navcss_of(src)

    changed = []
    for rel in FOOTER_TARGETS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        h = open(p, encoding='utf-8').read(); before = h
        if FOOTER_RE.search(h):
            h = FOOTER_RE.sub(lambda _: footer, h, count=1)
        else:
            print('[chrome] %s has no footer to replace' % rel)
        if rel in NAV_TARGETS:
            if NAV_RE.search(h):
                h = NAV_RE.sub(lambda _: nav_for(nav, NAV_TARGETS[rel]), h, count=1)
            else:
                print('[chrome] %s has no nav to replace' % rel)
            h, ok = swap_navcss(h, navcss)
            if not ok:
                print('[chrome] %s: could not locate its nav CSS block' % rel)
        if h != before:
            open(p, 'w', encoding='utf-8').write(h); changed.append(rel)
    print('[chrome] nav + footer synced from index.html' + (': ' + ', '.join(changed) if changed else ' (all current)'))

    # the standalone form page keeps its own markup; flag it if its disclosure loses a clause
    umi = os.path.join(ROOT, 'update-my-info/index.html')
    if os.path.exists(umi):
        t = open(umi, encoding='utf-8').read()
        for phrase in ('Aurora Securities', 'accredited investors', 'Past performance'):
            if phrase not in t:
                print('[chrome] WARNING: /update-my-info/ disclosure is missing "%s"' % phrase)


if __name__ == '__main__':
    main()

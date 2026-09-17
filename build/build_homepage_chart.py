"""Rewrite the homepage return chart from build/fullcycle.tsv, the same dataset the Results page uses.

Why this exists: the Results page regenerates from the dataset on every deploy (build_results_data.py) while
the homepage chart was hand-written SVG. The moment the dataset moved — a sponsor added in Airtable, a deal
corrected — the two pages disagreed about Baker 1031's own published performance, silently. That is a
compliance problem, not a cosmetic one, so the chart is generated too.

What it rewrites, all from the dataset: the two Baker 1031 bars (path height, value label and its position),
their <title> tooltips, the <desc> accessibility summary, the hidden data table rows, and the program counts
and preferred-sponsor names in the sources note. The three third-party bars are left alone — they are
published figures from Fundrise, Cove Capital and Origin, not ours to compute.

The chart's axis is read out of the SVG rather than assumed. If a Baker 1031 figure would run off the top of
that axis the chart is left exactly as committed and the build prints a warning: a bar drawn past its own
axis, or silently clipped to it, misstates the number. Rescale the axis by hand and the next build picks it up.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fullcycle as fc

ROOT = os.environ.get('SITE_ROOT') or os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'index.html')
ALL_LABEL = 'All Tracked Sponsors'
PREF_LABEL = 'Baker 1031 Preferred Sponsors'


def axis(html):
    """(y at 0%, svg units per percentage point, axis maximum) read from the chart's own gridline ticks."""
    ticks = [(float(v), float(y)) for y, v in
             re.findall(r'<text class="c-tick" x="\d+" y="([\d.]+)"[^>]*>([\d.]+)%</text>', html)]
    ticks = [(v, y - 4.0) for v, y in ticks]        # tick text sits 4 units below its gridline
    if len(ticks) < 2:
        return None
    ticks.sort()
    (v0, y0), (v1, y1) = ticks[0], ticks[-1]
    return y0, (y0 - y1) / (v1 - v0), v1


def bar(html, label, value):
    """Redraw one bar: the rounded path's top, the value label and its y, and the tooltip."""
    g = re.search(r'(<g style="--i:\d+" class="c-bar[^"]*" tabindex="0">\s*<title>%s: )[\d.]+%%( average annual '
                  r'return</title>.*?<path class="c-fill" d="M[\d.]+ [\d.]+ V)[\d.]+( a4 4 0 0 1 4 -4 h[\d.]+ '
                  r'a4 4 0 0 1 4 4 V[\d.]+ Z"/>\s*<text class="c-val" x="[\d.]+" y=")[\d.]+("[^>]*>)[\d.]+%%(</text>)'
                  % re.escape(label), html, re.S)
    if not g:
        return None
    y0, per, _ = AX
    top = round(y0 - value * per + 4, 1)
    return html[:g.start()] + ('%s%.2f%%%s%s%s%.1f%s%.2f%%%s'
                               % (g.group(1), value, g.group(2), top, g.group(3), top - 12,
                                  g.group(4), value, g.group(5))) + html[g.end():]


def names(items):
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def main():
    global AX
    rows = fc.load()
    pref_names = fc.preferred()
    pref_rows = [r for r in rows if r['sponsor'] in pref_names]
    all_st, pref_st = fc.stats(rows), fc.stats(pref_rows)
    # The note says "average of N programs", so N is how many were actually averaged — rows with a
    # reported return — not every row in the table. A row with no disclosed multiple is not in the mean.
    all_n = len([r for r in rows if r['ret'] is not None])
    pref_n = len([r for r in pref_rows if r['ret'] is not None])
    if not all_st or not pref_st:
        print('WARNING: the dataset has no returns to average. Leaving the homepage chart as committed.')
        return 0

    html = open(PAGE, encoding='utf-8').read()
    AX = axis(html)
    if not AX:
        print("WARNING: could not read the chart's axis out of index.html. Leaving the homepage chart as committed.")
        return 0
    _, _, top_pct = AX
    over = [(n, v) for n, v in ((ALL_LABEL, all_st['ret']), (PREF_LABEL, pref_st['ret'])) if v > top_pct]
    if over:
        print('WARNING: %s above the chart\'s %g%% axis, so the homepage chart was NOT updated and still shows '
              'the committed figures — a bar drawn past its own axis, or clipped to it, misstates the number. '
              'Raise the axis in index.html (the c-grid lines and c-tick labels) and rebuild.'
              % ('; '.join('%s now averages %.2f%%' % (n, v) for n, v in over), top_pct))
        return 0

    before = html
    for label, st in ((ALL_LABEL, all_st), (PREF_LABEL, pref_st)):
        out = bar(html, label, st['ret'])
        if out is None:
            print('WARNING: could not find the "%s" bar in index.html. Homepage chart left as committed.' % label)
            return 0
        html = out

    # Hidden data table (the accessible equivalent of the bars).
    for label, st in ((ALL_LABEL.replace('Baker 1031 ', ''), all_st), (PREF_LABEL, pref_st)):
        html = re.sub(r'(<tr><td>%s</td><td>)[\d.]+%%(</td></tr>)' % re.escape(label),
                      lambda m, v=st['ret']: '%s%.2f%%%s' % (m.group(1), v, m.group(2)), html, count=1)

    # Screen-reader summary of the whole chart.
    html = re.sub(r'(<desc id="chart-desc">.*?all tracked sponsors )[\d.]+%(, Baker 1031 preferred sponsors )[\d.]+%',
                  lambda m: '%s%.2f%%%s%.2f%%' % (m.group(1), all_st['ret'], m.group(2), pref_st['ret']),
                  html, count=1, flags=re.S)

    # Sources note: the program counts and the preferred-sponsor names must match the dataset they describe.
    # The em dash is written both literally and as &mdash; in this sentence, so match either.
    DASH = r'(?:&mdash;|\u2014)'
    html = re.sub(r'(All Tracked Sponsors ' + DASH + r' simple average of the )\d+( of )\d+( full-cycle programs)',
                  lambda m: '%s%d%s%d%s' % (m.group(1), all_n, m.group(2), len(rows), m.group(3)), html, count=1)
    html = re.sub(r'(Baker 1031 Preferred Sponsors ' + DASH + r' the )\d+( of those programs from preferred sponsors \()[^)]*(\))',
                  lambda m: '%s%d%s%s%s' % (m.group(1), pref_n, m.group(2), names(sorted(pref_names)), m.group(3)),
                  html, count=1)

    # The hold answer in the FAQ quoted its own program count and average, which had drifted to more
    # than twice the dataset's size. Generated here from the same rows as the chart above it.
    holds = [r['hold'] for r in rows if r.get('hold')]
    if holds:
        html = re.sub(r'Across the [\d,]+ completed sponsor programs in the track record data I maintain, '
                      r'the average hold was [\d.]+ years\.',
                      'Across the %d completed sponsor programs in the track record data I maintain, the '
                      'average hold was %.1f years.' % (len(holds), sum(holds) / len(holds)),
                      html, count=1)

    if html == before:
        print('[chart] already current: %s %.2f%% (n=%d), preferred %.2f%% (n=%d)'
              % (ALL_LABEL.lower(), all_st['ret'], all_n, pref_st['ret'], pref_n))
        return 0
    open(PAGE, 'w', encoding='utf-8').write(html)
    print('[chart] all tracked %.2f%% (n=%d), preferred %.2f%% (n=%d) from %s'
          % (all_st['ret'], all_n, pref_st['ret'], pref_n, names(sorted(pref_names))))
    return 0


if __name__ == '__main__':
    sys.exit(main())

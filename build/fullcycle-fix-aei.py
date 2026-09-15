"""AEI's rows in the Results dataset carry sale-proceeds equity multiples — capital returned at sale,
with the distributions paid over the hold left out — and an annual return derived from them as
(EM - 1) / hold. For net-lease deals held 10-20 years that understates the result badly. The sponsor
page carried the total-return figures all along. This puts those back into build/fullcycle.tsv."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, 'match.py')).read().split("print('matched %d of %d page rows'")[0])

TSV = '/home/claude/repo/build/fullcycle.tsv'
cands = [(t, p) for sp, p, t in matches if sp == 'AEI']
BLANK = {("Arby's", 'TN', 20.04), ('Rite Aid', 'NY', 18.23)}   # no page counterpart; sale-only figures

def numf(s):
    s = (s or '').strip()
    try: return float(s)
    except ValueError: return None
def fmt(v, nd=6):
    return '' if v is None else (('%.*f' % (nd, v)).rstrip('0').rstrip('.') or '0')

taken, out, fixed, blanked, missed = set(), [], 0, 0, []
with open(TSV, encoding='utf-8') as f:
    rd = csv.reader(f, delimiter='\t'); header = next(rd)
    for r in rd:
        r = [c.strip() for c in r] + [''] * (8 - len(r))
        if r[1] == 'AEI':
            h = numf(r[6])
            pool = [(i, t, p) for i, (t, p) in enumerate(cands)
                    if i not in taken and norm(t['name']) == norm(r[0]) and t['state'] == r[3]
                    and (h is None or t['hold'] is None or abs(t['hold'] - h) < 0.01)]
            if pool:
                i, t, p = pool[0]; taken.add(i)
                r[4], r[5], r[6] = fmt(p['ret']), fmt(p['em']), fmt(p['hold'])
                if p['city']: r[7] = p['city']
                fixed += 1
            elif any(n == r[0] and s == r[3] and h is not None and abs(h - hh) < 0.02 for n, s, hh in BLANK):
                r[4], r[5] = '', ''        # unreported: renders as "—", left out of the averages
                blanked += 1
            else:
                missed.append(r[:7])
        out.append(r)
with open(TSV, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(header)
    for r in out: w.writerow(r)
print('AEI: %d deals restored to total-return figures, %d marked unreported' % (fixed, blanked))
for m in missed: print('   unmatched AEI row left as-is:', m)

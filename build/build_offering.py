import re, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo
# Repo mode: SITE_ROOT points at the checked-out site; the homepage (index.html) supplies the nav/footer and
# shared assets are referenced by path. Scratch mode (no SITE_ROOT) is the original Cowork build layout.
ROOT = os.environ.get('SITE_ROOT')
HERE = os.path.dirname(os.path.abspath(__file__))
if ROOT:
    h = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    a = { 'logo':'/assets/media/logo.png', 'jerry':'/assets/media/jerry-baker.jpg', 'skyline':'/assets/media/sf-skyline.png' }
    deals = []
else:
    h = open('/home/claude/hero-jerry.html').read()
    a = json.load(open('assets.json'))
    deals = json.load(open('deal_imgs.json'))
inv = open(os.path.join(HERE, 'build_inventory.py'), encoding='utf-8').read()

def between(start, end, src=h):
    i = src.index(start); j = src.index(end, i); return src[i:j]

navcss = between('  /* ---------- Sticky nav ---------- */', '  /* section anchors land below the sticky bar */')
nav_mobile = between('    .nav__inner{ gap:16px; height:54px; }', '    .ctabar__inner{')
footcss = between('  /* ---------- Footer ---------- */', '  /* ---------- Sticky nav ---------- */')
badgecss = between('  .badge{', '  .hand-inline{')
navhtml = re.search(r'<header class="nav" id="nav">.*?</header>', h, flags=re.S).group(0)
navhtml = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', navhtml)
navhtml = navhtml.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"').replace('<a href="/invest/">', '<a href="/invest/" aria-current="page">')
foot = re.search(r'<footer class="footer">.*?</footer>', h, flags=re.S).group(0)
foot = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', foot)
foot = foot.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"')
navjs = between("  // Nav: shadow once scrolled; mobile menu toggle", "})();\n</script>")
tipcss = between('  /* rating tooltip: Jerry\'s explanation from the homepage */', '  .table .tip__box', inv)

# ---- offering data: Airtable "Investment Data (Live)" -> Offering Data (offerings.json; images cached in at_imgs/) ----
import base64, os, html as _html
AT = json.load(open(os.path.join(HERE, 'offerings.json'), encoding='utf-8'))
RATING_MAP = { 'Preferred':'highly', 'Common':'approved', 'Not Preferred':'specialized', 'Insufficient Data':'specialized' }
RATING_TEXT = {
  'highly': 'The investment passes our review, and I particularly like the sponsor, business plan, underwriting, and terms. I’ll explain what earned it that second thumb.',
  'approved': 'The investment passes our review, but I have more reservations. We’ll discuss those concerns and whether the tradeoffs make sense for you.',
  'specialized': 'This investment is specialized. It may have a place in certain situations, but we need a specific reason to use it.',
  'rejected': 'The investment didn’t meet our standards. I passed.',
}
def esc(x): return _html.escape(str(x if x is not None else ''), quote=True)
def paras(text): return [esc(t.strip()) for t in re.split(r'\n\s*\n|\n', text or '') if t.strip()]
def img_of(slug):
    if ROOT:
        d = os.path.join(ROOT, 'assets/media/offerings')
        for name in (slug + '-hero.jpg', slug + '.jpg', slug + '.png', slug + '.webp'):
            if os.path.exists(os.path.join(d, name)): return '/assets/media/offerings/' + name
        return ''
    f = 'at_imgs/' + slug + '.jpg'
    return 'data:image/jpeg;base64,' + base64.b64encode(open(f, 'rb').read()).decode() if os.path.exists(f) else ''
def full_of(slug):
    # the untouched original as uploaded to Airtable (any format), linked from the offering photo
    if not ROOT: return ''
    d = os.path.join(ROOT, 'assets/media/offerings')
    for ext in ('jpg', 'png', 'webp', 'gif'):
        if os.path.exists(os.path.join(d, f'{slug}.{ext}')): return f'/assets/media/offerings/{slug}.{ext}'
    return ''
def make_O(r):
    types = r['types'] or []; locs = r['locations'] or []
    rating = 'rejected' if r['status'] == 'Rejected' else RATING_MAP.get(r['coverage'] or '', 'specialized')
    y1 = r['income'][0]
    # An offering with no projected operating distributions at all (a land programme, a zero-coupon
    # structure) has no yield to state. Showing it as 0.00% reads like a forecast of nothing; it is the
    # absence of a forecast. This used to be hard-coded to one slug, which stopped being true at the
    # 2026-09-16 cutover, so it is read off the cash-flow schedule instead.
    no_income = not any(isinstance(v, (int, float)) and v for v in r['income'])
    allcash = not r['debt']
    # A debt-free offering used to render four labelled rows with $0 and two em dashes in them.
    # Say the one thing that is true instead.
    if allcash:
        debt_block = ('<p style="margin:0;font-size:15px">This offering is debt-free. It uses no financing, '
                      'so there is no loan amount, rate, term or refinancing risk.</p>')
    else:
        debt_block = ('<dl class="kv" style="grid-template-columns:1fr">'
                      '<div><dt>Loan amount</dt><dd>%s</dd></div>'
                      '<div><dt>Leverage (loan to total capitalization)</dt><dd>%d%%</dd></div>'
                      '<div><dt>Rate</dt><dd>%s</dd></div>'
                      '<div><dt>Term</dt><dd>%s</dd></div></dl>'
                      % (money(r['debt'] or 0), round((r['ltv'] or 0) * 100),
                         esc(r['rate'] or '\u2014'),
                         (f"{r['loanTerm']:g} years" if r['loanTerm'] else '\u2014')))
    return dict(
        debtBlock=debt_block,
        slug=r['slug'], name=esc(r['name']), sponsor=esc(r['sponsor'] or '—'),
        type=esc(' · '.join(types) or '—'), city=esc(' · '.join(locs) or 'Location TBD'), state='',
        status=r['status'] or 'Available', rating=rating, ratingText=RATING_TEXT[rating],
        yld=(None if no_income else (round(y1 * 100, 2) if isinstance(y1, (int, float)) else None)),
        zeroCoupon=no_income,
        ltv=round((r['ltv'] or 0) * 100), exit721=(r['exit721'] or 'None').lower(),
        equityRaise=r['equity'] or 0, totalOffering=r['total'] or 0, loanAmount=r['debt'] or 0,
        purchasePrice=r['purchasePrice'], initialReserves=r['reserves'],
        # Interest Rate is the sponsor's own words now ("5.708%", "No Loan - All-Cash"), not a number to format.
        loanRate=esc('—' if allcash else (r['rate'] or '—')),
        loanTerm=('—' if allcash or not r['loanTerm'] else f"{r['loanTerm']:g} years"),
        lender=esc('None — all-cash offering' if allcash else (r['lender'] or '—')),
        amortization=esc('—' if allcash else (r['amort'] or '—')),
        registration=esc(r['registration'] or '—'), propertyTypes=esc(' · '.join(types) or '—'),
        # Printed as the PPM states it; only the hyphen in a range is normalised to an en dash.
        holdTarget=esc(re.sub(r'(\d)\s*-\s*(\d)', lambda m: m.group(1) + '–' + m.group(2), r['holdLabel'] or '—')),
        photos=[img_of(r['slug'])], photoFull=full_of(r['slug']),
        overview=paras(r['description']),
        highlights=[esc(h) for h in r['highlights']],
        props=[dict(addr=esc(a.strip())) for a in (r['addresses'] or '').split(';') if a.strip()],
        cashflow=[(v * 100 if isinstance(v, (int, float)) else None) for v in r['income']],
        cfBasis=esc(r['cfBasis'] or ''), cfDisclosure=esc(r['cfDisclosure'] or ''), postForecast=esc(r['postForecast'] or ''),
        docs=[(esc(re.sub(r'\.(pdf|docx?|xlsx?|pptx?)$', '', d['filename'], flags=re.I)), esc(d.get('rel') or '')) for d in r['docs']],
        notes=paras(r['notes']),
        features=[], risks=[],
        typeLabel=(types[0] if types else 'DST'),
        metaDesc=_meta_desc(r, types, locs),
        ogImage=(img_of(r['slug']) if img_of(r['slug']).startswith('/') else ''),
    )

def _meta_desc(r, types, locs):
    """Search snippet: what the offering is, where, by whom, then the first sentence of the sponsor description."""
    bits = [r['name'], 'a ' + (' / '.join(types) if types else 'DST') + ' 1031 exchange offering' + (' in ' + ', '.join(locs) if locs else '')]
    if r.get('sponsor'): bits[-1] += ' sponsored by ' + r['sponsor']
    d = re.sub(r'\s+', ' ', (r.get('description') or '')).strip()
    first = re.split(r'(?<=[.!?])\s', d)[0] if d else ''
    out = bits[0] + ': ' + bits[1] + '.' + ((' ' + first) if first else '')
    if len(out) > 158: out = out[:out.rfind(' ', 0, 156)] + '…'
    return out

# Availability Status is a single-select in Airtable, so Jerry can add a choice at any time. A status this
# map has not seen must not take the build down — it renders with the default pill and the build says so.
STATUS_CLS = { 'Available':'', 'Limited Availability':'status--limited', 'Pending Approval':'status--soon',
               'Under Review':'status--soon', 'Closed':'status--sold', 'Rejected':'status--rejected' }
_unknown_status = set()
def status_cls(status):
    if status not in STATUS_CLS: _unknown_status.add(status)
    return STATUS_CLS.get(status, '')
RATING = { 'highly':('badge--ok','👍👍','Highly Approved'), 'approved':('badge--ok','👍','Approved'), 'specialized':('badge--warn','❗','Specialized'), 'rejected':('badge--no','👎','Rejected') }
EXIT = { 'mandatory':'Mandatory', 'optional':'Optional', 'none':'None' }
def money(n): return '—' if n is None else '$' + f'{n:,.0f}'
def render(O):
    rc, re_, rl = RATING[O['rating']]

    thumbs = ''.join(f'<button type="button" class="gal__thumb{" is-on" if i==0 else ""}" data-i="{i}" aria-label="Photo {i+1}"><img src="{src}" alt=""></button>' for i,src in enumerate(O['photos']))
    highlights = ''.join(f'<li>{x}</li>' for x in O['highlights'])
    # one property → a single address line; several → a list
    if len(O['props']) == 1:
        props_html = f'<p class="addr">{O["props"][0]["addr"]}</p>'
        props_title = 'Property address'
    else:
        props_html = '<ul class="addrs">' + ''.join(f'<li class="addr">{p["addr"]}</li>' for p in O['props']) + '</ul>'
        # Some offerings list street addresses; others list county or basin groupings that each cover
        # several properties. Counting the entries as "addresses" then contradicts the text beside it
        # ("Property addresses 4" over "14 deeded properties"), so only a real address list is counted.
        addressish = sum(1 for p in O['props'] if re.match(r'\s*\d', p['addr']))
        props_title = (f'Property addresses <span class="sec__count">{len(O["props"])}</span>'
                       if addressish == len(O['props']) else 'Property locations')
    cf = [(i, v) for i, v in enumerate(O['cashflow']) if v is not None]
    # The heading is the same on every offering; the sponsor's own term for the figure is a note under
    # the table, not a second name for the section. Seven different headings for one row of numbers made
    # the offerings look like they were measuring different things.
    cf_basis = ''
    cf_note = ('<p class="cf-basis">These are the sponsor\u2019s projections, stated in the offering documents as '
               '\u201c' + O['cfBasis'] + '\u201d. They are not guaranteed.</p>') if O['cfBasis'] else ''
    cf_hidden = '' if cf else ' hidden'
    cf_head = ''.join(f'<th class="num">Yr {i+1}</th>' for i, v in cf)
    cf_row = ''.join(f'<td class="num">{v:.2f}%</td>' for i, v in cf)
    cf_stack = ''.join(f'<div><dt>Year {i+1}</dt><dd>{v:.2f}%</dd></div>' for i, v in cf)
    features = ''.join(f'<li>{x}</li>' for x in O['features'])
    risks = ''.join(f'<li>{x}</li>' for x in O['risks'])
    def _doc_open(i, m):
        if not m: return '<li><span class="doc doc--pending" data-doc="%d" title="Document not yet available">' % i
        return '<li><a class="doc" href="%s" data-doc="%d" target="_blank" rel="noopener">' % (m, i)
    docs = ''.join(_doc_open(i, m) + f'<span class="doc__icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" ><path d="M8 17H16" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 13H12" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 2.5V3C13 5.82843 13 7.24264 13.8787 8.12132C14.7574 9 16.1716 9 19 9H19.5M20 10.6569V14C20 17.7712 20 19.6569 18.8284 20.8284C17.6569 22 15.7712 22 12 22C8.22876 22 6.34315 22 5.17157 20.8284C4 19.6569 4 17.7712 4 14V9.45584C4 6.21082 4 4.58831 4.88607 3.48933C5.06508 3.26731 5.26731 3.06508 5.48933 2.88607C6.58831 2 8.21082 2 11.4558 2C12.1614 2 12.5141 2 12.8372 2.11401C12.9044 2.13772 12.9702 2.165 13.0345 2.19575C13.3436 2.34355 13.593 2.593 14.0919 3.09188L18.8284 7.82843C19.4065 8.40649 19.6955 8.69552 19.8478 9.06306C20 9.4306 20 9.83935 20 10.6569Z" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span class="doc__name">{t}</span>' + ('</a></li>' if m else '</span></li>') for i,(t,m) in enumerate(O['docs']))
    notes = ''.join(f'<p>{x}</p>' for x in O['notes'])
    overview = ''.join(f'<p>{x}</p>' for x in O['overview'])

    page = r'''<!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="utf-8">
    <script>/* approved-investor gate: mark the document before first paint so gated content never flashes */
    try{ if(/(?:^|;\s*)b31_ui=/.test(document.cookie)) document.documentElement.classList.add('is-logged-in'); }catch(e){}</script>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    ''' + seo.head(title=(O['name'] + ' — 1031 Exchange DST | Baker 1031' if len(O['name']) <= 26 else
                        (O['name'] + ' | Baker 1031' if len(O['name']) <= 46 else O['name'])), desc=O['metaDesc'], canonical='https://baker1031.com/offerings/' + O['slug'] + '/', image=('https://baker1031.com' + O['ogImage']) if O.get('ogImage') else seo.OG_IMAGE, image_alt=O['name'] + ' property photo', graph=[seo.webpage('https://baker1031.com/offerings/' + O['slug'] + '/', O['name'], O['metaDesc'], {'isAccessibleForFree': False, 'hasPart': {'@type': 'WebPageElement', 'isAccessibleForFree': False, 'cssSelector': '.gated'}}), seo.breadcrumbs([('Home', 'https://baker1031.com/'), ('Available Investments' if O['status'] in ('Available', 'Limited Availability') else 'Investments', 'https://baker1031.com/invest/'), (O['name'], None)])]) + r'''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Special+Gothic&family=Caveat:wght@400..700&display=swap" rel="stylesheet">
    <style>
/* Brand fonts (self-hosted): Guardian Sans for text, Sanomat for headings */
:root{ --page:#FFFFFF; --accent-2:#00A071; --rose:#00A071;
        --black:#000; --white:#fff;
        --accent:#00A071; --accent-hover:#008F63; --accent-soft:#FCF7F0;
        --grey:#000000; --grey-light:rgba(0,0,0,.6); --hair:#D5D2CD; --hair-strong:#D5D2CD;
        --radius:6px;
        --font:"Special Gothic", "Helvetica Neue", Helvetica, Arial, sans-serif;
    --display:"Special Gothic", "Helvetica Neue", Helvetica, Arial, sans-serif;
        --hand:"Caveat", "Segoe Print", "Bradley Hand", cursive;
      }
      *{ box-sizing:border-box; }
      html{ -webkit-text-size-adjust:100%; scroll-behavior:smooth; }
      body{ margin:0; background:var(--page); color:var(--black); font-family:var(--font); line-height:1.5; -webkit-font-smoothing:antialiased; }
      ::selection{ background:var(--accent); color:var(--white); }
      .btn{
        display:inline-flex; align-items:center; justify-content:center; gap:10px;
        padding:12px 20px; background:var(--accent); color:var(--black);
        border:1px solid var(--accent); border-radius:var(--radius);
        font:inherit; font-size:14px; font-weight:600; text-decoration:none; cursor:pointer;
        transition:background .18s ease, border-color .18s ease;
      }
      .btn:hover{ background:var(--accent-hover); border-color:var(--accent-hover); }
      .btn svg{ width:16px; height:16px; }
      .btn--secondary{ background:transparent; color:var(--grey); border-color:#D5D2CD; }
      .btn--secondary:hover{ background:transparent; color:var(--accent); border-color:var(--accent); }
      .wrap{ max-width:calc(1200px + 48px); margin:0 auto; padding:0 24px; }
      .rule{ max-width:calc(1200px + 48px); margin:0 auto; padding:0 24px; }
      .rule::before{ content:""; display:block; height:1px; background:#D5D2CD; }
      .rule--strong::before{ height:2px; background:#D5D2CD; }

      /* ---------- Sticky nav (from the homepage) ---------- */
    ''' + navcss + r'''  .nav__links a[aria-current="page"] .nav__word{ color:var(--black); }
      [id]{ scroll-margin-top:84px; }

      /* ---------- Rating badges + tooltip ---------- */
    ''' + badgecss + tipcss + r'''
      /* ---------- Breadcrumb + title ---------- */
      .crumbs{ display:flex; align-items:center; gap:8px; margin:0; padding:20px 0 0; font-size:13px; color:var(--grey-light); list-style:none; flex-wrap:wrap; }
      .crumbs a{ color:var(--grey); text-decoration:none; } .crumbs a:hover{ color:var(--accent); }
      .crumbs li + li::before{ content:"›"; margin-right:8px; color:rgba(0,0,0,.55); }
      .title{ display:flex; align-items:flex-end; justify-content:space-between; gap:24px; padding:22px 0 8px; flex-wrap:wrap; }
      .title__eyebrow{ margin:0 0 8px; font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--grey-light); display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
      .status{ display:inline-flex; align-items:center; gap:7px; font-size:11px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:var(--grey); }
      .status::before{ content:""; width:7px; height:7px; border-radius:50%; background:#00A071; }
      .status--limited::before{ background:#F59E0B; } .status--closing::before{ background:#EF4444; } .status--soon::before{ background:var(--accent); } .status--sold::before{ background:rgba(0,0,0,.55); }
      .title h1{ margin:0; font-size:clamp(28px,3vw,40px); font-weight:700; line-height:1.1; letter-spacing:-.02em; }
      .title__sub{ margin:8px 0 0; font-size:14px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--grey-light); }
      .title__sub strong{ color:var(--black); font-weight:600; }
      .title__right{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
      .tip{ position:relative; display:inline-flex; }

      /* ---------- Gallery ---------- */
      .gal{ display:grid; grid-template-columns:minmax(0,2.3fr) minmax(0,1fr); gap:10px; }
      .gal__main{ position:relative; aspect-ratio:16 / 9; border-radius:var(--radius); overflow:hidden; background:#FCF7F0; }
      .gal__main img{ width:100%; height:100%; object-fit:cover; display:block; }
      .gal__count{ position:absolute; right:12px; bottom:12px; padding:5px 10px; border-radius:999px; background:rgba(0,0,0,.6); color:#fff; font-size:12px; font-weight:600; }
      .gal__side{ display:grid; grid-template-rows:repeat(2, minmax(0,1fr)); gap:10px; }
      .gal__thumbs{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:10px; }
      .gal__thumb{ padding:0; border:2px solid transparent; border-radius:var(--radius); overflow:hidden; background:#FCF7F0; cursor:pointer; min-height:0; }
      .gal__thumb img{ width:100%; height:100%; object-fit:cover; display:block; }
      .gal__thumb.is-on{ border-color:var(--accent); }
      .gal__thumb:focus-visible{ outline:none; box-shadow:0 0 0 3px rgba(0,160,113,.35); }

      /* ---------- Key stats strip ---------- */
      .stats{ display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); margin:24px 0 0; padding:0; border:1px solid var(--hair-strong); border-radius:var(--radius); overflow:hidden; }
      .stats > div{ padding:16px 18px; border-left:1px solid var(--hair); min-width:0; }
      .stats > div:first-child{ border-left:0; }
      .stats dt{ margin:0 0 4px; font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--grey-light); }
      .stats dd{ margin:0; font-size:22px; font-weight:700; letter-spacing:-.01em; color:var(--black); font-variant-numeric:tabular-nums; }
      .stats dd.is-accent{ color:var(--accent); }
      .stats dd small{ display:block; font-size:12px; font-weight:500; color:var(--grey); letter-spacing:0; margin-top:2px; }

      /* ---------- Body layout ---------- */
      .body{ display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:0 56px; padding:20px 0 72px; align-items:start; }
      .photo{ aspect-ratio:16 / 9; border-radius:var(--radius); overflow:hidden; background:#FCF7F0; margin-bottom:28px; }
      .photo img{ width:100%; height:100%; object-fit:cover; display:block; }
      .sec{ padding:32px 0; border-top:1px solid var(--hair); }
      .sec:first-child{ border-top:0; padding-top:0; }
      .sec h2{ margin:0 0 16px; font-size:22px; font-weight:700; letter-spacing:-.015em; line-height:1.2; }
      .sec p{ margin:0 0 14px; font-size:16px; line-height:1.7; color:var(--grey); }
      .sec p:last-child{ margin-bottom:0; }
      .cols{ display:grid; grid-template-columns:1fr 1fr; gap:24px 40px; }
      .list{ margin:0; padding:0 0 0 18px; color:var(--grey); font-size:15px; line-height:1.6; }
      .list li{ margin:0 0 8px; padding-left:4px; }
      .list li::marker{ color:var(--accent); }
      .list--risk li::marker{ color:#B45309; }
      .kv{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:0 32px; margin:0; }
      .kv div{ display:flex; justify-content:space-between; gap:16px; padding:10px 0; border-bottom:1px solid var(--hair); font-size:14.5px; }
      .kv dt{ color:var(--grey); } .kv dd{ margin:0; font-weight:600; color:var(--black); text-align:right; }
      .tablewrap{ overflow-x:auto; border:1px solid var(--hair-strong); border-radius:var(--radius); }
      table{ width:100%; border-collapse:collapse; font-size:14px; }
      th, td{ padding:11px 14px; text-align:left; border-bottom:1px solid var(--hair); }
      th{ font-size:11px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--grey-light); background:#FCF7F0; white-space:nowrap; }
      tr:last-child td{ border-bottom:0; }
      td.num, th.num{ text-align:right; font-variant-numeric:tabular-nums; }
      .cf{ min-width:760px; } .cf td.num{ font-weight:600; }
      .cf-stack{ display:none; }
      .cfnote{ margin:12px 0 0; font-size:13px; line-height:1.6; color:var(--grey-light); }
      .status--rejected::before{ background:#EF4444; }
      .sec__count{ display:inline-flex; align-items:center; justify-content:center; min-width:22px; height:22px; padding:0 7px; margin-left:8px; border-radius:11px; background:var(--accent-soft); color:var(--accent); font-size:12px; font-weight:700; vertical-align:middle; }
      .addrs{ list-style:none; margin:0; padding:0; }
      .addr{ display:flex; flex-wrap:wrap; gap:4px 16px; align-items:baseline; margin:0; padding:10px 0; border-bottom:1px solid var(--hair); font-size:15px; }
      .addrs .addr:last-child{ border-bottom:0; }
      .addr{ color:var(--black); }
      .foot-note{ margin:10px 0 0 !important; font-size:12px !important; color:var(--grey-light) !important; line-height:1.5 !important; }
      .docs{ list-style:none; margin:0; padding:0; display:grid; gap:8px; }
      .doc{ display:flex; align-items:center; gap:14px; padding:12px 14px; border:1px solid var(--hair-strong); border-radius:var(--radius); text-decoration:none; color:inherit; transition:border-color .15s; }
      .doc:hover{ border-color:var(--accent); }
      .doc__icon{ width:34px; height:34px; border-radius:6px; background:var(--accent-soft); color:var(--accent); display:inline-flex; align-items:center; justify-content:center; flex:0 0 auto; }
      .doc__icon svg{ width:18px; height:18px; }
      .doc__name{ font-size:14.5px; font-weight:600; color:var(--black); }
      .doc:hover .doc__name{ color:var(--accent); }

      /* Jerry's notes: soft click-through */
      .notes{ border:1px solid var(--hair-strong); border-radius:var(--radius); overflow:hidden; }
      .notes__head{ display:flex; align-items:center; gap:14px; padding:16px 18px; background:#FCF7F0; border-bottom:1px solid var(--hair); }
      .notes__photo{ width:44px; height:44px; border-radius:50%; object-fit:cover; flex:0 0 auto; }
      .notes__head h2{ margin:0; font-size:18px; }
      .notes__head h2 .hand{ font-family:var(--hand); font-weight:600; color:var(--accent); font-size:1.4em; line-height:.8; display:inline-block; transform:rotate(-3deg); margin-right:.06em; }
      .notes__gate{ padding:18px; }
      .notes__gate p{ font-size:14px; color:var(--grey); margin:0 0 14px; }
      .notes__body{ padding:18px; }
      .notes__body p{ font-size:15.5px; line-height:1.7; color:var(--black); }
      .notes__body[hidden]{ display:none; }
      .notes__gate[hidden]{ display:none; }
      .notes__fine{ font-size:12px !important; color:var(--grey-light) !important; margin-top:10px !important; }

      /* ---------- Sticky side card ---------- */
      .side{ position:sticky; top:84px; }
      .card{ border:1px solid var(--hair-strong); border-radius:var(--radius); background:var(--white); padding:20px; }
      .card__min{ margin:0; font-size:13px; color:var(--grey); }
      .card__min strong{ display:block; font-size:28px; font-weight:700; letter-spacing:-.02em; color:var(--black); }
      .card .kv{ grid-template-columns:minmax(0,1fr); margin:8px 0 0; }
      .card .kv div:last-child{ border-bottom:0; }
      .card .kv div{ padding:9px 0; font-size:14px; align-items:baseline; flex-wrap:wrap; gap:2px 16px; }
      .card .kv dt{ flex:0 0 auto; }
      .card .kv dd{ flex:1 1 auto; min-width:0; overflow-wrap:anywhere; }   /* long values (lender, amortization) wrap under the label instead of truncating */
      .card .kv dd .status{ white-space:normal; text-align:right; justify-content:flex-end; }
      .card__top{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:4px; }
      .card__label{ font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--grey-light); }
      .card .kv .status{ font-size:11px; }
      .card__top .badge{ height:26px; font-size:11.5px; padding:0 9px 0 8px; gap:6px; }
      .card__top .tip__box{ right:0; }
      .card .btn{ width:100%; }
      .card .btn + .btn{ margin-top:8px; }
      .card__fine{ margin:14px 0 0; font-size:11.5px; line-height:1.5; color:var(--grey-light); }
      .card__jerry{ display:flex; align-items:center; gap:12px; margin-top:18px; padding-top:16px; border-top:1px solid var(--hair); }
      .card__jerry img{ width:44px; height:44px; border-radius:50%; object-fit:cover; }
      .card__jerry p{ margin:0; font-size:13px; color:var(--grey); line-height:1.4; }
      .card__jerry strong{ display:block; color:var(--black); font-weight:600; }
      .card__jerry a{ color:var(--accent); text-decoration:none; }
      .backlink{ display:inline-flex; align-items:center; gap:6px; margin-top:16px; font-size:13px; color:var(--grey-light); text-decoration:none; }
      .backlink:hover{ color:var(--accent); }

      .disclosure{ padding:24px 0 0; font-size:11px; line-height:1.55; color:rgba(0,0,0,.6); max-width:900px; }

      /* ---------- Approved-investor gate ---------- */
      .gate{ max-width:calc(1200px + 48px); margin:0 auto; padding:24px 24px 96px; }
      .wrap--head{ padding-bottom:0; }
      .gate__card{ max-width:560px; margin:0 auto; text-align:center; }
      .gate__card h2{ margin:0 0 12px; font-size:clamp(28px,3vw,36px); font-weight:700; line-height:1.1; letter-spacing:-.02em; }
      .gate__card p{ margin:0 0 24px; font-size:16px; line-height:1.65; color:var(--grey); }
      .gate__actions{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; }
      .gate__actions .btn--secondary{ background:var(--white); color:var(--black); border-color:var(--hair-strong); }
      .gate__actions .btn--secondary:hover{ background:#FCF7F0; border-color:var(--black); }
      .gate__note{ margin:20px 0 0 !important; font-size:13px !important; color:var(--grey-light) !important; }
      html:not(.is-logged-in) .gated{ display:none; }
      .is-logged-in .gate{ display:none; }

      /* ---------- Footer (from the homepage) ---------- */
    ''' + footcss + r'''
      /* ---------- Responsive ---------- */
      @media (max-width:1100px){ .stats{ grid-template-columns:repeat(3, minmax(0,1fr)); } .stats > div:nth-child(4){ border-left:0; } .stats > div:nth-child(-n+3){ border-bottom:1px solid var(--hair); } .body{ grid-template-columns:minmax(0,1fr) 300px; gap:0 36px; } }
      @media (max-width:900px){
    ''' + nav_mobile + r'''    .wrap{ padding:0 20px; }
        .gal{ grid-template-columns:1fr; }
        .gal__side{ grid-template-rows:none; }
        .gal__thumbs{ grid-template-columns:repeat(4, minmax(0,1fr)); grid-template-rows:none; height:auto; }
        .gal__thumb{ aspect-ratio:4 / 3; }
        .body{ grid-template-columns:1fr; padding:28px 0 56px; }
        .side{ position:static; order:-1; margin-bottom:8px; }
        .cols{ grid-template-columns:1fr; }
        .kv{ grid-template-columns:1fr; }
        .stats{ grid-template-columns:repeat(2, minmax(0,1fr)); }
        .stats > div:nth-child(odd){ border-left:0; } .stats > div:nth-child(-n+4){ border-bottom:1px solid var(--hair); }
        .cf{ display:none; } .cf-stack{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:0 20px; margin:0; }
        .cf-stack div{ display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--hair); font-size:14px; }
        .cf-stack dt{ color:var(--grey); } .cf-stack dd{ margin:0; font-weight:600; }
        .footer__inner{ grid-template-columns:1fr 1fr; padding:40px 20px 32px; }
        .skyline{ padding-top:32px; }
        .footer__brand{ grid-column:1 / -1; }
        .footer__offices{ grid-column:1 / -1; display:grid; grid-template-columns:1fr 1fr; column-gap:24px; }
        .footer__offices .footer__label{ grid-column:1 / -1; }
      }
    /* Headings in Sanomat (one weight); everything else stays in Guardian Sans */
h1:not(#_),h2:not(#_),h3:not(#_){font-family:var(--display);font-weight:400;letter-spacing:-.01em}
</style>
    </head>
    <body id="top" data-offering="''' + O['slug'] + r'''">

    ''' + navhtml + r'''

    <div class="wrap wrap--head">
      <ol class="crumbs" aria-label="Breadcrumb">
        <li><a href="/">Home</a></li>
        <li><a href="/invest/">''' + ('Available Investments' if O['status'] in ('Available', 'Limited Availability') else 'Investments') + r'''</a></li>
        <li aria-current="page">''' + O['name'] + r'''</li>
      </ol>
      <div class="title">
        <div>
          <h1>''' + O['name'] + r'''</h1>
          <p class="title__sub">''' + O['type'] + ' · ' + O['city'] + r'''</p>
        </div>
      </div>
    </div>

    <section class="gate" id="gate" aria-labelledby="gate-heading">
      <div class="gate__card">
        <h2 id="gate-heading">The details of this offering are for approved investors.</h2>
        <p>Log in with the email address on your account to see the photos, financials, distributions and documents. New here? Registration takes a few minutes, and the last step is scheduling a call with me.</p>
        <div class="gate__actions">
          <a class="btn" href="/login/?next=/offerings/''' + O['slug'] + r'''/">Log In</a>
          <a class="btn btn--secondary" href="/register/">Create an Account</a>
        </div>
        <p class="gate__note">Offerings are available solely to accredited investors and are made only by a sponsor’s private placement memorandum.</p>
      </div>
    </section>

    <div class="gated">

    <div class="wrap">
      <div class="body">
        <div>
          <div class="photo">''' + (('<a href="' + O['photoFull'] + '" target="_blank" rel="noopener" title="Open the full-resolution photo">') if O['photoFull'] else '') + r'''<img src="''' + O['photos'][0] + r'''" alt="''' + O['name'] + r'''">''' + ('</a>' if O['photoFull'] else '') + r'''</div>
          <section class="sec" id="overview">
            <h2>Overview</h2>
            ''' + overview + r'''
          </section>

          <section class="sec" id="highlights">
            <h2>Key highlights</h2>
            <ul class="list">''' + highlights + r'''</ul>
          </section>

          <section class="sec" id="financials">
            <h2>Financials</h2>
            <div class="cols">
              <div>
                <h3 style="margin:0 0 10px;font-size:14px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--grey-light)">Offering</h3>
                <dl class="kv" style="grid-template-columns:1fr">
                  <div><dt>Total offering</dt><dd>''' + money(O['totalOffering']) + r'''</dd></div>
                  <div><dt>Equity raise</dt><dd>''' + money(O['equityRaise']) + r'''</dd></div>
                  <div><dt>Purchase price</dt><dd>''' + money(O['purchasePrice']) + r'''</dd></div>
                  <div><dt>Initial reserves</dt><dd>''' + money(O['initialReserves']) + r'''</dd></div>
                </dl>
              </div>
              <div>
                <h3 style="margin:0 0 10px;font-size:14px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--grey-light)">Debt</h3>
                ''' + O['debtBlock'] + r'''
              </div>
            </div>
            <h3 style="margin:28px 0 10px;font-size:14px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--grey-light)">Projected distributions''' + cf_basis + r'''</h3>
            <div class="tablewrap"''' + cf_hidden + r'''><table class="cf">
              <thead><tr>''' + cf_head + r'''</tr></thead>
              <tbody><tr>''' + cf_row + r'''</tr></tbody>
            </table></div>''' + cf_note + r'''
            <dl class="cf-stack">''' + cf_stack + r'''</dl>''' + cf_note + r'''
            <p class="foot-note">Projections from the sponsor’s offering documents. Distributions are not guaranteed and may be lower than shown or suspended. See the PPM for assumptions.</p>
          </section>

          <section class="sec" id="notes">
            <div class="notes">
              <div class="notes__head"><h2><span class="hand">Jerry’s</span> notes on this offering</h2></div>
              <div class="notes__gate" id="notes-gate">
                <p>These are my opinions after reviewing the offering. They aren’t investment advice or a recommendation for any particular investor, and they don’t replace the PPM — please read it before investing.</p>
                <button type="button" class="btn btn--secondary" id="notes-open">Understood — show me the notes</button>
              </div>
              <div class="notes__body" id="notes-body" hidden>
                ''' + notes + r'''
                <p class="notes__fine">Opinion only. Not investment, tax, or legal advice. Review the private placement memorandum and consult your own advisors.</p>
              </div>
            </div>
          </section>

          <section class="sec" id="properties">
            <h2>''' + props_title + r'''</h2>
            ''' + props_html + r'''
          </section>

          <section class="sec" id="documents">
            <h2>Documents</h2>
            <ul class="docs">''' + docs + r'''</ul>
          </section>

          <p class="disclosure">This page summarizes information from the sponsor’s private placement memorandum and is provided for informational purposes only. It is not an offer to sell or a solicitation of an offer to buy any security; offers are made only by the PPM to accredited investors. Figures are as of the offering date and subject to change. DST interests are speculative, illiquid, and involve a high degree of risk, including loss of principal. Securities offered through Aurora Securities, Inc., member FINRA/SIPC.</p>
        </div>

        <aside class="side" id="request">
          <div class="card">
            <div class="card__top">
              <span class="card__label">Offering details</span>
              <span class="tip" tabindex="0"><span class="badge ''' + rc + r'''"><span class="badge__emoji" aria-hidden="true">''' + re_ + r'''</span>''' + rl + r'''</span> <span class="tip__box" role="tooltip"><strong>''' + re_ + ' ' + rl + r'''</strong> ''' + O['ratingText'] + r'''<small>My assessment, not a guarantee of performance or the return of your principal.</small></span></span>
            </div>
            <dl class="kv">
              <div><dt>Investment Sponsor</dt><dd>''' + O['sponsor'] + r'''</dd></div>
              <div><dt>Availability Status</dt><dd><span class="status ''' + status_cls(O['status']) + r'''">''' + O['status'] + r'''</span></dd></div>
              <div><dt>Registration</dt><dd>''' + O['registration'] + r'''</dd></div>
              <div><dt>721 Exchange</dt><dd>''' + EXIT[O['exit721']] + r'''</dd></div>
              <div><dt>Property Type</dt><dd>''' + O['propertyTypes'] + r'''</dd></div>
              <div><dt>Equity</dt><dd>''' + money(O['equityRaise']) + r'''</dd></div>
              <div><dt>Debt</dt><dd>''' + money(O['loanAmount']) + r'''</dd></div>
              <div><dt>Total Investment</dt><dd>''' + money(O['totalOffering']) + r'''</dd></div>
              <div><dt>Leverage</dt><dd>''' + f"{O['ltv']}%" + r'''</dd></div>
              <div><dt>Initial Reserves</dt><dd>''' + money(O['initialReserves']) + r'''</dd></div>
              <div><dt>Lender</dt><dd title="''' + O['lender'] + r'''">''' + O['lender'] + r'''</dd></div>
              <div><dt>Amortization</dt><dd title="''' + O['amortization'] + r'''">''' + O['amortization'] + r'''</dd></div>
              <div><dt>Estimated Hold Period</dt><dd>''' + O['holdTarget'] + r'''</dd></div>
            </dl>
            <div class="card__jerry">
              <img src="{{JERRY}}" alt="">
              <p><strong>Jerry Baker</strong>Founder, Baker 1031 Investments<br><a href="tel:+14159650552">(415) 965-0552</a></p>
            </div>
          </div>
          <a class="backlink" href="/invest/">← Back to all investments</a>
        </aside>
      </div>
    </div>

    </div><!-- /.gated -->
    <div class="rule rule--strong" aria-hidden="true"></div>
    ''' + foot + r'''

    <div class="skyline" aria-hidden="true">
      <img src="{{SKYLINE}}" alt="" width="2000" height="459">
    </div>

    <script>
    (function(){
    ''' + navjs + r'''})();
    </script>
    <script>
    (function(){
      // Jerry's notes: soft click-through
      document.getElementById('notes-open').addEventListener('click', function(){
        document.getElementById('notes-gate').hidden = true;
        document.getElementById('notes-body').hidden = false;
      });
      // documents: files are downloaded at build time into offerings/<slug>/docs/ and hard-gated at the edge;
      // a doc that has no file yet stays a placeholder.

    })();
    </script>

    </body>
    </html>
    '''
    # tidy: the gallery side has one thumbs block (remove the empty second one)
    page = page.replace('''<div class="gal__thumbs">''' + thumbs + '''</div>
          <div class="gal__thumbs"></div>''', '''<div class="gal__thumbs">''' + thumbs + '''</div>''')
    page = page.replace('''  .gal__side{ display:grid; grid-template-rows:repeat(2, minmax(0,1fr)); gap:10px; }
      .gal__thumbs{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:10px; }''','''  .gal__side{ display:grid; min-height:0; }
      .gal__thumbs{ display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); grid-template-rows:repeat(2, minmax(0,1fr)); gap:10px; height:100%; }''')
    return page


# ---- build: one page per offering (repo: offerings/<slug>/index.html; scratch: /home/claude/offerings/<slug>.html + offering.html sample) ----
SAMPLE = 'passco-allure-dst'
built = set()
for rec in AT:
    O = make_O(rec)
    page = render(O)
    out = page.replace('{{LOGO}}', a['logo']).replace('{{SKYLINE}}', a['skyline']).replace('{{JERRY}}', a['jerry'])
    if ROOT:
        d = os.path.join(ROOT, 'offerings', O['slug']); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(out); built.add(O['slug'])
    else:
        os.makedirs('/home/claude/offerings', exist_ok=True)
        open('/home/claude/offerings/' + O['slug'] + '.html', 'w', encoding='utf-8').write(out)
        if O['slug'] == SAMPLE:
            open(os.path.join(HERE, 'offering_template.html'), 'w', encoding='utf-8').write(page)
            open('/home/claude/offering.html', 'w', encoding='utf-8').write(out)
            print('sample built', len(out))
if _unknown_status:
    print('NOTE: Airtable has Availability Status values this build has no styling for, so they render with the '
          'default pill: ' + ', '.join(sorted(x for x in _unknown_status if x)) + '. Add them to STATUS_CLS in '
          'build/build_offering.py and to STATUS_CLS / STATUS_ORDER / STATUS_SHORT in build/build_inventory.py.')
if ROOT:
    # an offering deleted (or renamed) in Airtable disappears from the site on the next build
    import shutil
    for slug in os.listdir(os.path.join(ROOT, 'offerings')):
        if slug not in built and os.path.isdir(os.path.join(ROOT, 'offerings', slug)):
            shutil.rmtree(os.path.join(ROOT, 'offerings', slug)); print('removed stale page', slug)
print('offering pages', len(AT))

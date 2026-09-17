import re, json, random, os, sys, html
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

def between(start, end, src=h):
    i = src.index(start); j = src.index(end, i); return src[i:j]

# ---- pieces reused from the homepage ----
navcss = between('  /* ---------- Sticky nav ---------- */', '  /* section anchors land below the sticky bar */')
nav_mobile = between('    .nav__inner{ gap:16px; height:54px; }', '    .ctabar__inner{')
footcss = between('  /* ---------- Footer ---------- */', '  /* ---------- Sticky nav ---------- */')
badgecss = between('  .badge{', '  .hand-inline{')
navhtml = re.search(r'<header class="nav" id="nav">.*?</header>', h, flags=re.S).group(0)
navhtml = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', navhtml)
navhtml = navhtml.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"')
# mark Invest as current
navhtml = navhtml.replace('<a href="/invest/">', '<a href="/invest/" aria-current="page">')
foot = re.search(r'<footer class="footer">.*?</footer>', h, flags=re.S).group(0)
foot = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', foot)
foot = foot.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"')
navjs = between("  // Nav: shadow once scrolled; mobile menu toggle", "})();\n</script>")

# ---- inventory: Airtable "Investment Data (Live)" -> Offering Data (pulled into offerings.json by fetch_airtable.py; images cached in at_imgs/) ----
import base64, os
AT = json.load(open(os.path.join(HERE, 'offerings.json'), encoding='utf-8'))
# Rating badge = Coverage Review, except a Rejected availability status wins.
RATING_MAP = { 'Preferred':'highly', 'Common':'approved', 'Not Preferred':'specialized', 'Insufficient Data':'specialized' }
def rating_of(o):
    if o['status'] == 'Rejected': return 'rejected'
    return RATING_MAP.get(o['coverage'] or '', 'specialized')
def img_of(slug):
    if ROOT:
        d = os.path.join(ROOT, 'assets/media/offerings')
        for name in (slug + '-card.jpg', slug + '.jpg', slug + '.png', slug + '.webp'):
            if os.path.exists(os.path.join(d, name)): return '/assets/media/offerings/' + name
        return ''
    f = 'at_imgs/' + slug + '.jpg'
    return 'data:image/jpeg;base64,' + base64.b64encode(open(f, 'rb').read()).decode() if os.path.exists(f) else ''
def loc_label(states):
    if not states: return 'Location TBD'
    if len(states) <= 2: return ' · '.join(states)
    return str(len(states)) + ' states'
OFFERINGS = []
for o in AT:
    y1 = o['income'][0]
    # No projected operating distributions at all -> no yield to state (see build_offering.py).
    no_income = not any(isinstance(v, (int, float)) and v for v in o['income'])
    OFFERINGS.append(dict(
        slug=o['slug'], name=o['name'], sponsor=o['sponsor'] or '',
        types=o['types'] or [], typeLabel=' · '.join(o['types'] or ['—']),
        locations=o['locations'] or [], locLabel=loc_label(o['locations'] or []),
        status=o['status'] or 'Available', registration=o['registration'] or '',
        yld=(None if no_income else (round(y1 * 100, 2) if isinstance(y1, (int, float)) else None)),
        zeroCoupon=no_income,
        ltv=(round((o['ltv'] or 0) * 100)),
        exit721=(o['exit721'] or 'None').lower(),
        rating=rating_of(o), hold=o['hold'] or 0,
        img=img_of(o['slug']),
    ))
print('offerings', len(OFFERINGS))

page = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<script>/* approved-investor gate: mark the document before first paint so gated content never flashes */
try{ if(/(?:^|;\s*)b31_ui=/.test(document.cookie)) document.documentElement.classList.add('is-logged-in'); }catch(e){}</script>
<meta name="viewport" content="width=device-width, initial-scale=1">
''' + seo.head(title='Available 1031 Exchange Investments: DSTs, 721 Exchanges & More — Baker 1031 Investments', desc='Current 1031 exchange investments tracked by Jerry Baker: Delaware Statutory Trusts, 721 exchange DSTs and other offerings with sponsor, property type, location, year-one yield and LTV. Details for approved investors.', canonical='https://baker1031.com/invest/', graph=[seo.webpage('https://baker1031.com/invest/', 'Available Investments', 'Current 1031 exchange investments with sponsor, property type, location, yield and LTV.', {'isAccessibleForFree': False, 'hasPart': {'@type': 'WebPageElement', 'isAccessibleForFree': False, 'cssSelector': '.lockwrap'}}), seo.breadcrumbs([('Home', 'https://baker1031.com/'), ('Available Investments', None)])]) + r'''
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400..700&display=swap" rel="stylesheet">
<style>
/* Brand fonts (self-hosted): Guardian Sans for text, Sanomat for headings */
@font-face{font-family:"Guardian Sans";src:url(/assets/fonts/guardian-sans-400.woff2) format("woff2");font-weight:400;font-style:normal;font-display:swap}
@font-face{font-family:"Guardian Sans";src:url(/assets/fonts/guardian-sans-400i.woff2) format("woff2");font-weight:400;font-style:italic;font-display:swap}
@font-face{font-family:"Guardian Sans";src:url(/assets/fonts/guardian-sans-500.woff2) format("woff2");font-weight:500;font-style:normal;font-display:swap}
@font-face{font-family:"Guardian Sans";src:url(/assets/fonts/guardian-sans-600.woff2) format("woff2");font-weight:600;font-style:normal;font-display:swap}
@font-face{font-family:"Guardian Sans";src:url(/assets/fonts/guardian-sans-700.woff2) format("woff2");font-weight:700;font-style:normal;font-display:swap}
@font-face{font-family:"Sanomat";src:url(/assets/fonts/sanomat-400.woff2) format("woff2");font-weight:400;font-style:normal;font-display:swap}

  :root{
    --black:#000; --white:#fff;
    --accent:rgb(0,84,153); --accent-hover:rgb(0,66,122); --accent-soft:#EEF3F9;
    --grey:#4B5563; --grey-light:#6B7280; --hair:#E5E7EB; --hair-strong:#CBD2D9;
    --radius:6px;
    --font:"Guardian Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
    --display:"Sanomat", Georgia, "Times New Roman", serif;
    --hand:"Caveat", "Segoe Print", "Bradley Hand", cursive;
  }
  *{ box-sizing:border-box; }
  html{ -webkit-text-size-adjust:100%; }
  body{ margin:0; background:var(--white); color:var(--black); font-family:var(--font); line-height:1.5; -webkit-font-smoothing:antialiased; }
  ::selection{ background:var(--accent); color:var(--white); }
  .btn{
    display:inline-flex; align-items:center; gap:10px;
    padding:12px 20px; background:var(--accent); color:var(--white);
    border:1px solid var(--accent); border-radius:var(--radius);
    font:inherit; font-size:14px; font-weight:600; text-decoration:none; cursor:pointer;
    transition:background .18s ease, border-color .18s ease;
  }
  .btn:hover{ background:var(--accent-hover); border-color:var(--accent-hover); }
  .btn svg{ width:16px; height:16px; }
  .btn--secondary{ background:transparent; color:var(--grey); border-color:#D1D5DB; }
  .btn--secondary:hover{ background:transparent; color:var(--accent); border-color:var(--accent); }

  /* ---------- Sticky nav (from the homepage) ---------- */
''' + navcss + r'''  .nav__links a[aria-current="page"] .nav__word{ color:var(--black); }
  [id]{ scroll-margin-top:72px; }

  /* ---------- Rating badges (from the homepage) ---------- */
''' + badgecss + r'''
  /* ---------- Page head ---------- */
  .head{
    max-width:calc(1200px + 48px); margin:0 auto; padding:56px 24px 28px;
  }
  .head h1{
    margin:0 0 12px;
    font-size:clamp(30px,3vw,40px); font-weight:700; line-height:1.1; letter-spacing:-.02em;
  }
  .head h1 .hand{ font-family:var(--hand); font-weight:600; color:var(--accent); font-size:1.3em; line-height:.8; display:inline-block; transform:rotate(-3deg) translateY(.04em); margin-right:.08em; }
  .head p{ margin:0; max-width:720px; font-size:16px; line-height:1.65; color:var(--grey); }
  .rule{ max-width:calc(1200px + 48px); margin:0 auto; padding:0 24px; }
  .rule::before{ content:""; display:block; height:1px; background:#E5E7EB; }
  .rule--strong::before{ height:2px; background:#CBD2D9; }

  /* ---------- Layout: filter chips across the top, results fill the width ---------- */
  .inv{ max-width:calc(1200px + 48px); margin:0 auto; padding:28px 24px 72px; }
  .fbar{ display:flex; align-items:center; gap:10px; position:relative; }
  .fbar__chips{ display:flex; align-items:center; gap:10px; flex:1 1 auto; min-width:0; flex-wrap:nowrap; }
  .select{
    appearance:none; font:inherit; font-size:14px; color:var(--black);
    padding:9px 34px 9px 12px; background:var(--white) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='none'%3E%3Cpath d='M4 6l4 4 4-4' stroke='%234B5563' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") no-repeat right 12px center / 14px;
    border:1px solid var(--hair-strong); border-radius:var(--radius); outline:none; cursor:pointer;
  }
  .select:focus{ border-color:var(--accent); box-shadow:0 0 0 3px rgba(0,84,153,.18); }
  .chipwrap{ position:relative; flex:0 0 auto; }
  .chipwrap.is-hidden{ display:none; }
  .chip{
    display:inline-flex; align-items:center; gap:8px; white-space:nowrap;
    padding:9px 12px 9px 14px; font:inherit; font-size:13.5px; font-weight:600; color:var(--grey);
    background:var(--white); border:1px solid var(--hair-strong); border-radius:999px; cursor:pointer;
    transition:border-color .15s, color .15s, background .15s;
  }
  .chip:hover{ border-color:var(--accent); color:var(--black); }
  .chip svg{ width:12px; height:12px; flex:0 0 auto; transition:transform .15s; }
  .chip[aria-expanded="true"]{ border-color:var(--accent); color:var(--black); }
  .chip[aria-expanded="true"] svg{ transform:rotate(180deg); }
  .chip.is-set{ background:var(--accent-soft); border-color:var(--accent); color:var(--accent); }
  .chip__val{ font-weight:600; }
  .chip--more{ flex:0 0 auto; }
  .chip--more.is-hidden{ display:none; }
  .chip--more.is-set{ background:var(--accent-soft); }
  .chip--clear{ flex:0 0 auto; padding-left:12px; border-style:dashed; color:var(--grey); }
  .chip--clear:hover{ color:#B91C1C; border-color:#FCA5A5; background:#FEF2F2; }
  .chip--clear[hidden]{ display:none; }

  /* popover panel under a chip */
  .pop{
    position:absolute; top:calc(100% + 8px); left:0; z-index:30;
    min-width:260px; max-width:340px;
    background:var(--white); border:1px solid var(--hair-strong); border-radius:var(--radius);
    box-shadow:0 12px 32px rgba(0,0,0,.12); padding:6px 0 0;
  }
  .pop[hidden]{ display:none; }
  .pop__list{ max-height:280px; overflow:auto; padding:4px 8px; }
  .check{ display:flex; align-items:center; gap:10px; font-size:14px; color:var(--grey); cursor:pointer; padding:7px 8px; border-radius:4px; }
  .check:hover{ background:#F9FAFB; }
  .check input{ position:absolute; opacity:0; width:0; height:0; }
  .check__box{ width:18px; height:18px; border:2px solid var(--hair-strong); border-radius:4px; display:inline-flex; align-items:center; justify-content:center; color:var(--white); flex:0 0 auto; transition:background .15s, border-color .15s; }
  .check__box svg{ width:11px; height:11px; opacity:0; }
  .check input:checked ~ .check__box{ background:var(--accent); border-color:var(--accent); }
  .check input:checked ~ .check__box svg{ opacity:1; }
  .check input:focus-visible ~ .check__box{ box-shadow:0 0 0 3px rgba(0,84,153,.25); }
  .check input:checked ~ .check__text{ color:var(--black); }
  .check__count{ margin-left:auto; font-size:12px; color:#9CA3AF; }
  .pop__range{ padding:14px 16px 8px; }
  .pop__rangehead{ display:flex; justify-content:space-between; align-items:baseline; margin:0 0 10px; font-size:13px; color:var(--grey); }
  .pop__rangehead output{ font-size:16px; font-weight:700; color:var(--accent); font-variant-numeric:tabular-nums; }
  input[type="range"]{ width:100%; accent-color:var(--accent); margin:0; }
  .range__scale{ display:flex; justify-content:space-between; font-size:11.5px; color:#9CA3AF; margin-top:4px; }
  .pop__range.is-off input[type="range"]{ opacity:.35; }
  .pop__range.is-off .pop__rangehead{ opacity:.5; }
  .pop__alt{ padding:4px 12px 10px; }
  .altbtn{
    display:flex; align-items:center; gap:10px; width:100%; white-space:nowrap;
    padding:9px 10px; font:inherit; font-size:14px; color:var(--grey); text-align:left;
    background:var(--white); border:1px solid var(--hair-strong); border-radius:var(--radius); cursor:pointer;
    transition:border-color .15s, background .15s, color .15s;
  }
  .altbtn small{ font-size:12px; color:var(--grey-light); margin-left:auto; }
  .altbtn:hover{ border-color:var(--accent); }
  .altbtn.is-on{ border-color:var(--accent); background:var(--accent-soft); color:var(--black); }
  .altbtn__box{ width:18px; height:18px; border:2px solid var(--hair-strong); border-radius:4px; display:inline-flex; align-items:center; justify-content:center; color:var(--white); flex:0 0 auto; }
  .altbtn__box svg{ width:11px; height:11px; opacity:0; }
  .altbtn.is-on .altbtn__box{ background:var(--accent); border-color:var(--accent); }
  .altbtn.is-on .altbtn__box svg{ opacity:1; }
  .pop__foot{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:10px 12px; border-top:1px solid var(--hair); margin-top:4px; }
  .pop__reset{ font:inherit; font-size:13px; color:var(--grey-light); background:none; border:0; padding:0; cursor:pointer; text-decoration:underline; text-decoration-style:dotted; text-decoration-color:var(--accent); text-underline-offset:3px; }
  .pop__reset:hover{ color:var(--accent); }
  .pop__done{ font:inherit; font-size:13px; font-weight:600; color:var(--white); background:var(--accent); border:1px solid var(--accent); border-radius:var(--radius); padding:7px 14px; cursor:pointer; }
  .pop__done:hover{ background:var(--accent-hover); }

  /* "all filters" modal */
  .modal{ position:fixed; inset:0; z-index:80; display:flex; align-items:center; justify-content:center; padding:24px; background:rgba(0,0,0,.4); }
  .modal[hidden]{ display:none; }
  .modal__panel{ width:100%; max-width:720px; max-height:calc(100vh - 48px); overflow:auto; background:var(--white); border-radius:8px; box-shadow:0 24px 64px rgba(0,0,0,.25); }
  .modal__head{ display:flex; align-items:center; justify-content:space-between; padding:18px 22px; border-bottom:1px solid var(--hair); position:sticky; top:0; background:var(--white); z-index:1; }
  .modal__head h2{ margin:0; font-size:18px; font-weight:700; letter-spacing:-.01em; }
  .modal__close{ width:34px; height:34px; border-radius:50%; border:1px solid var(--hair-strong); background:var(--white); cursor:pointer; display:inline-flex; align-items:center; justify-content:center; color:var(--grey); }
  .modal__close:hover{ color:var(--accent); border-color:var(--accent); }
  .modal__close svg{ width:14px; height:14px; }
  .modal__body{ padding:8px 22px 6px; display:grid; grid-template-columns:1fr 1fr; gap:0 32px; }
  .modal__sec{ padding:16px 0; border-bottom:1px solid var(--hair); }
  .modal__sec h3{ margin:0 0 8px; font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--grey-light); }
  .modal__sec .pop__list{ max-height:none; padding:0; }
  .modal__sec .pop__range{ padding:6px 0 0; }
  .modal__foot{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:16px 22px; border-top:1px solid var(--hair); position:sticky; bottom:0; background:var(--white); }
  .modal__count{ font-size:14px; color:var(--grey); } .modal__count strong{ color:var(--black); }

  .results__bar{ display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; margin:22px 0 18px; }
  .results__count{ margin:0; font-size:14px; color:var(--grey); }
  .results__count strong{ color:var(--black); font-weight:600; }
  .results__tools{ display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
  .sort{ display:flex; align-items:center; gap:10px; font-size:13px; color:var(--grey); }
  .sort .select{ width:auto; padding-top:7px; padding-bottom:7px; }
  /* cards / list toggle */
  .view{ display:inline-flex; border:1px solid var(--hair-strong); border-radius:var(--radius); overflow:hidden; }
  .view button{
    display:inline-flex; align-items:center; gap:7px;
    padding:7px 12px; font:inherit; font-size:13px; font-weight:600; color:var(--grey);
    background:var(--white); border:0; cursor:pointer;
  }
  .view button + button{ border-left:1px solid var(--hair-strong); }
  .view button svg{ width:14px; height:14px; }
  .view button[aria-pressed="true"]{ background:var(--accent-soft); color:var(--accent); }

  /* ---------- Cards ---------- */
  .grid{ display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:22px; }
  .card{
    display:flex; flex-direction:column;
    border:1px solid var(--hair-strong); border-radius:var(--radius);
    background:var(--white); color:inherit; text-decoration:none;
    transition:border-color .18s ease, box-shadow .18s ease, transform .18s ease;
  }
  .card:hover{ border-color:var(--accent); box-shadow:0 10px 28px rgba(0,0,0,.08); transform:translateY(-2px); }
  .card__media{ position:relative; aspect-ratio:4 / 3; background:#F3F4F6; border-radius:var(--radius) var(--radius) 0 0; overflow:hidden; }
  .card__rating{ position:absolute; right:12px; top:12px; z-index:2; }
  .card__rating .badge{ box-shadow:0 1px 4px rgba(0,0,0,.14); }
  .card__media img{ width:100%; height:100%; object-fit:cover; display:block; }
  .card__body{ padding:14px 16px 16px; display:flex; flex-direction:column; gap:8px; flex:1; }
  .card__row{ display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; }
  .status{
    display:inline-flex; align-items:center; gap:7px;
    font-size:11px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:var(--grey);
  }
  .status::before{ content:""; width:7px; height:7px; border-radius:50%; background:#10B981; flex:0 0 auto; }
  .status--limited::before{ background:#F59E0B; }
  .status--closing::before{ background:#EF4444; }
  .status--soon::before{ background:var(--accent); }
  .status--sold::before{ background:#9CA3AF; }
  .status--rejected::before{ background:#EF4444; }
  .card__rating .badge{ height:26px; font-size:11.5px; padding:0 9px 0 8px; gap:6px; }
  .card__rating .badge__emoji{ font-size:13px; }
  /* rating tooltip: Jerry's explanation from the homepage */
  .tip{ position:relative; display:inline-flex; }
  .tip__box{
    position:absolute; z-index:40; right:0; top:calc(100% + 8px); width:260px;
    padding:12px 14px; background:#111827; color:#F9FAFB; border-radius:6px;
    font-size:13px; font-weight:400; line-height:1.5; letter-spacing:0; white-space:normal; text-transform:none;
    box-shadow:0 10px 28px rgba(0,0,0,.25);
    opacity:0; visibility:hidden; transform:translateY(-4px);
    transition:opacity .15s ease, transform .15s ease, visibility 0s linear .15s;
    pointer-events:none;
  }
  .tip__box::before{ content:""; position:absolute; right:18px; top:-6px; border-left:6px solid transparent; border-right:6px solid transparent; border-bottom:6px solid #111827; }
  .tip__box strong{ display:block; margin-bottom:3px; color:#fff; }
  .tip__box small{ display:block; margin-top:6px; font-size:11px; color:#9CA3AF; }
  .tip:hover .tip__box, .tip:focus-within .tip__box{ opacity:1; visibility:visible; transform:none; transition-delay:0s; }
  .table .tip__box{ right:auto; left:0; } .table .tip__box::before{ right:auto; left:18px; }
  .card__type{ margin:0; font-size:11.5px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--grey-light); line-height:1.4; }
  .card__name{ margin:0 0 4px; font-size:17px; font-weight:700; line-height:1.25; letter-spacing:-.01em; color:var(--black); }
  .card__name a{ color:inherit; text-decoration:none; }
  .card__name a::after{ content:""; position:absolute; inset:0; }   /* whole card clickable, tooltip stays above */
  .card{ position:relative; }
  .card__media{ display:block; }
  .card__stats{ margin:auto 0 0; padding-top:4px; border-top:1px solid var(--hair); }
  .card__stats div{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; padding:7px 0; border-bottom:1px solid #F0F1F3; }
  .card__stats div:last-child{ border-bottom:0; }
  .card__stats dt{ margin:0; font-size:12.5px; color:var(--grey); }
  .card__stats dd{ margin:0; font-size:15px; font-weight:700; letter-spacing:-.01em; color:var(--black); font-variant-numeric:tabular-nums; text-align:right; }
  .card__stats dd.is-accent{ color:var(--accent); }
  .card__stats dd small{ font-size:11.5px; font-weight:500; color:var(--grey); margin-left:4px; }
  .card--sold{ opacity:.6; }
  .card--sold:hover{ transform:none; box-shadow:none; border-color:var(--hair-strong); }
  .empty{ grid-column:1 / -1; text-align:center; padding:64px 24px; border:1px dashed var(--hair-strong); border-radius:var(--radius); color:var(--grey); }
  .empty .hand{ display:block; font-family:var(--hand); font-size:30px; font-weight:600; color:var(--accent); margin-bottom:6px; transform:rotate(-2deg); }
  .inv__index{ margin:40px 0 0; font-size:12.5px; line-height:1.9; color:#6B7280; max-width:1100px; }
  .inv__index-label{ margin:0 0 4px; font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:#6B7280; }
  .inv__index a{ color:#4B5563; text-decoration:none; }
  .inv__index a:hover{ color:var(--accent); text-decoration:underline; }
  .inv__disclosure{ margin:24px 0 0; font-size:11px; line-height:1.55; color:#6B7280; max-width:900px; }

  /* ---------- List view (sortable table) ---------- */
  .tablewrap{ overflow-x:auto; border:1px solid var(--hair-strong); border-radius:var(--radius); }
  .table{ width:100%; border-collapse:collapse; font-size:14px; min-width:860px; }
  .table th, .table td{ padding:12px 14px; text-align:left; border-bottom:1px solid var(--hair); vertical-align:middle; }
  .table th{
    font-size:11px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--grey-light);
    background:#FAFBFC; white-space:nowrap; cursor:pointer; user-select:none;
  }
  .table th:hover{ color:var(--accent); }
  .table th[aria-sort] { color:var(--black); }
  .table th .arrow{
    display:inline-block; width:9px; height:9px; margin-left:6px; vertical-align:-1px;
    background-color:currentColor;
    -webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 10' fill='none'%3E%3Cpath d='M5 8.6V1.6M5 1.6 2.2 4.4M5 1.6l2.8 2.8' stroke='%23000' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
            mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 10' fill='none'%3E%3Cpath d='M5 8.6V1.6M5 1.6 2.2 4.4M5 1.6l2.8 2.8' stroke='%23000' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
    opacity:0; transform:scale(.72);
    transition:transform .3s cubic-bezier(.22,1,.36,1), opacity .18s ease;
  }
  .table th:hover .arrow{ opacity:.4; transform:scale(1); }
  .table th[aria-sort] .arrow{ opacity:1; transform:scale(1); color:var(--accent); }
  .table th[aria-sort="descending"] .arrow{ transform:rotate(180deg) scale(1); }
  .table tbody tr{ position:relative; will-change:transform; }
  .table tbody td{ transition:border-color .25s cubic-bezier(.23,1,.32,1); }
  .table.is-moving tbody td{ border-bottom-color:transparent; transition:border-color .12s cubic-bezier(.4,0,1,1); }
  .table.is-moving tbody tr:hover td{ background:transparent; }
  @media (prefers-reduced-motion:reduce){
    .table th .arrow, .table tbody tr, .table tbody td{ transition:none; }
  }
  .table tbody tr:last-child td{ border-bottom:0; }
  .table tbody tr:hover td{ background:#FAFBFC; }
  .table td.num{ text-align:right; font-variant-numeric:tabular-nums; font-weight:600; }
  .table th.num{ text-align:right; }
  .table td.num.is-accent{ color:var(--accent); font-weight:700; }
  .table__thumb{ width:56px; height:42px; object-fit:cover; border-radius:4px; display:block; }
  .table__name{ font-weight:700; color:var(--black); text-decoration:none; }
  .table__name:hover{ color:var(--accent); }
  .table__sub{ display:block; font-size:12px; color:var(--grey-light); font-weight:400; margin-top:2px; }
  .table tr.is-sold td{ opacity:.6; }
  .table .badge{ height:24px; font-size:11px; padding:0 8px 0 7px; gap:5px; }
  .table .badge__emoji{ font-size:12px; }
  [hidden]{ display:none !important; }

  /* ---------- Approved-investor gate: filters + headers stay, the offerings render as a blurred skeleton with the gate card over them ---------- */
  .lockwrap{ position:relative; }
  .gate{ display:none; position:absolute; left:50%; top:48px; transform:translateX(-50%); z-index:3; width:min(560px, calc(100% - 8px)); }
  html:not(.is-logged-in) .gate{ display:block; }
  .gate__card{ background:var(--white); border:1px solid var(--hair-strong); border-radius:10px; padding:32px 32px 28px; text-align:center; box-shadow:0 24px 48px -24px rgba(0,0,0,.28), 0 2px 6px rgba(0,0,0,.06); }
  .gate__card h2{ margin:0 0 10px; font-size:clamp(22px,2.4vw,28px); font-weight:700; line-height:1.15; letter-spacing:-.02em; }
  .gate__card p{ margin:0 0 20px; font-size:15px; line-height:1.6; color:var(--grey); }
  /* locked state: the grid is inert and softly blurred, fading out toward the bottom; controls stay visible but can't be used */
  html:not(.is-logged-in) .lockwrap > .grid{
    filter:blur(3px); pointer-events:none; user-select:none;
    -webkit-mask-image:linear-gradient(to bottom, #000 55%, transparent 100%); mask-image:linear-gradient(to bottom, #000 55%, transparent 100%);
  }
  html:not(.is-logged-in) .fbar, html:not(.is-logged-in) .results__bar{ pointer-events:none; }
  html:not(.is-logged-in) .results__bar select, html:not(.is-logged-in) .results__bar .view button{ opacity:.7; }
  /* skeleton cards: same footprint as a real card so unlocking causes no layout shift (skeleton recipe from transitions.dev) */
  :root{ --pulse-dur:1400ms; --pulse-min:.55; }
  .card--skel .card__media{ background:#EEF0F3; }
  .sk{ display:block; background:#E3E6EA; border-radius:4px; animation:t-skel-pulse var(--pulse-dur) ease-in-out infinite; }
  .card--skel .card__row{ min-height:20px; }
  .card--skel .card__stats div{ align-items:center; }
  .card--skel .card__stats dd .sk{ width:56px; height:23px; }
  .card--skel .card__stats dt .sk{ width:84px; height:12px; }
  @keyframes t-skel-pulse{ 0%,100%{ opacity:1; } 50%{ opacity:var(--pulse-min); } }
  @media (prefers-reduced-motion:reduce){ .sk{ animation:none; } }
  .gate__actions{ display:flex; gap:12px; justify-content:center; flex-wrap:wrap; }
  .gate__actions .btn--secondary{ background:var(--white); color:var(--black); border-color:var(--hair-strong); }
  .gate__actions .btn--secondary:hover{ background:#FAFBFC; border-color:var(--black); }
  .gate__note{ margin:20px 0 0 !important; font-size:13px !important; color:var(--grey-light) !important; }
  .is-logged-in .gate{ display:none; }

  /* ---------- Footer (from the homepage) ---------- */
''' + footcss + r'''
  /* ---------- Responsive ---------- */
  @media (max-width:1100px){ .grid{ grid-template-columns:repeat(3, minmax(0,1fr)); } }
  @media (max-width:900px){
''' + nav_mobile + r'''    .head{ padding:36px 20px 20px; }
    .inv{ padding:20px 20px 56px; }
    .modal__body{ grid-template-columns:1fr; }
    .grid{ grid-template-columns:1fr; gap:18px; }
    .footer__inner{ grid-template-columns:1fr 1fr; padding:40px 20px 32px; }
    .skyline{ padding-top:32px; }
    .footer__brand{ grid-column:1 / -1; }
    .footer__offices{ grid-column:1 / -1; display:grid; grid-template-columns:1fr 1fr; column-gap:24px; }
    .footer__offices .footer__label{ grid-column:1 / -1; }
  }
  @media (min-width:600px) and (max-width:900px){ .grid{ grid-template-columns:repeat(2, minmax(0,1fr)); } }

/* Headings in Sanomat (one weight); everything else stays in Guardian Sans */
h1:not(#_),h2:not(#_),h3:not(#_){font-family:var(--display);font-weight:400;letter-spacing:-.01em}
</style>
</head>
<body id="top">

''' + navhtml + r'''



<header class="head">
  <h1>Available Investments</h1>
  <p>Every offering here has been through my review process. Filter by what matters for your exchange — location, property type, the debt you need to replace, and current yield.</p>
</header>
<div class="rule" aria-hidden="true"></div>

<main class="inv">
  <div class="fbar" id="fbar" aria-label="Filters">
    <div class="fbar__chips" id="chips"></div>
    <button type="button" class="chip chip--more is-hidden" id="more" aria-haspopup="dialog"><span class="chip__val" id="more-label">More filters</span></button>
    <button type="button" class="chip chip--clear" id="clear" hidden><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6L6.00081 17.9992M17.9992 18L6 6.00085" stroke-linecap="round" stroke-linejoin="round"/></svg>Clear all</button>
  </div>

  <section aria-label="Investments">
    <div class="results__bar">
      <p class="results__count" id="count"></p>
      <div class="results__tools">
        <label class="sort">Sort by
          <select class="select" id="sort">
            <option value="name">Name — A to Z</option>
            <option value="rec">Featured</option>
            <option value="yield-desc">Current yield — high to low</option>
            <option value="ltv-asc">LTV — low to high</option>
            <option value="ltv-desc">LTV — high to low</option>
          </select>
        </label>
        <div class="view" role="group" aria-label="View">
          <button type="button" data-view="cards" aria-pressed="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3.88884 9.66294C4.39329 10 5.09552 10 6.49998 10C7.90445 10 8.60668 10 9.11113 9.66294C9.32951 9.51702 9.51701 9.32952 9.66292 9.11114C9.99998 8.60669 9.99998 7.90446 9.99998 6.5C9.99998 5.09554 9.99998 4.39331 9.66292 3.88886C9.51701 3.67048 9.32951 3.48298 9.11113 3.33706C8.60668 3 7.90445 3 6.49998 3C5.09552 3 4.39329 3 3.88884 3.33706C3.67046 3.48298 3.48296 3.67048 3.33705 3.88886C2.99998 4.39331 2.99998 5.09554 2.99998 6.5C2.99998 7.90446 2.99998 8.60669 3.33705 9.11114C3.48296 9.32952 3.67046 9.51702 3.88884 9.66294Z" stroke-linejoin="round"/><path d="M14.8888 9.66294C15.3933 10 16.0955 10 17.5 10C18.9044 10 19.6067 10 20.1111 9.66294C20.3295 9.51702 20.517 9.32952 20.6629 9.11114C21 8.60669 21 7.90446 21 6.5C21 5.09554 21 4.39331 20.6629 3.88886C20.517 3.67048 20.3295 3.48298 20.1111 3.33706C19.6067 3 18.9044 3 17.5 3C16.0955 3 15.3933 3 14.8888 3.33706C14.6705 3.48298 14.483 3.67048 14.337 3.88886C14 4.39331 14 5.09554 14 6.5C14 7.90446 14 8.60669 14.337 9.11114C14.483 9.32952 14.6705 9.51702 14.8888 9.66294Z" stroke-linejoin="round"/><path d="M3.88884 20.6629C4.39329 21 5.09552 21 6.49998 21C7.90445 21 8.60668 21 9.11113 20.6629C9.32951 20.517 9.51701 20.3295 9.66292 20.1111C9.99998 19.6067 9.99998 18.9045 9.99998 17.5C9.99998 16.0955 9.99998 15.3933 9.66292 14.8889C9.51701 14.6705 9.32951 14.483 9.11113 14.3371C8.60668 14 7.90445 14 6.49998 14C5.09552 14 4.39329 14 3.88884 14.3371C3.67046 14.483 3.48296 14.6705 3.33705 14.8889C2.99998 15.3933 2.99998 16.0955 2.99998 17.5C2.99998 18.9045 2.99998 19.6067 3.33705 20.1111C3.48296 20.3295 3.67046 20.517 3.88884 20.6629Z" stroke-linejoin="round"/><path d="M14.8888 20.6629C15.3933 21 16.0955 21 17.5 21C18.9044 21 19.6067 21 20.1111 20.6629C20.3295 20.517 20.517 20.3295 20.6629 20.1111C21 19.6067 21 18.9045 21 17.5C21 16.0955 21 15.3933 20.6629 14.8889C20.517 14.6705 20.3295 14.483 20.1111 14.3371C19.6067 14 18.9044 14 17.5 14C16.0955 14 15.3933 14 14.8888 14.3371C14.6705 14.483 14.483 14.6705 14.337 14.8889C14 15.3933 14 16.0955 14 17.5C14 18.9045 14 19.6067 14.337 20.1111C14.483 20.3295 14.6705 20.517 14.8888 20.6629Z" stroke-linejoin="round"/></svg>Cards</button>
          <button type="button" data-view="list" aria-pressed="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 11.4C2 10.2417 2.24173 10 3.4 10H20.6C21.7583 10 22 10.2417 22 11.4V12.6C22 13.7583 21.7583 14 20.6 14H3.4C2.24173 14 2 13.7583 2 12.6V11.4Z" stroke-linecap="round"/><path d="M2 3.4C2 2.24173 2.24173 2 3.4 2H20.6C21.7583 2 22 2.24173 22 3.4V4.6C22 5.75827 21.7583 6 20.6 6H3.4C2.24173 6 2 5.75827 2 4.6V3.4Z" stroke-linecap="round"/><path d="M2 19.4C2 18.2417 2.24173 18 3.4 18H20.6C21.7583 18 22 18.2417 22 19.4V20.6C22 21.7583 21.7583 22 20.6 22H3.4C2.24173 22 2 21.7583 2 20.6V19.4Z" stroke-linecap="round"/></svg>List</button>
        </div>
      </div>
    </div>
    <div class="lockwrap">
<section class="gate" id="gate" aria-labelledby="gate-heading">
  <div class="gate__card">
    <h2 id="gate-heading">These investments are for approved investors.</h2>
    <p>Log in with the email address on your account to see what’s currently available. New here? Registration takes a few minutes, and the last step is scheduling a call with me.</p>
    <div class="gate__actions">
      <a class="btn" href="/login/?next=/invest/">Log In</a>
      <a class="btn btn--secondary" href="/register/">Create an Account</a>
    </div>
    <p class="gate__note">Offerings are available solely to accredited investors and are made only by a sponsor’s private placement memorandum.</p>
  </div>
</section>
    <div class="grid" id="grid" aria-live="polite"></div>
    <div class="tablewrap" id="listwrap" hidden>
      <table class="table" id="table">
        <thead><tr>
          <th data-key="name">Investment<span class="arrow"></span></th>
          <th data-key="type">Property type<span class="arrow"></span></th>
          <th data-key="location">Location<span class="arrow"></span></th>
          <th data-key="status">Status<span class="arrow"></span></th>
          <th data-key="yld" class="num">Current yield<span class="arrow"></span></th>
          <th data-key="ltv" class="num">LTV<span class="arrow"></span></th>
          <th data-key="exit721">721 exit<span class="arrow"></span></th>
          <th data-key="rating">Rating<span class="arrow"></span></th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    </div><!-- /.lockwrap -->
    <div class="modal" id="modal" hidden role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div class="modal__panel">
        <div class="modal__head"><h2 id="modal-title">All filters</h2><button type="button" class="modal__close" id="modal-close" aria-label="Close"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ><path d="M18 6L6.00081 17.9992M17.9992 18L6 6.00085" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div>
        <div class="modal__body" id="modal-body"></div>
        <div class="modal__foot"><button type="button" class="pop__reset" id="modal-clear">Clear all</button><span class="modal__count" id="modal-count"></span><button type="button" class="pop__done" id="modal-done">Show results</button></div>
      </div>
    </div>
    <nav class="inv__index" aria-label="All offerings">
      <p class="inv__index-label">All offerings tracked on this page</p>
      ''' + ' · '.join('<a href="/offerings/%s/">%s</a>' % (o['slug'], html.escape(o['name'])) for o in sorted(OFFERINGS, key=lambda o: o['name'].lower())) + r'''
    </nav>
    <p class="inv__disclosure">Current yield is the projected first-year cash distribution rate stated in the sponsor’s offering documents and is not guaranteed. Loan-to-value (LTV) is based on the offering’s stated debt and purchase price. Ratings reflect Jerry Baker’s opinion after his review process and are not investment advice for any particular investor. Offerings are made only by a private placement memorandum to accredited investors; availability and terms are subject to change without notice.</p>
  </section>
</main>

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
  // ---- inventory data (placeholder set; in production this comes from the Airtable "Investment Data (Live)" build) ----
  var OFFERINGS = ''' + json.dumps(OFFERINGS) + r''';

  var RATING = {
    highly:      { cls:'badge--ok',   emoji:'👍👍', label:'Highly Approved' },
    approved:    { cls:'badge--ok',   emoji:'👍',  label:'Approved' },
    specialized: { cls:'badge--warn', emoji:'❗',  label:'Specialized' },
    rejected:    { cls:'badge--no',   emoji:'👎',  label:'Rejected' }
  };
  // Availability Status is a single-select in Airtable and Jerry can add a choice at any time, so every
  // lookup here falls back rather than throwing — an unstyled status must not blank out the whole list.
  var STATUS_CLS = { 'Available':'', 'Limited Availability':'card__status--limited', 'Pending Approval':'card__status--soon', 'Under Review':'card__status--soon', 'Closed':'card__status--sold', 'Rejected':'card__status--rejected' };
  function statusCls(s){ return STATUS_CLS[s] || ''; }
  var OPEN = ['Available','Limited Availability'];
  var MUTED = ['Closed','Rejected'];

  var grid = document.getElementById('grid'), count = document.getElementById('count'), tbody = document.getElementById('tbody');
  var sort = document.getElementById('sort');
  var view = 'cards', tableSort = { key:null, dir:1 };

  var EXIT = { mandatory:'Mandatory', optional:'Optional', none:'None' };
  var RATING_TEXT = {
    highly:      'The investment passes our review, and I particularly like the sponsor, business plan, underwriting, and terms. I’ll explain what earned it that second thumb.',
    approved:    'The investment passes our review, but I have more reservations. We’ll discuss those concerns and whether the tradeoffs make sense for you.',
    specialized: 'This investment is specialized. It may have a place in certain situations, but we need a specific reason to use it.',
    rejected:    'The investment didn’t meet our standards. I passed.'
  };
  var order = { highly:0, approved:1, specialized:2, rejected:3 };
  var STATUS_ORDER = ['Available','Limited Availability','Under Review','Pending Approval','Closed','Rejected'];
  // Any status in the data that STATUS_ORDER does not know about is appended, so it still sorts and still
  // appears as a filter option instead of silently hiding the offerings that carry it.
  OFFERINGS.forEach(function(o){ if(o.status && STATUS_ORDER.indexOf(o.status) === -1) STATUS_ORDER.push(o.status); });

  // ---- filter definitions (multi-selects and ranges) ----
  function countBy(fn){ var m = {}; OFFERINGS.forEach(function(o){ var k = fn(o); (Array.isArray(k) ? k : [k]).forEach(function(x){ m[x] = (m[x] || 0) + 1; }); }); return m; }
  var stateCounts = countBy(function(o){ return o.locations; }), typeCounts = countBy(function(o){ return o.types; }), statusCounts = countBy(function(o){ return o.status; }), exitCounts = countBy(function(o){ return o.exit721; });
  var FILTERS = [
    { key:'location', label:'Location', kind:'multi', options: Object.keys(stateCounts).sort(function(a,b){ return a.localeCompare(b); }).map(function(k){ return { value:k, label:k, count:stateCounts[k] }; }) },
    { key:'type', label:'Property type', kind:'multi', options: Object.keys(typeCounts).sort().map(function(k){ return { value:k, label:k, count:typeCounts[k] }; }) },
    { key:'status', label:'Status', kind:'multi', options: STATUS_ORDER.filter(function(k){ return statusCounts[k]; }).map(function(k){ return { value:k, label:k, count:statusCounts[k] }; }) },
    { key:'ltv', label:'Min LTV', kind:'range', min:0, max:60, step:5, fmt:function(v){ return v + '%'; } },
    { key:'yld', label:'Min current yield', kind:'range', min:0, max:7.5, step:0.25, fmt:function(v){ return v.toFixed(2) + '%'; } },
    { key:'exit721', label:'721 exit', kind:'multi', options: ['mandatory','optional','none'].map(function(k){ return { value:k, label:EXIT[k], count:exitCounts[k] || 0 }; }) }
  ];
  var F = { location:[], type:[], status:[], exit721:[], ltv:0, yld:0, allCash:false };
  function isSet(def){ if(def.key === 'ltv' && F.allCash) return true; return def.kind === 'multi' ? F[def.key].length > 0 : F[def.key] > 0; }
  function anySet(){ return FILTERS.some(isSet); }
  function chipText(def){
    if(!isSet(def)) return def.label;
    if(def.key === 'ltv' && F.allCash) return 'LTV · All-cash only';
    if(def.kind === 'range') return def.label + ' · ' + def.fmt(F[def.key]) + '+';
    var v = F[def.key], labels = def.options.filter(function(o){ return v.indexOf(o.value) > -1; }).map(function(o){ return o.label; });
    return def.label + ' · ' + (labels.length <= 2 ? labels.join(', ') : labels.length + ' selected');
  }

  // ---- shared control renderers (used by chip popovers and the modal) ----
  function checkHtml(def, o){
    var on = F[def.key].indexOf(o.value) > -1;
    return '<label class="check"><input type="checkbox" data-f="' + def.key + '" value="' + esc(o.value) + '"' + (on ? ' checked' : '') + '><span class="check__box" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round" ><path d="M5 14L8.5 17.5L19 6.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span class="check__text">' + esc(o.label) + '</span><span class="check__count">' + o.count + '</span></label>';
  }
  function controlHtml(def){
    if(def.kind === 'multi') return '<div class="pop__list">' + def.options.map(function(o){ return checkHtml(def, o); }).join('') + '</div>';
    var v = F[def.key], cash = def.key === 'ltv' && F.allCash;
    return '<div class="pop__range' + (cash ? ' is-off' : '') + '"><div class="pop__rangehead"><span>' + (v ? 'At least' : 'Any') + '</span><output>' + (v ? def.fmt(v) : '—') + '</output></div>' +
      '<input type="range" data-f="' + def.key + '" min="' + def.min + '" max="' + def.max + '" step="' + def.step + '" value="' + v + '"' + (cash ? ' disabled' : '') + '>' +
      '<div class="range__scale"><span>' + def.fmt(def.min) + '</span><span>' + def.fmt(def.max) + '</span></div></div>' +
      (def.key === 'ltv' ? '<div class="pop__alt"><button type="button" class="altbtn' + (cash ? ' is-on' : '') + '" data-allcash aria-pressed="' + (cash ? 'true' : 'false') + '"><span class="altbtn__box" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.75" stroke-linecap="round" stroke-linejoin="round" ><path d="M5 14L8.5 17.5L19 6.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>All-cash only <small>0% LTV</small></button></div>' : '');
  }

  // ---- chips ----
  var chips = document.getElementById('chips'), more = document.getElementById('more'), clearBtn = document.getElementById('clear');
  FILTERS.forEach(function(def){
    var w = document.createElement('div'); w.className = 'chipwrap'; w.dataset.key = def.key;
    w.innerHTML = '<button type="button" class="chip" aria-expanded="false" aria-haspopup="true"><span class="chip__val"></span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke-linecap="round" stroke-linejoin="round"/></svg></button><div class="pop" hidden></div>';
    chips.appendChild(w);
  });
  function renderChips(){
    FILTERS.forEach(function(def){
      var w = chips.querySelector('[data-key="' + def.key + '"]'), btn = w.querySelector('.chip');
      btn.querySelector('.chip__val').textContent = chipText(def);
      btn.classList.toggle('is-set', isSet(def));
    });
    clearBtn.hidden = !anySet();
    fitChips();
  }
  var openKey = null;
  function openPop(key){
    closePops();
    var w = chips.querySelector('[data-key="' + key + '"]'), def = FILTERS.filter(function(d){ return d.key === key; })[0];
    var pop = w.querySelector('.pop');
    pop.innerHTML = controlHtml(def) + '<div class="pop__foot"><button type="button" class="pop__reset" data-reset="' + key + '">Reset</button><button type="button" class="pop__done">Done</button></div>';
    pop.hidden = false; w.querySelector('.chip').setAttribute('aria-expanded','true'); openKey = key;
    // keep the panel on screen
    var r = pop.getBoundingClientRect(); if(r.right > window.innerWidth - 12){ pop.style.left = 'auto'; pop.style.right = '0'; }
  }
  function closePops(){
    Array.prototype.forEach.call(chips.querySelectorAll('.pop'), function(p){ p.hidden = true; p.style.left = ''; p.style.right = ''; });
    Array.prototype.forEach.call(chips.querySelectorAll('.chip'), function(c){ c.setAttribute('aria-expanded','false'); });
    openKey = null;
  }
  chips.addEventListener('click', function(e){
    var btn = e.target.closest('.chip');
    if(btn){ var key = btn.closest('.chipwrap').dataset.key; if(openKey === key) closePops(); else openPop(key); return; }
    if(e.target.closest('.pop__done')){ closePops(); return; }
    var ac = e.target.closest('[data-allcash]');
    if(ac){ F.allCash = !F.allCash; if(F.allCash) F.ltv = 0; apply(); openPop('ltv'); return; }
    var reset = e.target.closest('[data-reset]');
    if(reset){ var def = FILTERS.filter(function(d){ return d.key === reset.dataset.reset; })[0]; F[def.key] = def.kind === 'multi' ? [] : 0; if(def.key === 'ltv') F.allCash = false; apply(); openPop(def.key); }
  });
  document.addEventListener('click', function(e){ if(e.target.isConnected && !e.target.closest('.chipwrap')) closePops(); });
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape'){ closePops(); closeModal(); } });

  // any control change (chip popover or modal) updates the state
  document.addEventListener('input', function(e){
    var el = e.target; if(!el.dataset || !el.dataset.f) return;
    var def = FILTERS.filter(function(d){ return d.key === el.dataset.f; })[0];
    if(def.kind === 'multi'){
      var arr = F[def.key].slice(); var i = arr.indexOf(el.value);
      if(el.checked && i === -1) arr.push(el.value); if(!el.checked && i > -1) arr.splice(i, 1);
      F[def.key] = arr;
    } else {
      F[def.key] = +el.value;
      if(def.key === 'ltv' && F.ltv > 0) F.allCash = false;
      var head = el.parentElement.querySelector('.pop__rangehead');
      if(head){ head.querySelector('span').textContent = F[def.key] ? 'At least' : 'Any'; head.querySelector('output').textContent = F[def.key] ? def.fmt(F[def.key]) : '—'; }
    }
    apply();
  });

  // ---- overflow: collapse chips that don't fit into "More filters" ----
  function fitChips(){
    var wraps = Array.prototype.slice.call(chips.querySelectorAll('.chipwrap'));
    wraps.forEach(function(w){ w.classList.remove('is-hidden'); });
    more.classList.add('is-hidden');
    var avail = chips.clientWidth;
    var used = 0, hiddenCount = 0, gap = 10;
    // reserve room for the "More" chip if anything will overflow
    var total = wraps.reduce(function(t, w){ return t + w.offsetWidth + gap; }, 0) - gap;
    var needMore = total > avail;
    var reserve = needMore ? 150 : 0;
    wraps.forEach(function(w, i){
      var wdt = w.offsetWidth + (i ? gap : 0);
      if(used + wdt > avail - reserve){ w.classList.add('is-hidden'); hiddenCount++; }
      else used += wdt;
    });
    if(hiddenCount){
      more.classList.remove('is-hidden');
      var hiddenSet = wraps.filter(function(w){ return w.classList.contains('is-hidden'); }).filter(function(w){ return isSet(FILTERS.filter(function(d){ return d.key === w.dataset.key; })[0]); }).length;
      document.getElementById('more-label').textContent = '+' + hiddenCount + ' more filter' + (hiddenCount === 1 ? '' : 's') + (hiddenSet ? ' · ' + hiddenSet + ' set' : '');
      more.classList.toggle('is-set', hiddenSet > 0);
    }
  }
  if(window.ResizeObserver){ new ResizeObserver(function(){ fitChips(); if(openKey && chips.querySelector('[data-key="' + openKey + '"]').classList.contains('is-hidden')) closePops(); }).observe(chips); } else { window.addEventListener('resize', fitChips); }

  // ---- modal with every filter ----
  var modal = document.getElementById('modal'), modalBody = document.getElementById('modal-body');
  function openModal(){
    closePops();
    modalBody.innerHTML = FILTERS.map(function(def){ return '<section class="modal__sec"><h3>' + esc(def.label) + '</h3>' + controlHtml(def) + '</section>'; }).join('');
    modal.hidden = false; document.body.style.overflow = 'hidden';
    document.getElementById('modal-close').focus();
  }
  function closeModal(){ if(modal.hidden) return; modal.hidden = true; document.body.style.overflow = ''; more.focus(); }
  more.addEventListener('click', openModal);
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-done').addEventListener('click', closeModal);
  modal.addEventListener('click', function(e){
    if(e.target === modal){ closeModal(); return; }
    var ac = e.target.closest('[data-allcash]');
    if(ac){ F.allCash = !F.allCash; if(F.allCash) F.ltv = 0; apply(); openModal(); }
  });
  document.getElementById('modal-clear').addEventListener('click', function(){ clearAll(); openModal(); });
  function clearAll(){ FILTERS.forEach(function(def){ F[def.key] = def.kind === 'multi' ? [] : 0; }); F.allCash = false; apply(); }
  clearBtn.addEventListener('click', clearAll);

  // ---- rendering ----
  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function loc(o){ return o.locLabel; }
  function fmtYield(o){ return o.yld === null ? (o.zeroCoupon ? '<span title="This offering projects no operating distributions">No current income</span>' : '—') : o.yld.toFixed(2) + '%'; }
  function badge(o){
    var r = RATING[o.rating]; if(!r) return '';
    return '<span class="tip" tabindex="0"><span class="badge ' + r.cls + '"><span class="badge__emoji" aria-hidden="true">' + r.emoji + '</span>' + r.label + '</span>' +
      '<span class="tip__box" role="tooltip"><strong>' + r.emoji + ' ' + r.label + '</strong>' + esc(RATING_TEXT[o.rating]) + '<small>My assessment, not a guarantee of performance or the return of your principal.</small></span></span>';
  }
  var STATUS_SHORT = { 'Limited Availability':'Limited', 'Pending Approval':'Pending', 'Under Review':'Review' };
  function statusPill(o){ return '<span class="status ' + statusCls(o.status).replace('card__status','status') + '" title="' + esc(o.status) + '">' + esc(STATUS_SHORT[o.status] || o.status) + '</span>'; }
  function card(o){
    var sold = MUTED.indexOf(o.status) > -1;
    return '<div class="card' + (sold ? ' card--sold' : '') + '">' +
      '<a class="card__media" href="/offerings/' + o.slug + '/" aria-label="' + esc(o.name) + '"><img src="' + o.img + '" alt="" loading="lazy"></a>' +
      '<span class="card__rating">' + badge(o) + '</span>' +
      '<div class="card__body">' +
        '<div class="card__row">' + statusPill(o) + '</div>' +
        '<p class="card__type">' + esc(o.typeLabel) + ' · ' + esc(loc(o)) + '</p>' +
        '<h3 class="card__name"><a href="/offerings/' + o.slug + '/">' + esc(o.name) + '</a></h3>' +
        '<dl class="card__stats">' +
          '<div><dt>Current yield</dt><dd class="is-accent">' + fmtYield(o) + '</dd></div>' +
          '<div><dt>LTV</dt><dd>' + (o.ltv ? o.ltv + '%' : '0%<small>all-cash</small>') + '</dd></div>' +
          '<div><dt>721 exchange exit</dt><dd>' + (o.exit721 === 'none' ? '<span style="color:var(--grey);font-weight:600">None</span>' : EXIT[o.exit721]) + '</dd></div>' +
        '</dl>' +
      '</div>' +
    '</div>';
  }
  // Rows travel to their new order (FLIP: measure, re-render, invert, play). Only rows near the viewport animate.
  var REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function flipRows(tbody, render){
    if(REDUCED){ render(); return; }
    var before = {};
    Array.prototype.forEach.call(tbody.children, function(tr){ if(tr.dataset.id) before[tr.dataset.id] = tr.getBoundingClientRect().top; });
    render();
    var table = tbody.parentNode, vh = window.innerHeight, movers = [], order = 0;
    Array.prototype.forEach.call(tbody.children, function(tr){
      var id = tr.dataset.id; if(!id || before[id] === undefined) return;
      var now = tr.getBoundingClientRect().top, dy = before[id] - now;
      if(Math.abs(dy) < 1) return;
      if(!((before[id] > -300 && before[id] < vh + 300) || (now > -300 && now < vh + 300))) return;
      tr.style.transition = 'none';
      tr.style.transform = 'translateY(' + dy + 'px)';
      movers.push({ tr:tr, delay: Math.min(order++, 8) * 18 });
    });
    if(!movers.length) return;
    table.classList.add('is-moving');
    void tbody.offsetHeight;   // commit the inverted positions before playing
    movers.forEach(function(m){
      m.tr.style.transition = 'transform .42s cubic-bezier(.22,1,.36,1) ' + m.delay + 'ms';
      m.tr.style.transform = '';
    });
    clearTimeout(flipRows._t);
    flipRows._t = setTimeout(function(){
      table.classList.remove('is-moving');
      movers.forEach(function(m){ m.tr.style.transition = ''; m.tr.style.transform = ''; });
    }, 380 + 8 * 18);
  }
  function row(o){
    return '<tr data-id="' + o.slug + '"' + (MUTED.indexOf(o.status) > -1 ? ' class="is-sold"' : '') + '>' +
      '<td><div style="display:flex;align-items:center;gap:12px"><img class="table__thumb" src="' + o.img + '" alt="" loading="lazy"><div><a class="table__name" href="/offerings/' + o.slug + '/">' + esc(o.name) + '</a></div></div></td>' +
      '<td>' + esc(o.typeLabel) + '</td>' +
      '<td>' + esc(loc(o)) + '</td>' +
      '<td>' + statusPill(o) + '</td>' +
      '<td class="num is-accent">' + fmtYield(o) + '</td>' +
      '<td class="num">' + o.ltv + '%</td>' +
      '<td>' + EXIT[o.exit721] + '</td>' +
      '<td>' + badge(o) + '</td>' +
    '</tr>';
  }
  function cmp(key, dir){
    return function(a, b){
      var va, vb;
      if(key === 'location'){ va = loc(a); vb = loc(b); }
      else if(key === 'rating'){ va = order[a.rating]; vb = order[b.rating]; }
      else if(key === 'exit721'){ var EO = { mandatory:0, optional:1, none:2 }; va = EO[a.exit721]; vb = EO[b.exit721]; }
      else if(key === 'status'){ va = STATUS_ORDER.indexOf(a.status); vb = STATUS_ORDER.indexOf(b.status); }
      else if(key === 'type'){ va = a.typeLabel; vb = b.typeLabel; }
      else { va = a[key]; vb = b[key]; }
      if(va === null || vb === null){ if(va === vb) return 0; return va === null ? 1 : -1; }   // no-yield rows sink
      if(typeof va === 'string') return va.localeCompare(vb) * dir;
      return (va - vb) * dir;
    };
  }
  function filtered(){
    return OFFERINGS.filter(function(o){
      if(F.location.length && !o.locations.some(function(s){ return F.location.indexOf(s) > -1; })) return false;
      if(F.type.length && !o.types.some(function(t){ return F.type.indexOf(t) > -1; })) return false;
      if(F.status.length && F.status.indexOf(o.status) === -1) return false;
      if(F.exit721.length && F.exit721.indexOf(o.exit721) === -1) return false;
      if(F.allCash ? o.ltv !== 0 : o.ltv < F.ltv) return false;
      if(F.yld > 0 && (o.yld === null || o.yld < F.yld)) return false;
      return true;
    });
  }
  var LOCKED = !document.documentElement.classList.contains('is-logged-in');
  function skeletonCard(){
    return '<div class="card card--skel" aria-hidden="true"><div class="card__media"></div><div class="card__body">' +
      '<div class="card__row" style="min-height:17px"><span class="sk" style="width:76px;height:12px"></span></div>' +
      '<span class="sk" style="width:62%;height:12px;margin:2px 0"></span>' +
      '<span class="sk" style="width:88%;height:17px;margin-top:2px"></span><span class="sk" style="width:48%;height:17px;margin-bottom:4px"></span>' +
      '<dl class="card__stats">' + '<div><dt><span class="sk"></span></dt><dd><span class="sk"></span></dd></div>'.repeat(3) + '</dl>' +
    '</div></div>';
  }
  function applyLocked(){
    var n = Math.min(OFFERINGS.length, 8);
    grid.innerHTML = skeletonCard().repeat(n);
    grid.hidden = false; document.getElementById('listwrap').hidden = true;
    count.innerHTML = '<strong>' + OFFERINGS.length + '</strong> investment' + (OFFERINGS.length === 1 ? '' : 's');
    sort.disabled = true;
    Array.prototype.forEach.call(document.querySelectorAll('.view button, .fbar .chip'), function(b){ b.setAttribute('aria-disabled', 'true'); b.tabIndex = -1; });
    renderChips();
  }
  function apply(){
    if(LOCKED){ applyLocked(); return; }
    var list = filtered();
    if(view === 'list' && tableSort.key){
      list.sort(cmp(tableSort.key, tableSort.dir));
    } else {
      var sv = sort.value;
      list.sort(function(a,b){
        if(sv === 'yield-desc') return (b.yld === null ? -1 : b.yld) - (a.yld === null ? -1 : a.yld);
        if(sv === 'ltv-asc') return a.ltv - b.ltv;
        if(sv === 'ltv-desc') return b.ltv - a.ltv;
        if(sv === 'name') return a.name.localeCompare(b.name);
        var ao = OPEN.indexOf(a.status) > -1 ? 0 : 1, bo = OPEN.indexOf(b.status) > -1 ? 0 : 1;
        return ao - bo || order[a.rating] - order[b.rating] || (b.yld === null ? -1 : b.yld) - (a.yld === null ? -1 : a.yld);   // recommended
      });
    }
    var empty = '<div class="empty"><span class="hand">Nothing matches — yet.</span>Try loosening a filter or two. If you don’t see what you’re looking for, <a href="mailto:jerry@baker1031.com">let me know</a> and I’ll keep an eye out for the right fit.</div>';
    grid.innerHTML = list.length ? list.map(card).join('') : empty;
    flipRows(tbody, function(){ tbody.innerHTML = list.map(row).join(''); });
    document.getElementById('listwrap').hidden = view !== 'list' || !list.length;
    grid.hidden = view === 'list' && list.length > 0;
    count.innerHTML = '<strong>' + list.length + '</strong> of ' + OFFERINGS.length + ' investment' + (OFFERINGS.length === 1 ? '' : 's');
    var mc = document.getElementById('modal-count'); if(mc) mc.innerHTML = '<strong>' + list.length + '</strong> match' + (list.length === 1 ? '' : 'es');
    Array.prototype.forEach.call(document.querySelectorAll('.table th'), function(th){
      if(view === 'list' && th.dataset.key === tableSort.key) th.setAttribute('aria-sort', tableSort.dir === 1 ? 'ascending' : 'descending'); else th.removeAttribute('aria-sort');
    });
    renderChips();
    try { localStorage.setItem('b1031-inv', JSON.stringify({ F:F, sort:sort.value, view:view, tableSort:tableSort })); } catch(e){}
  }
  sort.addEventListener('change', function(){ tableSort = { key:null, dir:1 }; apply(); });
  Array.prototype.forEach.call(document.querySelectorAll('.view button'), function(b){
    b.addEventListener('click', function(){
      view = b.dataset.view;
      Array.prototype.forEach.call(document.querySelectorAll('.view button'), function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      apply();
    });
  });
  document.querySelector('.table thead').addEventListener('click', function(e){
    var th = e.target.closest('th'); if(!th) return;
    var key = th.dataset.key;
    tableSort = tableSort.key === key ? { key:key, dir:-tableSort.dir } : { key:key, dir:(key === 'yld' || key === 'ltv') ? -1 : 1 };
    apply();
  });
  // restore this visitor's last filters / view
  try {
    var saved = JSON.parse(localStorage.getItem('b1031-inv') || 'null');
    if(saved && saved.F){
      FILTERS.forEach(function(def){ if(saved.F[def.key] !== undefined) F[def.key] = saved.F[def.key]; }); F.allCash = !!saved.F.allCash;
      sort.value = saved.sort || 'name';
      view = saved.view === 'list' ? 'list' : 'cards'; tableSort = saved.tableSort || { key:null, dir:1 };
      Array.prototype.forEach.call(document.querySelectorAll('.view button'), function(x){ x.setAttribute('aria-pressed', x.dataset.view === view ? 'true' : 'false'); });
    }
  } catch(e){}
  apply();
})();
</script>

</body>
</html>
'''
open(os.path.join(HERE, 'inventory_template.html'), 'w', encoding='utf-8').write(page)
out = page.replace('{{LOGO}}', a['logo']).replace('{{SKYLINE}}', a['skyline'])
if ROOT:
    os.makedirs(os.path.join(ROOT, 'invest'), exist_ok=True)
    open(os.path.join(ROOT, 'invest', 'index.html'), 'w', encoding='utf-8').write(out)
else:
    open('/home/claude/inventory.html', 'w', encoding='utf-8').write(out)
print('built', len(out))

import re, json
h = open('/home/claude/hero-jerry.html').read()
a = json.load(open('assets.json'))
import csv

def between(start, end, src=h):
    i = src.index(start); j = src.index(end, i); return src[i:j]

navcss = between('  /* ---------- Sticky nav ---------- */', '  /* section anchors land below the sticky bar */')
nav_mobile = between('    .nav__inner{ gap:16px; height:54px; }', '    .ctabar__inner{')
footcss = between('  /* ---------- Footer ---------- */', '  /* ---------- Sticky nav ---------- */')
navhtml = re.search(r'<header class="nav" id="nav">.*?</header>', h, flags=re.S).group(0)
navhtml = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', navhtml)
navhtml = navhtml.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"').replace('<a href="/results/">', '<a href="/results/" aria-current="page">')
foot = re.search(r'<footer class="footer">.*?</footer>', h, flags=re.S).group(0)
foot = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', foot)
foot = foot.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"')
navjs = between("  // Nav: shadow once scrolled; mobile menu toggle", "})();\n</script>")

# Full-cycle dataset — one master file shared with the sponsor track records (build/fullcycle.py)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fullcycle as fc
data = [{k: d[k] for k in ('name', 'sponsor', 'type', 'state', 'ret', 'em', 'hold', 'id')} for d in fc.load()]
print('deals', len(data))

page = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Full-Cycle Results — Baker 1031 Investments</title>
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

  :root{ --page:#DFDAD2; --accent-2:#6B2E3E; --rose:#8A5B66;
    --black:#000; --white:#fff;
    --accent:#4C0018; --accent-hover:#33000F; --accent-soft:#F2EDE7;
    --grey:#4A4444; --grey-light:#645D5B; --hair:#DED8D1; --hair-strong:#C6BEB6;
    --radius:6px;
    --font:"Guardian Sans", "Helvetica Neue", Helvetica, Arial, sans-serif;
    --display:"Sanomat", Georgia, "Times New Roman", serif;
    --hand:"Caveat", "Segoe Print", "Bradley Hand", cursive;
  }
  *{ box-sizing:border-box; }
  html{ -webkit-text-size-adjust:100%; }
  body{ margin:0; background:var(--page); color:var(--black); font-family:var(--font); line-height:1.5; -webkit-font-smoothing:antialiased; }
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

  /* ---------- Sticky nav (from the homepage) ---------- */
''' + navcss + r'''  .nav__links a[aria-current="page"] .nav__word{ color:var(--black); }

  /* ---------- Page head ---------- */
  .head{ max-width:calc(1200px + 48px); margin:0 auto; padding:56px 24px 28px; }
  .head h1{ margin:0 0 12px; font-size:clamp(30px,3vw,40px); font-weight:700; line-height:1.1; letter-spacing:-.02em; }
  .head p{ margin:0; max-width:760px; font-size:16px; line-height:1.65; color:var(--grey); }
  .rule{ max-width:calc(1200px + 48px); margin:0 auto; padding:0 24px; }
  .rule::before{ content:""; display:block; height:1px; background:#DED8D1; }
  .rule--strong::before{ height:2px; background:#C6BEB6; }

  /* ---------- Results table ---------- */
  .wrap{ max-width:calc(1200px + 48px); margin:0 auto; padding:28px 24px 72px; }
  .sec{ padding:8px 0 40px; }
  .sec + .sec{ padding-top:40px; border-top:1px solid var(--hair); }
  .bar{ display:flex; align-items:baseline; justify-content:space-between; gap:16px; flex-wrap:wrap; margin-bottom:16px; }
  .bar h2{ margin:0; font-size:22px; font-weight:700; letter-spacing:-.015em; line-height:1.2; }
  .bar__count{ margin-left:10px; font-size:14px; font-weight:400; color:var(--grey); letter-spacing:0; }
  .bar__count strong{ color:var(--black); font-weight:600; }
  .star{ color:#8A5B66; font-size:15px; margin-left:6px; vertical-align:-1px; }
  .legend{ margin:12px 0 0; font-size:12.5px; line-height:1.55; color:var(--grey-light); max-width:820px; }
  .legend .star{ margin:0 4px 0 0; }
  .bar__hint{ margin:0; font-size:13px; color:var(--grey-light); }
  .tools{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin:0 0 14px; }
  .tools input, .tools select{
    font:inherit; font-size:14px; color:var(--black); background:var(--white);
    border:1px solid var(--hair-strong); border-radius:var(--radius); padding:9px 12px; height:40px;
  }
  .tools input{ flex:1 1 260px; min-width:200px; }
  .tools input::placeholder{ color:#6E6765; }
  .tools select{ flex:0 1 auto; max-width:100%; padding-right:32px; -webkit-appearance:none; appearance:none;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' fill='none' stroke='%234B5563' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat:no-repeat; background-position:right 12px center; }
  .tools input:focus, .tools select:focus{ outline:none; border-color:var(--accent); box-shadow:0 0 0 3px rgba(76,0,24,.18); }
  .tools__clear{ font:inherit; font-size:13.5px; font-weight:600; color:var(--accent); background:none; border:0; padding:8px 4px; cursor:pointer; }
  .tools__clear:hover{ color:var(--accent-hover); text-decoration:underline; }
  .tools__clear[hidden]{ display:none; }
  .table td.na{ color:#6E6765; font-weight:400; }
  .empty{ padding:36px 16px; text-align:center; color:var(--grey); font-size:14.5px; }
  .tablewrap{ overflow-x:auto; border:1px solid var(--hair-strong); border-radius:var(--radius); }
  .table{ width:100%; border-collapse:collapse; font-size:14.5px; min-width:820px; }
  .table th, .table td{ padding:13px 16px; text-align:left; border-bottom:1px solid var(--hair); vertical-align:middle; }
  .table th{
    font-size:11px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--grey-light);
    background:#FAF8F5; white-space:nowrap; cursor:pointer; user-select:none;
  }
  .table th:hover{ color:var(--accent); }
  .table th[aria-sort]{ color:var(--black); }
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
  .table tbody tr:hover td{ background:#FAF8F5; }
  .table td.name{ font-weight:700; color:var(--black); }
  .table td.name small{ display:block; font-size:12px; font-weight:400; color:var(--grey-light); margin-top:2px; }
  .table td.num, .table th.num{ text-align:left; font-variant-numeric:tabular-nums; }
  .table td.num{ font-weight:600; }
  .table td.num.is-accent{ color:var(--accent); font-weight:700; }
  .table tfoot td{ padding:13px 16px; background:#FAF8F5; border-top:1px solid var(--hair); font-size:13.5px; color:var(--grey); }
  .table tfoot tr:first-child td{ border-top:2px solid var(--hair-strong); }
  .table tfoot td.num{ font-weight:700; color:var(--black); }
  .table tfoot td.name{ font-weight:600; color:var(--black); }
  .disclosure{ margin:28px 0 0; font-size:11px; line-height:1.55; color:#645D5B; max-width:900px; }

  /* ---------- Footer (from the homepage) ---------- */
''' + footcss + r'''
  @media (max-width:900px){
''' + nav_mobile + r'''    .head{ padding:36px 20px 20px; }
    .wrap{ padding:20px 20px 56px; }
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
<body id="top">

''' + navhtml + r'''

<header class="head">
  <h1>Results</h1>
  <p>Every investment here went full-cycle — bought, operated, and sold — and these are the results the sponsors reported to investors. Click any column heading to sort, or search the full list by name, sponsor, property type, or state.</p>
</header>
<div class="rule" aria-hidden="true"></div>

<main class="wrap">
  <section class="sec" id="sponsors">
    <div class="bar">
      <h2>Sponsor Performance</h2>
      <p class="bar__hint" id="sorted-sp"></p>
    </div>
    <div class="tablewrap">
      <table class="table" id="sptable">
        <thead><tr>
          <th data-key="sponsor" aria-sort="ascending">Sponsor<span class="arrow"></span></th>
          <th data-key="n" class="num">Full-cycle deals<span class="arrow"></span></th>
          <th data-key="ret" class="num">Avg. annual return<span class="arrow"></span></th>
          <th data-key="em" class="num">Avg. equity multiple<span class="arrow"></span></th>
          <th data-key="hold" class="num">Avg. hold period<span class="arrow"></span></th>
          <th data-key="success" class="num">Success rate<span class="arrow"></span></th>
        </tr></thead>
        <tbody id="sptbody"></tbody>
        <tfoot id="spfoot"></tfoot>
      </table>
    </div>
    <p class="legend"><span class="star" aria-hidden="true">★</span> Preferred sponsor — a firm I’ve worked with repeatedly and whose full-cycle track record I follow closely. Success rate is the share of a sponsor’s full-cycle deals that returned investors’ capital or better (equity multiple of 1.0x or higher). Where a sponsor didn’t report a figure it’s shown as “—” and left out of that average.</p>
  </section>

  <section class="sec" id="assets">
    <div class="bar">
      <h2>Performance by Asset Class</h2>
      <p class="bar__hint" id="sorted-ac"></p>
    </div>
    <div class="tablewrap">
      <table class="table" id="actable">
        <thead><tr>
          <th data-key="type" aria-sort="ascending">Asset class<span class="arrow"></span></th>
          <th data-key="n" class="num">Deals<span class="arrow"></span></th>
          <th data-key="ret" class="num">Avg. annual return<span class="arrow"></span></th>
          <th data-key="em" class="num">Avg. equity multiple<span class="arrow"></span></th>
          <th data-key="hold" class="num">Avg. hold period<span class="arrow"></span></th>
          <th data-key="success" class="num">Success rate<span class="arrow"></span></th>
        </tr></thead>
        <tbody id="actbody"></tbody>
      </table>
    </div>
  </section>

  <section class="sec" id="fullcycle">
  <div class="bar">
    <h2>Full-Cycle Results <span class="bar__count"><strong id="count">0</strong> investments</span></h2>
    <p class="bar__hint" id="sorted"></p>
  </div>
  <div class="tools" role="search">
    <input type="search" id="q" placeholder="Search by name, sponsor, type, or state" aria-label="Search full-cycle investments" autocomplete="off">
    <select id="f-sponsor" aria-label="Filter by sponsor"><option value="">All sponsors</option></select>
    <select id="f-type" aria-label="Filter by property type"><option value="">All property types</option></select>
    <button type="button" class="tools__clear" id="clear" hidden>Clear</button>
  </div>
  <div class="tablewrap">
    <table class="table" id="table">
      <thead><tr>
        <th data-key="name" aria-sort="ascending">Investment name<span class="arrow"></span></th>
        <th data-key="sponsor">Sponsor<span class="arrow"></span></th>
        <th data-key="type">Property type<span class="arrow"></span></th>
        <th data-key="ret" class="num">Average annual return<span class="arrow"></span></th>
        <th data-key="em" class="num">Equity multiple<span class="arrow"></span></th>
        <th data-key="hold" class="num">Hold period<span class="arrow"></span></th>
      </tr></thead>
      <tbody id="tbody"></tbody>
      <tfoot><tr>
        <td class="name" colspan="3" id="avg-label">Average across all full-cycle investments</td>
        <td class="num" id="avg-ret"></td>
        <td class="num" id="avg-em"></td>
        <td class="num" id="avg-hold"></td>
      </tr></tfoot>
    </table>
  </div>
  </section>
  <p class="disclosure">These figures are sponsor-reported and reflect a limited sample of completed investments. They’re subject to selection and survivorship bias, don’t represent the entire industry, and don’t guarantee future results. Average annual return and equity multiple are as reported by each sponsor at the time of sale, before individual investor taxes. Averages shown are simple (unweighted) averages of the investments listed; where a sponsor did not report a figure it is shown as “—” and excluded from that average. Past performance does not guarantee future results; investments in DSTs and other private placements involve substantial risk, including loss of principal.</p>

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
  // Full-cycle results (in production this comes from the Results source; numbers are sponsor-reported)
  var RESULTS = ''' + json.dumps(data) + r''';
  var LABEL = { name:'investment name', sponsor:'sponsor', type:'property type', ret:'average annual return', em:'equity multiple', hold:'hold period' };
  var tbody = document.getElementById('tbody'), heads = Array.prototype.slice.call(document.querySelectorAll('#table th'));
  var sort = { key:'name', dir:1 };
  var filt = { q:'', sponsor:'', type:'' };
  var qEl = document.getElementById('q'), spEl = document.getElementById('f-sponsor'), tyEl = document.getElementById('f-type'), clearEl = document.getElementById('clear');
  function uniq(field){ var seen = {}; RESULTS.forEach(function(r){ seen[r[field]] = 1; }); return Object.keys(seen).sort(function(a, b){ return a.localeCompare(b); }); }
  uniq('sponsor').forEach(function(v){ var o = document.createElement('option'); o.value = v; o.textContent = v; spEl.appendChild(o); });
  uniq('type').forEach(function(v){ var o = document.createElement('option'); o.value = v; o.textContent = v; tyEl.appendChild(o); });
  function norm(s){ return String(s).toLowerCase(); }
  function visible(){
    var q = norm(filt.q).trim();
    return RESULTS.filter(function(r){
      if(filt.sponsor && r.sponsor !== filt.sponsor) return false;
      if(filt.type && r.type !== filt.type) return false;
      if(!q) return true;
      return norm(r.name + ' ' + r.sponsor + ' ' + r.type + ' ' + r.state).indexOf(q) > -1;
    });
  }

  function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
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
  var NA = '<td class="num na" title="Not reported by the sponsor">—</td>';
  function fmtHold(y){ var n = Math.round(y * 100) / 100; return n + (n === 1 ? ' yr' : ' yrs'); }
  function fmtPct(v){ return v === null ? null : v.toFixed(2) + '%'; }
  function fmtEm(v){ return v === null ? null : v.toFixed(2) + 'x'; }
  function cell(v, cls){ return v === null ? NA : '<td class="num' + (cls ? ' ' + cls : '') + '">' + v + '</td>'; }
  function fmtCount(n){ return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function row(r){
    return '<tr data-id="r' + r.id + '">' +
      '<td class="name">' + esc(r.name) + (r.state ? '<small>' + esc(r.state) + '</small>' : '') + '</td>' +
      '<td>' + esc(r.sponsor) + '</td>' +
      '<td>' + esc(r.type) + '</td>' +
      cell(fmtPct(r.ret), 'is-accent') +
      cell(fmtEm(r.em)) +
      cell(r.hold === null ? null : fmtHold(r.hold)) +
    '</tr>';
  }
  // null-aware compare: missing figures always sink to the bottom, whichever direction is chosen
  function cmp(a, b, key, dir){
    var va = a[key], vb = b[key];
    if(typeof va === 'string' || typeof vb === 'string') return String(va).localeCompare(String(vb)) * dir;
    if(va === null && vb === null) return 0;
    if(va === null) return 1;
    if(vb === null) return -1;
    return (va - vb) * dir;
  }
  // averages: simple (unweighted) across the deals that report the figure
  function mean(list, k){ var xs = list.filter(function(r){ return r[k] !== null; }); return xs.length ? xs.reduce(function(t, r){ return t + r[k]; }, 0) / xs.length : null; }
  function render(){
    var list = visible().sort(function(a, b){ return cmp(a, b, sort.key, sort.dir) || a.name.localeCompare(b.name); });
    flipRows(tbody, function(){ tbody.innerHTML = list.length ? list.map(row).join('') : '<tr><td colspan="6" class="empty">No full-cycle investments match that search.</td></tr>'; });
    heads.forEach(function(th){
      if(th.dataset.key === sort.key) th.setAttribute('aria-sort', sort.dir === 1 ? 'ascending' : 'descending'); else th.removeAttribute('aria-sort');
    });
    var filtered = list.length !== RESULTS.length;
    document.getElementById('count').textContent = filtered ? fmtCount(list.length) + ' of ' + fmtCount(RESULTS.length) : fmtCount(RESULTS.length);
    document.getElementById('sorted').textContent = 'Sorted by ' + LABEL[sort.key] + (sort.dir === 1 ? (sort.key === 'name' || sort.key === 'sponsor' || sort.key === 'type' ? ', A to Z' : ', low to high') : (sort.key === 'name' || sort.key === 'sponsor' || sort.key === 'type' ? ', Z to A' : ', high to low'));
    var r = mean(list, 'ret'), e = mean(list, 'em'), h = mean(list, 'hold');
    document.getElementById('avg-label').textContent = filtered ? 'Average across the ' + fmtCount(list.length) + ' investments shown' : 'Average across all full-cycle investments';
    document.getElementById('avg-ret').textContent = r === null ? '—' : fmtPct(r);
    document.getElementById('avg-em').textContent = e === null ? '—' : fmtEm(e);
    document.getElementById('avg-hold').textContent = h === null ? '—' : fmtHold(h);
    clearEl.hidden = !(filt.q || filt.sponsor || filt.type);
  }
  qEl.addEventListener('input', function(){ filt.q = qEl.value; render(); });
  spEl.addEventListener('change', function(){ filt.sponsor = spEl.value; render(); });
  tyEl.addEventListener('change', function(){ filt.type = tyEl.value; render(); });
  clearEl.addEventListener('click', function(){ filt = { q:'', sponsor:'', type:'' }; qEl.value = ''; spEl.value = ''; tyEl.value = ''; render(); qEl.focus(); });

  document.querySelector('#table thead').addEventListener('click', function(e){
    var th = e.target.closest('th'); if(!th) return;
    var key = th.dataset.key;
    var numeric = key === 'ret' || key === 'em' || key === 'hold';
    sort = sort.key === key ? { key:key, dir:-sort.dir } : { key:key, dir: numeric ? -1 : 1 };   // numbers open high-to-low
    render();
  });
  render();

  // ---- Roll-ups from the full-cycle deals (by sponsor, by asset class) ----
  function stats(deals){
    var n = deals.length; if(!n) return null;
    var withEm = deals.filter(function(r){ return r.em !== null; });
    return {
      n:n, ret:mean(deals, 'ret'), em:mean(deals, 'em'), hold:mean(deals, 'hold'),
      success: withEm.length ? withEm.filter(function(r){ return r.em >= 1; }).length / withEm.length * 100 : null
    };
  }
  function rollup(field){
    var by = {};
    RESULTS.forEach(function(r){ (by[r[field]] || (by[r[field]] = [])).push(r); });
    return Object.keys(by).map(function(k){ var g = stats(by[k]); g.key = k; return g; });
  }
  var PREFERRED = ''' + json.dumps(fc.PREFERRED) + r''';   // preferred sponsors (build/fullcycle.py)
  var SPONSORS = rollup('sponsor').map(function(g){ g.sponsor = g.key; g.preferred = PREFERRED.indexOf(g.key) > -1; return g; });
  var ASSETS = rollup('type').map(function(g){ g.type = g.key; return g; });
  var spSort = { key:'sponsor', dir:1 };
  var spHeads = Array.prototype.slice.call(document.querySelectorAll('#sptable th'));
  var SPLABEL = { sponsor:'sponsor', n:'number of full-cycle deals', ret:'average annual return', em:'average equity multiple', hold:'average hold period', success:'success rate' };
  function statCells(g){
    return '<td class="num">' + fmtCount(g.n) + '</td>' +
      cell(fmtPct(g.ret), 'is-accent') +
      cell(fmtEm(g.em)) +
      cell(g.hold === null ? null : fmtHold(g.hold)) +
      cell(g.success === null ? null : Math.round(g.success) + '%');
  }
  function spRow(g){
    return '<tr data-id="sp:' + esc(g.sponsor) + '"><td class="name">' + esc(g.sponsor) + (g.preferred ? '<span class="star" title="Preferred sponsor" aria-label="Preferred sponsor">★</span>' : '') + '</td>' + statCells(g) + '</tr>';
  }
  function renderSponsors(){
    var list = SPONSORS.slice().sort(function(a, b){ return cmp(a, b, spSort.key, spSort.dir) || a.sponsor.localeCompare(b.sponsor); });
    var spb = document.getElementById('sptbody'); flipRows(spb, function(){ spb.innerHTML = list.map(spRow).join(''); });
    spHeads.forEach(function(th){ if(th.dataset.key === spSort.key) th.setAttribute('aria-sort', spSort.dir === 1 ? 'ascending' : 'descending'); else th.removeAttribute('aria-sort'); });
    document.getElementById('sorted-sp').textContent = 'Sorted by ' + SPLABEL[spSort.key] + (spSort.key === 'sponsor' ? (spSort.dir === 1 ? ', A to Z' : ', Z to A') : (spSort.dir === 1 ? ', low to high' : ', high to low'));
  }
  document.querySelector('#sptable thead').addEventListener('click', function(e){
    var th = e.target.closest('th'); if(!th) return;
    var key = th.dataset.key;
    spSort = spSort.key === key ? { key:key, dir:-spSort.dir } : { key:key, dir: key === 'sponsor' ? 1 : -1 };
    renderSponsors();
  });
  renderSponsors();
  // totals: computed across the underlying deals (deal-weighted), not an average of the sponsor averages
  var totals = stats;
  function totalRow(label, t){ return '<tr><td class="name">' + label + '</td>' + statCells(t) + '</tr>'; }
  var pref = totals(RESULTS.filter(function(r){ return PREFERRED.indexOf(r.sponsor) > -1; }));
  var all = totals(RESULTS);
  document.getElementById('spfoot').innerHTML = (pref ? totalRow('Preferred sponsors <span class="star" aria-hidden="true">★</span>', pref) : '') + totalRow('All tracked sponsors', all);

  // ---- Asset-class table ----
  var acSort = { key:'type', dir:1 };
  var acHeads = Array.prototype.slice.call(document.querySelectorAll('#actable th'));
  var ACLABEL = { type:'asset class', n:'number of deals', ret:'average annual return', em:'average equity multiple', hold:'average hold period', success:'success rate' };
  function acRow(g){ return '<tr data-id="ac:' + esc(g.type) + '"><td class="name">' + esc(g.type) + '</td>' + statCells(g) + '</tr>'; }
  function renderAssets(){
    var list = ASSETS.slice().sort(function(a, b){ return cmp(a, b, acSort.key, acSort.dir) || a.type.localeCompare(b.type); });
    var acb = document.getElementById('actbody'); flipRows(acb, function(){ acb.innerHTML = list.map(acRow).join(''); });
    acHeads.forEach(function(th){ if(th.dataset.key === acSort.key) th.setAttribute('aria-sort', acSort.dir === 1 ? 'ascending' : 'descending'); else th.removeAttribute('aria-sort'); });
    document.getElementById('sorted-ac').textContent = 'Sorted by ' + ACLABEL[acSort.key] + (acSort.key === 'type' ? (acSort.dir === 1 ? ', A to Z' : ', Z to A') : (acSort.dir === 1 ? ', low to high' : ', high to low'));
  }
  document.querySelector('#actable thead').addEventListener('click', function(e){
    var th = e.target.closest('th'); if(!th) return;
    var key = th.dataset.key;
    acSort = acSort.key === key ? { key:key, dir:-acSort.dir } : { key:key, dir: key === 'type' ? 1 : -1 };
    renderAssets();
  });
  renderAssets();
})();
</script>

</body>
</html>
'''
open('results_template.html', 'w').write(page)
out = page.replace('{{LOGO}}', a['logo']).replace('{{SKYLINE}}', a['skyline'])
open('/home/claude/results.html', 'w').write(out)
print('built', len(out))

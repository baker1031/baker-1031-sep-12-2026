import re, json
h = open('/home/claude/hero-jerry.html').read()
a = json.load(open('assets.json'))

def between(start, end, src=h):
    i = src.index(start); j = src.index(end, i); return src[i:j]

navcss = between('  /* ---------- Sticky nav ---------- */', '  /* section anchors land below the sticky bar */')
nav_mobile = between('    .nav__inner{ gap:16px; height:54px; }', '    .ctabar__inner{')
footcss = between('  /* ---------- Footer ---------- */', '  /* ---------- Sticky nav ---------- */')
navhtml = re.search(r'<header class="nav" id="nav">.*?</header>', h, flags=re.S).group(0)
navhtml = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', navhtml)
navhtml = navhtml.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"')
foot = re.search(r'<footer class="footer">.*?</footer>', h, flags=re.S).group(0)
foot = re.sub(r'<img src="data:image/png;base64,[^"]*" alt="Baker 1031"', '<img src="{{LOGO}}" alt="Baker 1031"', foot)
foot = foot.replace('href="#top"', 'href="/"').replace('href="#type-1031"', 'href="/invest/"').replace('href="#results"', 'href="/results/"').replace('href="#request-access"', 'href="/register/"')
navjs = between("  // Nav: shadow once scrolled; mobile menu toggle", "})();\n</script>")

page = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Log in — Baker 1031 Investments</title>
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Special+Gothic&family=Caveat:wght@400..700&display=swap" rel="stylesheet">
<style>
/* Brand fonts (self-hosted): Guardian Sans for text, Sanomat for headings */
:root{
    --black:#000; --white:#fff;
    --accent:#00A071; --accent-hover:#008F63; --accent-soft:#FCF7F0;
    --grey:#000000; --grey-light:rgba(0,0,0,.6); --hair:#D5D2CD; --hair-strong:#D5D2CD; --error:#DC2626;
    --radius:6px;
    --font:"Special Gothic", "Helvetica Neue", Helvetica, Arial, sans-serif;
    --display:"Special Gothic", "Helvetica Neue", Helvetica, Arial, sans-serif;
    --hand:"Caveat", "Segoe Print", "Bradley Hand", cursive;
  }
  *{ box-sizing:border-box; }
  html{ -webkit-text-size-adjust:100%; }
  body{ margin:0; background:var(--white); color:var(--black); font-family:var(--font); line-height:1.5; -webkit-font-smoothing:antialiased; min-height:100vh; display:flex; flex-direction:column; }
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
  .btn[disabled]{ opacity:.6; cursor:default; }

  /* ---------- Sticky nav (from the homepage) ---------- */
''' + navcss + r'''
  /* ---------- Login stage ---------- */
  .stage{
    flex:1 0 auto; position:relative; overflow:hidden;
    min-height:760px;
    background:var(--white);
    display:flex; align-items:flex-start; justify-content:center;
    padding:96px 24px 0;
  }
  .stage__sky{ position:absolute; left:0; right:0; bottom:-2px; pointer-events:none; opacity:.9; }
  .stage__sky img{ display:block; width:100%; height:auto; }
  .box{
    position:relative; z-index:1;
    width:100%; max-width:460px;
    background:var(--white); border:1px solid var(--hair-strong); border-radius:10px;
    box-shadow:0 20px 50px rgba(0,0,0,.08);
    padding:36px 36px 32px;
    margin-bottom:220px;
  }
  .box h1{ margin:0 0 6px; font-size:28px; font-weight:700; line-height:1.15; letter-spacing:-.02em; }
  .box h1 .hand{ font-family:var(--hand); font-weight:600; color:var(--accent); font-size:1.3em; line-height:.8; display:inline-block; transform:rotate(-3deg) translateY(.04em); margin-right:.08em; }
  .box__sub{ margin:0 0 26px; font-size:14.5px; color:var(--grey); }
  .box__sub a{ color:var(--accent); font-weight:600; text-decoration:none; }
  .box__sub a:hover{ text-decoration:underline; text-underline-offset:3px; }
  .field{ display:flex; flex-direction:column; }
  .field label{ font-size:13px; font-weight:600; color:var(--grey); margin-bottom:8px; }
  .field input{
    appearance:none; width:100%; font:inherit; font-size:17px; color:var(--black);
    background:var(--white); border:1px solid var(--hair-strong); border-radius:var(--radius);
    padding:12px 14px; outline:none; transition:border-color .2s ease, box-shadow .2s ease;
  }
  .field input::placeholder{ color:rgba(0,0,0,.45); }
  .field input:focus{ border-color:var(--accent); box-shadow:0 0 0 3px rgba(0,160,113,.18); }
  .field.is-invalid input{ border-color:var(--error); box-shadow:0 0 0 3px rgba(220,38,38,.12); }
  .field .btn{ width:100%; margin-top:14px; padding:13px 20px; font-size:15px; }
  .err{
    display:none; margin:12px 0 0; padding:12px 14px;
    border:1px solid #FECACA; border-left:3px solid var(--error); border-radius:var(--radius); background:#FEF2F2;
    font-size:13.5px; line-height:1.5; color:#7F1D1D;
  }
  .err.is-on{ display:block; }
  .err a{ color:var(--accent); font-weight:600; text-decoration:none; }
  .err a:hover{ text-decoration:underline; text-underline-offset:3px; }
  .ok{
    display:none; margin:12px 0 0; padding:12px 14px;
    border:1px solid #D5D2CD; border-left:3px solid var(--accent); border-radius:var(--radius); background:var(--accent-soft);
    font-size:13.5px; line-height:1.5; color:var(--grey);
  }
  .ok.is-on{ display:block; }
  .ok strong{ color:var(--black); }
  .box__help{ margin:22px 0 0; padding-top:18px; border-top:1px solid var(--hair); font-size:12.5px; line-height:1.5; color:var(--grey-light); }
  .box__help a{ color:var(--grey-light); text-decoration:underline; text-decoration-style:dotted; text-decoration-color:var(--accent); text-underline-offset:3px; }
  .box__help a:hover{ color:var(--accent); }

  .rule{ max-width:calc(1200px + 48px); margin:0 auto; padding:0 24px; width:100%; }
  .rule::before{ content:""; display:block; height:1px; background:#D5D2CD; }
  .rule--strong::before{ height:2px; background:#D5D2CD; }

  /* ---------- Footer (from the homepage) ---------- */
''' + footcss + r'''
  @media (max-width:900px){
''' + nav_mobile + r'''    .stage{ padding:40px 20px 0; min-height:560px; }
    .box{ padding:28px 22px 24px; margin-bottom:150px; }
    .box h1{ font-size:24px; }
    .footer__inner{ grid-template-columns:1fr 1fr; padding:40px 20px 32px; }
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

<main class="stage">
  <div class="stage__sky" aria-hidden="true"><img src="{{SKYLINE}}" alt="" width="2000" height="459"></div>
  <div class="box">
    <h1>Welcome back!</h1>
    <p class="box__sub">New to Baker 1031 Investments? <a href="/register/" id="create">Create an account</a></p>
    <form id="login" novalidate>
      <div class="field" id="field">
        <label for="email">Email address</label>
        <input id="email" name="email" type="email" placeholder="you@example.com" autocomplete="email" inputmode="email" spellcheck="false" autocapitalize="off" autofocus>
        <button class="btn" type="submit" id="submit">
          Log in
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18.5 12L4.99997 12" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 18C13 18 19 13.5811 19 12C19 10.4188 13 6 13 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
      <p class="err" id="err" role="alert" aria-live="polite"></p>
      <p class="ok" id="ok" role="status" aria-live="polite"></p>
    </form>
    <div id="need2" hidden>
      <p class="box__sub" style="margin-top:0">That page holds material I release individually. You're signed in — this just needs my okay on top of it.</p>
      <button class="btn" type="button" id="ask2">
        Request access
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18.5 12L4.99997 12" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 18C13 18 19 13.5811 19 12C19 10.4188 13 6 13 6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </button>
      <p class="ok" id="ok2" role="status" aria-live="polite"></p>
      <p class="err" id="err2" role="alert" aria-live="polite"></p>
    </div>
    <p class="box__help">Trouble logging in? Email <a href="mailto:invest@baker1031.com">invest@baker1031.com</a> or call <a href="tel:+14159650552">(415) 965-0552</a>.</p>
  </div>
</main>

<div class="rule rule--strong" aria-hidden="true"></div>
''' + foot + r'''

<script>
(function(){
''' + navjs + r'''})();
</script>
<script>
(function(){
  var form = document.getElementById('login'), field = document.getElementById('field'), input = document.getElementById('email');
  var err = document.getElementById('err'), ok = document.getElementById('ok'), submit = document.getElementById('submit'), create = document.getElementById('create');

  // Keep the "Create an account" link carrying whatever they've typed
  function syncCreate(){
    var v = clean(input.value);
    create.href = '/register/' + (v ? '?email=' + encodeURIComponent(v) : '');
  }
  function clean(raw){
    var e = (raw || '').trim().replace(/^mailto:/i, '').replace(/^[<"'(\[\s]+|[>"')\]\s]+$/g, '').replace(/\s+/g, '').replace(/[.,;:]+$/, '');
    var at = e.lastIndexOf('@');
    if(at > -1) e = e.slice(0, at) + '@' + e.slice(at + 1).replace(/,/g, '.').toLowerCase();
    return e;
  }
  function looksLikeEmail(e){ return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e); }

  // ---- Approved-investor check ----
  // POST /api/auth {action:'login', email} (Netlify function) looks the address up in Airtable → Investor Access →
  // Investors by Email Address, case-insensitively, and returns { status: 'ok' | 'call_needed' | 'not_found' }.
  // On 'ok' it sets the HttpOnly session cookie and the readable `b31_ui` companion (first name). The list
  // itself never reaches the browser.
  function lookup(e){
    return fetch('/api/auth', { method:'POST', headers:{ 'content-type':'application/json' }, credentials:'same-origin',
                 body: JSON.stringify({ action:'login', email:e }) })
      .then(function(r){ if(!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  }
  // Where to go after logging in: ?next=/invest (same-site paths only), default the investments page.
  var nextParam = (function(){ try { var n = new URLSearchParams(window.location.search).get('next') || ''; return /^\/[^\/\\]/.test(n) ? n : '/invest/'; } catch(e){ return '/invest/'; } })();

  // ---- Restricted page (?need=2) ----
  // gate.js sends a logged-in investor here when the page they wanted needs the second approval tier.
  // The form is useless to them — they are already signed in — so it is swapped for a request button.
  (function(){
    var need2, box;
    try { need2 = new URLSearchParams(window.location.search).get('need') === '2'; } catch(e){ return; }
    if(!need2) return;
    box = document.getElementById('need2');
    var heading = document.querySelector('.box h1'), sub = document.querySelector('.box__sub');
    fetch('/api/auth', { method:'POST', headers:{ 'content-type':'application/json' }, credentials:'same-origin',
           body: JSON.stringify({ action:'me' }) })
      .then(function(r){ return r.json(); })
      .then(function(me){
        if(!me || !me.authed) return;               // not logged in after all — leave the normal form up
        if(me.level >= 2){ window.location.href = nextParam; return; }   // already cleared; go on through
        if(heading) heading.textContent = 'One more approval';
        if(sub) sub.hidden = true;
        form.hidden = true;
        box.hidden = false;
      }).catch(function(){});
    var btn = document.getElementById('ask2'), ok2 = document.getElementById('ok2'), err2 = document.getElementById('err2');
    btn.addEventListener('click', function(){
      btn.disabled = true; btn.firstChild.textContent = 'Sending… ';
      fetch('/api/auth', { method:'POST', headers:{ 'content-type':'application/json' }, credentials:'same-origin',
             body: JSON.stringify({ action:'request_level2', path:nextParam }) })
        .then(function(r){ return r.json(); })
        .then(function(res){
          if(res && res.already){ window.location.href = nextParam; return; }
          if(!res || !res.ok) throw new Error('failed');
          btn.hidden = true;
          ok2.innerHTML = '<strong>Request sent.</strong> Jerry will take a look and email you as soon as it\u2019s open — usually the same day.';
          ok2.classList.add('is-on');
        }).catch(function(){
          btn.disabled = false; btn.firstChild.textContent = 'Request access ';
          err2.innerHTML = 'That didn\u2019t go through. Email <a href="mailto:invest@baker1031.com">invest@baker1031.com</a> and I\u2019ll open it up manually.';
          err2.classList.add('is-on');
        });
    });
  })();

  function showError(html){ err.innerHTML = html; err.classList.add('is-on'); ok.classList.remove('is-on'); field.classList.add('is-invalid'); }
  function clearError(){ err.classList.remove('is-on'); field.classList.remove('is-invalid'); }

  input.addEventListener('input', function(){ clearError(); syncCreate(); });
  syncCreate();

  form.addEventListener('submit', function(ev){
    ev.preventDefault();
    var e = clean(input.value);
    if(e !== input.value) input.value = e;
    syncCreate();
    if(!e){ showError('Please enter your email address.'); input.focus(); return; }
    if(!looksLikeEmail(e)){ showError('That doesn’t look like a complete email address — could you double-check it?'); input.focus(); return; }
    submit.disabled = true; submit.firstChild.textContent = 'Checking… ';
    lookup(e).then(function(res){
      submit.disabled = false; submit.firstChild.textContent = 'Log in ';
      if(res.status === 'not_found'){
        showError('That email doesn’t match an account on file. Try again and check the spelling closely, or <a href="' + create.href + '">create a new account</a> with this address.');
        input.focus(); input.select();
        return;
      }
      if(res.status === 'call_needed'){
        var url = res.scheduleUrl || '/contact';
        showError('<strong>One more step.</strong> Regulations require a short introductory call before I can share current investments. <a href="' + url + '">Schedule your call</a> and access opens right after.');
        return;
      }
      if(res.status !== 'ok'){ showError('Something went wrong on our end. Please try again in a moment, or email <a href="mailto:invest@baker1031.com">invest@baker1031.com</a>.'); return; }
      clearError();
      ok.innerHTML = '<strong>Welcome back' + (res.firstName ? ', ' + res.firstName : '') + '.</strong> Sending you to your investments…';
      ok.classList.add('is-on');
      try { if(window.b1031 && window.b1031.setUi) window.b1031.setUi(res.firstName); } catch(err){}
      setTimeout(function(){ window.location.href = nextParam; }, 900);
    }).catch(function(){
      submit.disabled = false; submit.firstChild.textContent = 'Log in ';
      showError('The login service isn’t reachable right now. Please try again in a moment, or email <a href="mailto:invest@baker1031.com">invest@baker1031.com</a>.');
    });
  });
})();
</script>

</body>
</html>
'''
open('login_template.html','w').write(page)
out = page.replace('{{LOGO}}', a['logo']).replace('{{SKYLINE}}', a['skyline']).replace('{{SFPHOTO}}', a['sfphoto'])
open('/home/claude/login.html','w').write(out)
print('built', len(out))

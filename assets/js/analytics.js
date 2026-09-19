/*
  Baker 1031 — Google Analytics 4 (property 471868930, stream "Baker 1031").

  Loaded from the shared <head> on every page, so there is one copy of this to change.

  Why this is a file and not the stock inline snippet: several of the links the site emails out
  carry their auth token in the query string — the portal login link (?rid=&t=&sig=), the personal
  update link (?cid=&sig=) and the reminder opt-out (?cid=&sig=). GA records page_location with the
  query string intact, which would file working credentials into a third-party analytics product and
  leave them in its retained reports. So the reported URL has those parameters removed before the
  first page_view goes out. Everything else about the URL is reported normally.

  The register form already calls gtag('event','generate_lead') and gtag('event','schedule') behind
  an `if (window.gtag)` guard; defining window.gtag here is what switches those two on.
*/
(function () {
  var ID = 'G-P29LR49RL8';
  // Auth tokens and identifiers, not analytics dimensions.
  var STRIP = ['sig', 'cid', 'rid', 't', 'key', 'token', 'email'];

  function reportable(href) {
    try {
      var u = new URL(href, location.origin);
      var hit = false;
      for (var i = 0; i < STRIP.length; i++) {
        if (u.searchParams.has(STRIP[i])) { u.searchParams.delete(STRIP[i]); hit = true; }
      }
      if (hit) u.searchParams.set('signed_link', '1');   // keeps the visit countable, drops the secret
      return u.toString();
    } catch (e) {
      // A URL we cannot parse is a URL we should not report verbatim.
      return location.origin + location.pathname;
    }
  }

  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };
  gtag('js', new Date());
  gtag('config', ID, { page_location: reportable(location.href) });

  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + ID;
  document.head.appendChild(s);
})();

/*
  Baker 1031 — what a logged-in investor does, reported to the CRM (crm.baker1031.com).

  Separate from Google Analytics above, which is anonymous. This part runs only for someone who is logged in
  to the investor portal (the readable b31_ui cookie is the same signal the nav uses) and sends three things
  to /api/auth, which checks the signed session and passes them on with the investor's identity:
    view       the page they opened: the offering slug when it is an offering page, the heading and the path
    view_end   how long the page was actually in front of them (time in a background tab does not count)
    download   a document they opened: PDFs and other files, by link text and address
  The address is sent without its query string, so no signed link or token ever travels. A visitor who is not
  logged in sends nothing.
*/
(function () {
  if (!/(?:^|;\s*)b31_ui=/.test(document.cookie) || !window.fetch) return;
  var pv = (Date.now().toString(36) + Math.random().toString(36).slice(2, 10)).slice(0, 20);
  var slug = (document.body && document.body.getAttribute('data-offering')) || '';
  var h1 = document.querySelector('h1');
  var title = ((h1 && h1.textContent) || document.title || '').replace(/\s+/g, ' ').replace(/\s*[|–-]\s*Baker 1031.*$/i, '').trim().slice(0, 160);

  function send(payload, leaving) {
    payload.action = 'track';
    var body = JSON.stringify(payload);
    try {
      if (leaving && navigator.sendBeacon) { navigator.sendBeacon('/api/auth', new Blob([body], { type: 'application/json' })); return; }
      fetch('/api/auth', { method: 'POST', credentials: 'same-origin', keepalive: true, headers: { 'content-type': 'application/json' }, body: body }).catch(function () {});
    } catch (e) { /* never in the way of the page */ }
  }

  send({ kind: 'view', pv: pv, slug: slug, title: title, path: location.pathname });

  // Time in view: the clock runs only while the tab is visible, and the total goes out when they leave
  // or switch away (and again if it has grown by the time they really go).
  var active = 0, since = document.visibilityState === 'visible' ? Date.now() : 0, reported = 0;
  function tally() { if (since) { active += Date.now() - since; since = 0; } }
  function report() {
    tally();
    var secs = Math.round(active / 1000);
    if (secs >= 3 && secs - reported >= 3) { reported = secs; send({ kind: 'view_end', pv: pv, seconds: secs }, true); }
  }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') report(); else since = Date.now();
  });
  window.addEventListener('pagehide', report);

  // Documents: any link to a file, a Dropbox or Box share, or one marked for download.
  var FILE = /\.(pdf|docx?|xlsx?|pptx?|csv|zip)$/i, HOSTS = /(^|\.)(dropbox\.com|dropboxusercontent\.com|box\.com|drive\.google\.com|docsend\.com)$/i;
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var u; try { u = new URL(a.getAttribute('href'), location.href); } catch (x) { return; }
    if (!(FILE.test(u.pathname) || a.hasAttribute('download') || HOSTS.test(u.hostname))) return;
    var label = (a.getAttribute('data-doc') || a.textContent || '').replace(/\s+/g, ' ').trim() || decodeURIComponent(u.pathname.split('/').pop() || 'Document');
    send({ kind: 'download', href: u.origin + u.pathname, name: label.slice(0, 160), slug: slug, offering: slug ? title : '' }, true);
  }, true);
})();

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

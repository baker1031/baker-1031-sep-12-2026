/*
  Baker 1031 — live offering status between builds.

  Offering pages and /invest/ are built from the Opportunities feed at deploy time, so a deal that sells out or
  closes between builds would keep its old status. This asks the same public feed once per page load
  (https://opportunities.baker1031.com/api/public/opportunities, CORS *, cached 60 s there and 60 s here in
  sessionStorage) and corrects the status in place. With JS off, or the feed unreachable, the built status stays.

  What it looks for (written by build_offering.py and build_inventory.py):
    [data-opp-slug][data-opp-status]   one offering; data-opp-status is rewritten to the live status
      [data-opp-label="full"|"short"]  the status pill inside it: text, title and its status--* class are updated
      data-opp-muted-class="x"         class to toggle on the element for Closed / Rejected / gone (dimmed, as the build does)
    [data-opp-crumb]                   the offering page's breadcrumb: "Available Investments" or "Investments", as built

  A deal missing from the feed (hidden or removed in the Opportunities tool) is shown as "No longer available",
  treated like Closed. /invest/ also listens for the "b1031:live-status" event and re-renders its list from the
  live statuses, so its own sort and filters (open deals first, closed ones dimmed) stay the build's.
*/
(function () {
  var FEED = 'https://opportunities.baker1031.com/api/public/opportunities';
  var CACHE_KEY = 'b1031-opp-live', TTL = 60000;
  var GONE = 'No longer available';
  var OPEN = ['Available', 'Limited Availability'];
  var MUTED = ['Closed', 'Rejected', GONE];
  // Same classes as build_offering.py STATUS_CLS / build_inventory.py statusPill; an unknown status gets the default pill.
  var CLS = { 'Available': '', 'Limited Availability': 'status--limited', 'Pending Approval': 'status--soon', 'Under Review': 'status--soon',
    'Closed': 'status--sold', 'Rejected': 'status--rejected' };
  CLS[GONE] = 'status--sold';
  var FULL = { 'Closed': 'Closed — no longer available' };
  var SHORT = { 'Limited Availability': 'Limited', 'Pending Approval': 'Pending', 'Under Review': 'Review', 'Closed': 'Closed' };
  SHORT[GONE] = 'Unavailable';

  // feed JSON -> { slug: { status, remainingPct, available } }
  function reduce(feed) {
    var out = {};
    var list = (feed && feed.opportunities) || [];
    for (var i = 0; i < list.length; i++) {
      var o = list[i];
      if (!o || !o.slug) continue;
      out[o.slug] = { status: o.status || 'Available', remainingPct: typeof o.remainingPct === 'number' ? o.remainingPct : null, available: o.availableForInvestment !== false };
    }
    return out;
  }

  function liveFor(slug, bySlug) {
    var l = bySlug[slug];
    var status = l ? l.status : GONE;
    return {
      status: status,
      full: FULL[status] || status,
      short: SHORT[status] || status,
      cls: CLS[status] || '',
      muted: MUTED.indexOf(status) > -1,
      open: OPEN.indexOf(status) > -1,
      remainingPct: l ? l.remainingPct : null,
    };
  }

  function setPill(pill, live) {
    var kind = pill.getAttribute('data-opp-label') === 'short' ? 'short' : 'full';
    pill.textContent = live[kind];
    pill.setAttribute('title', live.full);
    var keep = String(pill.className || '').split(/\s+/).filter(function (c) { return c && !/^status--/.test(c); });
    if (live.cls) keep.push(live.cls);
    pill.className = keep.join(' ');
  }

  function toggle(el, cls, on) {
    var list = String(el.className || '').split(/\s+/).filter(function (c) { return c && c !== cls; });
    if (on) list.push(cls);
    el.className = list.join(' ');
  }

  // Updates every marked element in `doc`. Returns how many offerings changed status.
  function apply(bySlug, doc) {
    var changed = 0;
    var els = doc.querySelectorAll('[data-opp-slug]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i], live = liveFor(el.getAttribute('data-opp-slug'), bySlug);
      if (el.getAttribute('data-opp-status') !== live.status) changed++;
      el.setAttribute('data-opp-status', live.status);
      if (live.remainingPct != null) el.setAttribute('data-opp-remaining', String(live.remainingPct));
      var pills = el.querySelectorAll('[data-opp-label]');
      for (var j = 0; j < pills.length; j++) setPill(pills[j], live);
      if (el.hasAttribute('data-opp-label')) setPill(el, live);
      var muted = el.getAttribute('data-opp-muted-class');
      if (muted) toggle(el, muted, live.muted);
      toggle(el, 'is-opp-limited', live.status === 'Limited Availability');
    }
    var crumbs = doc.querySelectorAll('[data-opp-crumb]');
    for (var k = 0; k < crumbs.length; k++) {
      crumbs[k].textContent = liveFor(crumbs[k].getAttribute('data-opp-crumb'), bySlug).open ? 'Available Investments' : 'Investments';
    }
    return changed;
  }

  function cached(storage, now) {
    try {
      var c = JSON.parse(storage.getItem(CACHE_KEY) || 'null');
      if (c && c.bySlug && now - c.at < TTL && now >= c.at) return c.bySlug;
    } catch (e) { /* private mode, bad JSON */ }
    return null;
  }

  // One request per page load at most, and none within 60 s of the last one in this tab. Resolves null on any failure.
  function load(env) {
    env = env || {};
    var storage = env.storage, now = (env.now || Date.now)(), doFetch = env.fetch;
    var hit = storage ? cached(storage, now) : null;
    if (hit) return Promise.resolve(hit);
    if (!doFetch) return Promise.resolve(null);
    try {
      return doFetch(FEED, { credentials: 'omit', headers: { accept: 'application/json' } })
        .then(function (r) { return r && r.ok ? r.json() : null; })
        .then(function (feed) {
          if (!feed || !feed.opportunities || !feed.opportunities.length) return null;   // an empty feed is an outage, not "everything closed"
          var bySlug = reduce(feed);
          try { if (storage) storage.setItem(CACHE_KEY, JSON.stringify({ at: now, bySlug: bySlug })); } catch (e) { /* quota, private mode */ }
          return bySlug;
        })
        .catch(function () { return null; });
    } catch (e) { return Promise.resolve(null); }
  }

  function run(env) {
    var doc = env.document;
    if (!doc || !doc.querySelector('[data-opp-slug]')) return Promise.resolve(null);
    return load(env).then(function (bySlug) {
      if (!bySlug) return null;
      try {
        if (typeof env.CustomEvent === 'function') doc.dispatchEvent(new env.CustomEvent('b1031:live-status', { detail: { bySlug: bySlug, gone: GONE } }));
      } catch (e) { /* a listener failed; the in-place update below still runs */ }
      try { return apply(bySlug, doc); } catch (e) { return null; }
    });
  }

  var api = { FEED: FEED, CACHE_KEY: CACHE_KEY, GONE: GONE, reduce: reduce, liveFor: liveFor, apply: apply, load: load, run: run };
  if (typeof module !== 'undefined' && module.exports) { module.exports = api; return; }

  try {
    var storage = null;
    try { storage = window.sessionStorage; } catch (e) { storage = null; }
    run({ document: document, storage: storage, fetch: window.fetch ? window.fetch.bind(window) : null, CustomEvent: window.CustomEvent });
  } catch (e) { /* never break the page */ }
})();

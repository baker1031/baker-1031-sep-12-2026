/*
  Baker 1031 — investor gate (Netlify Edge Function, runs on every request)
  SOFT GATING (Sept 2026): offerings and learn pages are served to everyone so
  search engines and AI crawlers can read them; the client-side overlay in
  auth-client.js asks non-logged-in visitors to log in (Google's flexible-sampling
  pattern, declared via isAccessibleForFree schema). This edge function now only
  hard-gates paths NOT in the allowlist below — add a prefix here to hard-gate it.
  Public pages pass through; everything else requires a valid signed session
  cookie (set by /api/auth login) or is redirected to /login/?next=<path>.
  This is the real enforcement layer — the client-side script only handles
  the header swap and view tracking.

  Env: SESSION_SECRET (must match the auth function's).
*/

const COOKIE = 'b31_session';

// Paths served without a session. Everything else is gated.
const PUBLIC_PREFIXES = [
  '/login',
  '/register',
  '/invest',
  '/results',
  '/offerings',
  '/learn',
  '/offerings',
  '/calculators',
  '/contact',
  '/update-my-info',
  '/schedule-call',
  '/schedule-consultation',
  '/privacy',
  '/terms',
  '/disclosures',
  '/request-access',
  '/update-my-info',
  '/assets/',
  '/api/',
  '/.netlify/',
  '/.well-known/', // ACME/TLS certificate challenges must never be gated
  // Content sections ported from the previous site — all public/educational.
  '/glossary',
  '/markets',
  '/sponsors',
  '/property-types',
  '/strategies',   // the six investment types behind the homepage accordion
  '/audiences',
  '/process',
  '/reg-bi',
  '/ccpa',
  '/accessibility',
  '/commitment-to-privacy',
];
const PUBLIC_EXACT = ['/', '/index.html', '/favicon.ico', '/robots.txt', '/sitemap.xml',
  '/llms.txt', '/apple-touch-icon.png', '/404.html', '/build-info.json'];

function isPublic(pathname) {
  if (PUBLIC_EXACT.includes(pathname)) return true;
  // IndexNow ownership proof. build.js writes /<INDEXNOW_KEY>.txt into dist only
  // when that variable is set, and Bing fetches it with no cookie to confirm the
  // key really belongs to this host -- so the gate has to let it through, or the
  // fetch lands on /login/ and every submission is rejected. Matched against the
  // variable itself rather than a generic "any .txt at the root" rule, so this
  // opens exactly one path and only on a site that opted in.
  const indexNowKey = (typeof Deno !== 'undefined' && Deno.env.get('INDEXNOW_KEY')) || '';
  if (indexNowKey && pathname === `/${indexNowKey}.txt`) return true;
  return PUBLIC_PREFIXES.some((p) =>
    p.endsWith('/') ? pathname.startsWith(p) : (pathname === p || pathname.startsWith(p + '/')),
  );
}

const b64url = (buf) =>
  btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

async function validSession(cookieHeader, secret) {
  if (!cookieHeader || !secret) return false;
  const raw = cookieHeader.split(/;\s*/).find((c) => c.startsWith(COOKIE + '='));
  if (!raw) return false;
  const [payload, sig] = raw.slice(COOKIE.length + 1).split('.');
  if (!payload || !sig) return false;
  try {
    const key = await crypto.subtle.importKey(
      'raw', new TextEncoder().encode(secret),
      { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'],
    );
    const mac = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload));
    if (b64url(mac) !== sig) return false; // signature mismatch
    const s = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return s.exp > Date.now();
  } catch {
    return false;
  }
}

// Legacy paths from the previous site → their new homes (301).
const LEGACY = {
  '/privacy-policy': '/privacy/',
  '/privacy-policy/': '/privacy/',
  '/current-offerings': '/invest/',
  '/current-offerings/': '/invest/',
  // Previous site: the inventory lived at /offerings/, registration at /request-access/, the data page at /performance/.
  '/offerings': '/invest/',
  '/offerings/': '/invest/',
  '/request-access': '/register/',
  '/request-access/': '/register/',
  '/performance': '/results/',
  '/performance/': '/results/',
  '/about/jerry-baker': '/#glance',
  '/about/jerry-baker/': '/#glance',
};

const perm = (to) => new Response(null, { status: 301, headers: { location: to, 'cache-control': 'no-store' } });

export default async (request, context) => {
  const url = new URL(request.url);
  if (LEGACY[url.pathname]) return perm(LEGACY[url.pathname]);
  if (url.pathname.startsWith('/current-offerings/')) return perm('/invest/');

  // Offering DOCUMENTS are hard-gated even though offering pages are soft-gated
  // for crawlers: PPMs and sub docs go only to logged-in investors.
  const docMatch = url.pathname.match(/^(\/offerings\/[^/]+)\/docs\//);
  if (docMatch) {
    const secret = Deno.env.get('SESSION_SECRET') || '';
    if (await validSession(request.headers.get('cookie'), secret)) return context.next();
    return new Response(null, {
      status: 302,
      headers: { location: `/login/?next=${encodeURIComponent(docMatch[1] + '/')}`, 'cache-control': 'no-store' },
    });
  }

  if (isPublic(url.pathname)) {
    const res = await context.next();
    // Old offering/calculator URLs that no longer exist → their section hub,
    // so pre-cutover links and rankings don't dead-end on a 404.
    if (res.status === 404 && /^\/(offerings|calculators)\/./.test(url.pathname)) {
      return perm(url.pathname.startsWith('/offerings/') ? '/invest/' : '/calculators/');
    }
    return res;
  }

  const secret = Deno.env.get('SESSION_SECRET') || '';
  if (await validSession(request.headers.get('cookie'), secret)) return context.next();

  // No session on a non-public path. If the page doesn't exist at all, serve
  // the real 404 — bouncing unknown URLs to the login page reads as a soft
  // redirect to crawlers and confuses people who mistyped a URL.
  const probe = await context.next();
  if (probe.status === 404) return probe;

  const dest = `/login/?next=${encodeURIComponent(url.pathname)}`;
  return new Response(null, {
    status: 302,
    headers: { location: dest, 'cache-control': 'no-store' },
  });
};

export const config = { path: '/*' };

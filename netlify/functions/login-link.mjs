/*
  Baker 1031 — first-time auto-login (GET /api/login-link)
  ?rid=<Airtable record id>&t=<issued ms>&sig=<HMAC>

  Sent in the portal welcome email (portal-sync.mjs). Clicking it verifies the
  signature, checks the link is under 30 days old, re-checks the investor's
  Access Level in Airtable (so a revoked investor's link is dead immediately),
  sets the same signed session cookie the normal login flow uses, and redirects
  into the portal. Any failure lands on /login/ where the person can sign in
  the usual way — never an error page.

  No personal data travels in the URL: rid is an opaque Airtable record id.
  Env: AIRTABLE_TOKEN, SESSION_SECRET (+ optional ACCESS_BASE_ID, ACCESS_TABLE_ID,
       SESSION_DAYS).
*/
import crypto from 'node:crypto';

const BASE = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ';
const TABLE = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';
const DAYS = parseInt(process.env.SESSION_DAYS || '30', 10);
const LINK_MAX_AGE_MS = 30 * 86400000; // magic links work for 30 days
const COOKIE = 'b31_session';

const b64u = (buf) => Buffer.from(buf).toString('base64url');
const hmac = (payload) => crypto.createHmac('sha256', process.env.SESSION_SECRET || '').update(payload).digest();

export const linkSig = (rid, t) => b64u(hmac(`portal-login:${rid}:${t}`)).slice(0, 32);

function makeCookie(rid, firstName) {
  const exp = Date.now() + DAYS * 86400000;
  const payload = b64u(JSON.stringify({ rid, fn: firstName, exp }));
  const value = `${payload}.${b64u(hmac(payload))}`;
  return [`${COOKIE}=${value}; Path=/; Max-Age=${DAYS * 86400}; HttpOnly; Secure; SameSite=Lax`,
          `b31_ui=${encodeURIComponent(firstName || 'Investor')}; Path=/; Max-Age=${DAYS * 86400}; Secure; SameSite=Lax`];
}

const redirect = (to, cookie) => ({
  statusCode: 302,
  headers: { location: to, 'cache-control': 'no-store' },
  ...(cookie ? { multiValueHeaders: { 'set-cookie': [].concat(cookie) } } : {}),
  body: '',
});

export const handler = async (event) => {
  const q = event.queryStringParameters || {};
  const { rid, t, sig } = q;
  const toLogin = redirect('/login/?ll=expired');

  if (!rid || !t || !sig || !/^rec[A-Za-z0-9]{14}$/.test(rid) || !/^\d{10,16}$/.test(t)) return toLogin;

  const want = Buffer.from(linkSig(rid, t));
  const got = Buffer.from(String(sig));
  if (want.length !== got.length || !crypto.timingSafeEqual(want, got)) return toLogin;
  if (Date.now() - Number(t) > LINK_MAX_AGE_MS) return toLogin; // expired — normal login still works

  // Live check: only currently-Approved investors get a session.
  try {
    const res = await fetch(`https://api.airtable.com/v0/${BASE}/${TABLE}/${rid}`, {
      headers: { Authorization: `Bearer ${process.env.AIRTABLE_TOKEN}` },
    });
    if (!res.ok) return toLogin;
    const rec = await res.json();
    if ((rec.fields || {})['Access Level'] !== 'Approved') return toLogin;
    // Explicit query stops Netlify from forwarding the token params onto the
    // destination URL (keeps the signed token out of the address bar/history).
    return redirect('/invest/?welcome=1', makeCookie(rid, rec.fields['First Name'] || 'Investor'));
  } catch {
    return toLogin;
  }
};

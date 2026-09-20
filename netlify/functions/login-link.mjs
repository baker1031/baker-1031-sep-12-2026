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
import { tellCrm, crmApi, usingCrm } from './lib/crm.mjs';
import crypto from 'node:crypto';

const BASE = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ';
const TABLE = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';
const DAYS = parseInt(process.env.SESSION_DAYS || '30', 10);
const LINK_MAX_AGE_MS = 30 * 86400000; // magic links work for 30 days
const COOKIE = 'b31_session';

const b64u = (buf) => Buffer.from(buf).toString('base64url');
const hmac = (payload) => crypto.createHmac('sha256', process.env.SESSION_SECRET || '').update(payload).digest();

export const linkSig = (rid, t) => b64u(hmac(`portal-login:${rid}:${t}`)).slice(0, 32);

function makeCookie(rid, firstName, level = 1) {
  const exp = Date.now() + DAYS * 86400000;
  const payload = b64u(JSON.stringify({ rid, fn: firstName, exp, lvl: level }));
  const value = `${payload}.${b64u(hmac(payload))}`;
  return [`${COOKIE}=${value}; Path=/; Max-Age=${DAYS * 86400}; HttpOnly; Secure; SameSite=Lax`,
          `b31_ui=${encodeURIComponent(firstName || 'Investor')}; Path=/; Max-Age=${DAYS * 86400}; Secure; SameSite=Lax`,
          `b31_lvl=${level}; Path=/; Max-Age=${DAYS * 86400}; Secure; SameSite=Lax`];
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

  // Links the CRM issued (?cid=...): the CRM signed them, so the CRM checks them, along with whether access is still on.
  if (q.cid) {
    if (!/^[A-Za-z0-9_-]{6,80}$/.test(q.cid) || !/^\d{10,16}$/.test(String(t || '')) || !sig || !(await usingCrm())) return toLogin;
    const r = await crmApi('login_link', { cid: q.cid, t, sig: String(sig).slice(0, 80) });
    if (!r.ok || !r.body.ok) return toLogin;
    await tellCrm('site.login', r.body.email, { via: 'email link' }, [r.body.firstName, r.body.lastName].filter(Boolean).join(' '));
    return redirect('/invest/?welcome=1', makeCookie(r.body.rid, r.body.firstName || 'Investor', r.body.level));
  }

  if (!rid || !t || !sig || !/^rec[A-Za-z0-9]{14}$/.test(rid) || !/^\d{10,16}$/.test(t)) return toLogin;

  const want = Buffer.from(linkSig(rid, t));
  const got = Buffer.from(String(sig));
  if (want.length !== got.length || !crypto.timingSafeEqual(want, got)) return toLogin;
  if (Date.now() - Number(t) > LINK_MAX_AGE_MS) return toLogin; // expired — normal login still works

  // A link from before the move, with the site now on the CRM: this site signed it, so the check above stands, and
  // the CRM says whether that person still has access (it kept the old id when it imported them).
  if (await usingCrm()) {
    const r = await crmApi('person', { rid });
    if (!r.ok || !r.body.ok || !r.body.approved) return toLogin;
    await tellCrm('site.login', r.body.email, { via: 'email link' }, [r.body.firstName, r.body.lastName].filter(Boolean).join(' '));
    return redirect('/invest/?welcome=1', makeCookie(r.body.rid, r.body.firstName || 'Investor', r.body.level));
  }

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
    const level = String((rec.fields || {})['Level 2 Access'] || '').toLowerCase() === 'approved' ? 2 : 1;
    await tellCrm('site.login', rec.fields['Email Address'], { via: 'email link' }, [rec.fields['First Name'], rec.fields['Last Name']].filter(Boolean).join(' '));
    return redirect('/invest/?welcome=1', makeCookie(rid, rec.fields['First Name'] || 'Investor', level));
  } catch {
    return toLogin;
  }
};

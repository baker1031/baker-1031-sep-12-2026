/*
  Baker 1031 — investor auth API (Netlify Function)
  Routes (POST /api/auth with JSON {action, ...}):
    check_email {email}      -> {exists}
    login       {email}      -> {status: "ok"|"call_needed"|"not_found", ...} (+ session cookie on ok)
    me                       -> {authed, firstName}  (re-verifies the Airtable record, so revoking
                                access or flipping to Call Needed logs the person out server-side)
    logout                   -> clears the session cookie
    track_view  {slug}       -> appends the offering to the investor's "Deals Reviewed" (first view only)

  Env: AIRTABLE_TOKEN (data.records:read + write on Investor Access),
       ACCESS_BASE_ID, ACCESS_TABLE_ID, SESSION_SECRET (long random string),
       SESSION_DAYS (default 30), SCHEDULE_CALL_URL.
  The session is a signed HttpOnly cookie; the browser never sees the Airtable token.
*/
import crypto from 'node:crypto';

const BASE = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ';
const TABLE = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';
const TOKEN = process.env.AIRTABLE_TOKEN;
const SECRET = process.env.SESSION_SECRET || '';
const DAYS = parseInt(process.env.SESSION_DAYS || '30', 10);
const SCHEDULE_URL = process.env.SCHEDULE_CALL_URL || 'https://calendly.com/jerry-baker-1031/introductory-consultation';
const COOKIE = 'b31_session';

// `cookie` may be one Set-Cookie value or an array (session cookie + readable companion).
const json = (status, body, cookie) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  ...(cookie ? { multiValueHeaders: { 'set-cookie': [].concat(cookie) } } : {}),
  body: JSON.stringify(body),
});
// Readable companion cookie (not HttpOnly): the investor's first name, so every page can render the
// "Welcome, <First>!" header before any request. It carries no secret — the signed HttpOnly cookie is the session.
const UI_COOKIE = 'b31_ui';
const uiCookie = (firstName) => `${UI_COOKIE}=${encodeURIComponent(firstName || 'Investor')}; Path=/; Max-Age=${DAYS * 86400}; Secure; SameSite=Lax`;
const clearUiCookie = () => `${UI_COOKIE}=; Path=/; Max-Age=0; Secure; SameSite=Lax`;

const b64u = (buf) => Buffer.from(buf).toString('base64url');
const sign = (payload) => crypto.createHmac('sha256', SECRET).update(payload).digest('base64url');

function makeCookie(rid, firstName) {
  const exp = Date.now() + DAYS * 86400000;
  const payload = b64u(JSON.stringify({ rid, fn: firstName, exp }));
  const value = `${payload}.${sign(payload)}`;
  return [`${COOKIE}=${value}; Path=/; Max-Age=${DAYS * 86400}; HttpOnly; Secure; SameSite=Lax`, uiCookie(firstName)];
}
const clearCookie = () => [`${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax`, clearUiCookie()];

function readSession(event) {
  const raw = (event.headers.cookie || '').split(/;\s*/).find((c) => c.startsWith(COOKIE + '='));
  if (!raw) return null;
  const [payload, sig] = raw.slice(COOKIE.length + 1).split('.');
  if (!payload || !sig) return null;
  if (!crypto.timingSafeEqual(Buffer.from(sign(payload)), Buffer.from(sig))) return null;
  try {
    const s = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    return s.exp > Date.now() ? s : null;
  } catch { return null; }
}

async function at(pathname, init = {}) {
  const res = await fetch(`https://api.airtable.com/v0/${BASE}/${TABLE}${pathname}`, {
    ...init,
    headers: { Authorization: `Bearer ${TOKEN}`, 'content-type': 'application/json', ...(init.headers || {}) },
  });
  if (!res.ok) throw new Error(`Airtable ${res.status}`);
  return res.json();
}

async function findByEmail(email) {
  const clean = String(email || '').trim().toLowerCase().replace(/"/g, '');
  if (!clean || !clean.includes('@')) return null;
  const formula = encodeURIComponent(`LOWER({Email Address}) = "${clean}"`);
  const data = await at(`?filterByFormula=${formula}&maxRecords=1`);
  return (data.records && data.records[0]) || null;
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { /* noop */ }
  const action = body.action;

  try {
    if (action === 'check_email') {
      const rec = await findByEmail(body.email);
      return json(200, { exists: !!rec });
    }

    if (action === 'login') {
      const rec = await findByEmail(body.email);
      if (!rec) return json(200, { status: 'not_found' });
      const level = rec.fields['Access Level'];
      if (level === 'Call Needed') return json(200, { status: 'call_needed', scheduleUrl: SCHEDULE_URL });
      if (level !== 'Approved') return json(200, { status: 'not_found' }); // Revoked etc. — no portal access
      return json(200, { status: 'ok', firstName: rec.fields['First Name'] || 'Investor' },
        makeCookie(rec.id, rec.fields['First Name'] || 'Investor'));
    }

    if (action === 'me') {
      const s = readSession(event);
      if (!s) return json(200, { authed: false });
      // Re-verify against Airtable so access revocation takes effect immediately.
      const data = await at(`/${s.rid}`).catch(() => null);
      if (!data || data.fields['Access Level'] !== 'Approved') return json(200, { authed: false }, clearCookie());
      return json(200, { authed: true, firstName: data.fields['First Name'] || s.fn || 'Investor' });
    }

    if (action === 'logout') return json(200, { ok: true }, clearCookie());

    if (action === 'track_view') {
      const s = readSession(event);
      if (!s) return json(401, { error: 'not logged in' });
      const slug = String(body.slug || '').slice(0, 120).replace(/[^a-z0-9-]/g, '');
      if (!slug) return json(400, { error: 'bad slug' });
      const rec = await at(`/${s.rid}`).catch(() => null);
      if (!rec) return json(401, { error: 'unknown investor' });
      const existing = rec.fields['Deals Reviewed'] || '';
      if (!existing.split('\n').some((l) => l.trim().startsWith(slug))) {
        const line = `${slug} (first viewed ${new Date().toISOString().slice(0, 10)})`;
        await at(`/${s.rid}`, {
          method: 'PATCH',
          body: JSON.stringify({ fields: { 'Deals Reviewed': existing ? existing + '\n' + line : line } }),
        });
        // A logged-in investor actively reviewing deals → note it in Attio and promote their deal
        // (ATTIO_REVIEW_STAGE), never demoting later stages.
        await moveToActivelyReviewing(rec.fields['Email Address'], slug).catch((e) => console.error('[auth] stage move:', e.message));
      }
      return json(200, { ok: true });
    }

    return json(400, { error: 'unknown action' });
  } catch (e) {
    console.error('[auth]', action, e.message);
    return json(500, { error: 'server error' });
  }
};

/*
  First offering view → in Attio, note it on the investor's person record and (when ATTIO_REVIEW_STAGE is
  set, e.g. "Actively Reviewing") move their open website deal to that stage. Promotes only from the stages
  listed in ATTIO_PROMOTE_FROM (comma-separated titles; default: the new-deal stage, "Lead") so a deal that
  is further along is never moved backwards. Best effort — never blocks the page.
*/
import * as attio from './lib/attio.mjs';

async function moveToActivelyReviewing(email, slug) {
  if (!attio.configured() || !email) return;
  const person = await attio.findPersonByEmail(email);
  if (!person) return;
  const personId = person.id.record_id;
  const target = process.env.ATTIO_REVIEW_STAGE;
  let moved = false;
  if (target) {
    const from = new Set((process.env.ATTIO_PROMOTE_FROM || process.env.ATTIO_DEAL_STAGE || 'Lead').split(',').map((x) => x.trim().toLowerCase()).filter(Boolean));
    const deal = await attio.openDeal(personId);
    const stage = deal?.values?.stage?.[0]?.status?.title || '';
    if (deal && from.has(stage.toLowerCase()) && stage.toLowerCase() !== target.toLowerCase()) {
      try { await attio.attio(`/objects/deals/records/${deal.id.record_id}`, 'PATCH', { data: { values: { stage: target } } }); moved = true; }
      catch (e) { console.error('[auth] deal stage:', e.message); }
    }
  }
  await attio.addNote('people', personId, 'Portal activity',
    `First offering viewed in the investor portal: ${slug} (${new Date().toISOString().slice(0, 16)}Z).${moved ? ` Deal moved to ${target}.` : ''}`, 'plaintext').catch(() => {});
}

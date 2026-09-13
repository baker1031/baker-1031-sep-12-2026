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
        // A logged-in investor actively reviewing deals → promote their GHL
        // opportunity to "Actively Reviewing" (never demotes later stages).
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
  First offering view → move the investor's GHL opportunity to "Actively
  Reviewing" (Live Opportunities pipeline). Added Sept 3, 2026 per Jerry.
  Promotes only from earlier stages — Leads pipeline (Registered/Cold) and
  Live Opportunities "Intro Call Scheduled" / "Reviewing Opportunities".
  Opportunities already at Actively Reviewing or further along (Completing
  Paperwork, Closing Processing, Closed), and non-open opportunities, are
  left alone. Leaves a note on the contact the first time it moves one.
*/
const GHL_API = 'https://services.leadconnectorhq.com';
const PIPE_LEADS = 'ZSMGJd2FbVFYyL87vXij';
const PIPE_LIVE = '28oMpg0Mb0zYCzJicMXF';
const STAGE_ACTIVE = 'cfeae9e2-d353-41fe-83ef-478339e991ce'; // Actively Reviewing
const PROMOTE_FROM = new Set([
  '8074c14c-6373-4d6a-965a-0860921dacd2', // Leads / Registered
  '299a9b0b-3f40-4f93-b591-5f010f04dc53', // Leads / Cold
  '81017fa0-e8e2-42a9-97f6-bffda8ad5e60', // Live / Intro Call Scheduled
  '355f90f0-6c6b-4cc5-a087-3d71a72bb395', // Live / Reviewing Opportunities
]);

async function moveToActivelyReviewing(email, slug) {
  const key = process.env.GHL_Key || process.env.GHL_API_KEY;
  const loc = process.env.GHL_LOCATION_ID;
  if (!key || !loc || !email) return;
  const h = { Authorization: `Bearer ${key}`, Version: '2021-07-28', 'content-type': 'application/json' };
  const cr = await fetch(`${GHL_API}/contacts/search/duplicate?locationId=${loc}&email=${encodeURIComponent(email)}`, { headers: h });
  const cid = cr.ok ? ((await cr.json()).contact || {}).id : null;
  if (!cid) return;
  const or = await fetch(`${GHL_API}/opportunities/search?location_id=${loc}&contact_id=${cid}&limit=20`, { headers: h });
  const opps = or.ok ? (await or.json()).opportunities || [] : [];
  let moved = false;
  for (const o of opps) {
    if (o.status !== 'open') continue;
    if (![PIPE_LEADS, PIPE_LIVE].includes(o.pipelineId)) continue;
    if (!PROMOTE_FROM.has(o.pipelineStageId)) continue;
    const ur = await fetch(`${GHL_API}/opportunities/${o.id}`, {
      method: 'PUT', headers: h,
      body: JSON.stringify({ pipelineId: PIPE_LIVE, pipelineStageId: STAGE_ACTIVE }),
    });
    if (ur.ok) moved = true;
    else console.error('[auth] opp move', o.id, ur.status, (await ur.text()).slice(0, 120));
  }
  if (moved) {
    await fetch(`${GHL_API}/contacts/${cid}/notes`, {
      method: 'POST', headers: h,
      body: JSON.stringify({ body: `Portal activity: moved opportunity to Actively Reviewing after first offering view (${slug}, ${new Date().toISOString().slice(0, 16)}Z).` }),
    }).catch(() => {});
  }
}

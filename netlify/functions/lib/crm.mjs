/*
  Baker 1031 — reports website activity to the CRM (crm.baker1031.com)

  One shared key, CRM_SHARED_KEY, set on this project and on the CRM project. With it the site tells the CRM
  what a known person did: logged in, viewed an offering (and for how long), downloaded a document,
  registered, booked a call, updated their information, asked for level-2 access. The CRM matches on the
  email address, shows the event in its Activity view and on the person's page, and keeps running totals
  per offering and per document.

  Best effort by design: a slow or unreachable CRM never delays a page or fails a request here. Nothing is
  sent when the key is missing, so the site behaves exactly as before until the key is set.

  Env: CRM_SHARED_KEY (24+ characters, same value on the CRM project), CRM_EVENTS_URL (optional override).
*/
import crypto from 'node:crypto';

const URL_DEFAULT = 'https://crm.baker1031.com/api/events';
export const crmConfigured = () => (process.env.CRM_SHARED_KEY || '').length >= 24;

export async function tellCrm(type, email, data = {}, name = '') {
  const to = String(email || '').trim().toLowerCase();
  if (!crmConfigured() || !to.includes('@')) return false;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 2000);
  try {
    const res = await fetch(process.env.CRM_EVENTS_URL || URL_DEFAULT, {
      method: 'POST',
      signal: ctl.signal,
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + process.env.CRM_SHARED_KEY },
      body: JSON.stringify({ events: [{ type, email: to, name, at: new Date().toISOString(), data }] }),
    });
    return res.ok;
  } catch (e) {
    console.error('[crm]', type, e.name === 'AbortError' ? 'timed out' : e.message);
    return false;
  } finally { clearTimeout(timer); }
}

/*
  Which system is behind the site right now: Attio + Airtable (as built) or the CRM.

  The switch lives in the CRM (Settings -> Website), so moving over and moving back are one click and no deploy. This site asks the CRM, remembers the
  answer for a minute, and falls back to the last answer it had -- or to Attio if it never had one -- when the CRM cannot be reached. CRM_BACKEND, when
  set to "crm" or "attio", overrides all of that.

  crmApi(op, body) is the call itself: POST https://crm.baker1031.com/api/site with the shared key. It never throws; { ok:false } means "could not".
*/
const API_DEFAULT = 'https://crm.baker1031.com/api/site';
export async function crmApi(op, body = {}, { timeoutMs = 8000 } = {}) {
  if (!crmConfigured()) return { ok: false, status: 0, body: {} };
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetch(process.env.CRM_SITE_URL || API_DEFAULT, {
      method: 'POST', signal: ctl.signal,
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + process.env.CRM_SHARED_KEY },
      body: JSON.stringify({ op, ...body }),
    });
    return { ok: res.ok, status: res.status, body: await res.json().catch(() => ({})) };
  } catch (e) {
    console.error('[crm]', op, e.name === 'AbortError' ? 'timed out' : e.message);
    return { ok: false, status: 0, body: {} };
  } finally { clearTimeout(timer); }
}

let modeSeen = { mode: '', at: 0 };
export async function backend() {
  const forced = String(process.env.CRM_BACKEND || '').trim().toLowerCase();
  if (forced === 'crm' || forced === 'attio') return forced;
  if (!crmConfigured()) return 'attio';
  if (modeSeen.mode && Date.now() - modeSeen.at < 60000) return modeSeen.mode;
  const res = await crmApi('mode', {}, { timeoutMs: 2500 });
  if (res.ok && (res.body.mode === 'crm' || res.body.mode === 'attio')) modeSeen = { mode: res.body.mode, at: Date.now() };
  else if (modeSeen.mode) modeSeen.at = Date.now() - 45000; // keep the last answer, and ask again soon
  return modeSeen.mode || 'attio';
}
export const usingCrm = async () => (await backend()) === 'crm';
export const _resetBackend = () => { modeSeen = { mode: '', at: 0 }; }; // tests only

// Constant-time check of the bearer key, for the endpoints the CRM calls on this site.
export function fromCrm(event) {
  if (!crmConfigured()) return false;
  const got = String(event.headers.authorization || event.headers.Authorization || '').replace(/^Bearer\s+/i, '');
  const a = crypto.createHash('sha256').update(got).digest();
  const b = crypto.createHash('sha256').update(process.env.CRM_SHARED_KEY).digest();
  return got.length > 0 && crypto.timingSafeEqual(a, b);
}

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

// Constant-time check of the bearer key, for the endpoints the CRM calls on this site.
export function fromCrm(event) {
  if (!crmConfigured()) return false;
  const got = String(event.headers.authorization || event.headers.Authorization || '').replace(/^Bearer\s+/i, '');
  const a = crypto.createHash('sha256').update(got).digest();
  const b = crypto.createHash('sha256').update(process.env.CRM_SHARED_KEY).digest();
  return got.length > 0 && crypto.timingSafeEqual(a, b);
}

/*
  Baker 1031 — registrations the CRM could not take, kept until it can (Netlify Blobs store "pending-leads")

  lead.mjs sends every registration to the CRM (POST crm.baker1031.com/api/site, op "lead"). When that call fails, the
  registration is written here instead of being dropped or sent anywhere else, and the visitor still sees success.
  lead-retry.mjs runs every 5 minutes, sends each entry to the CRM again and deletes it once the CRM confirms.
  An entry still failing after 24 hours is emailed to Jerry once, raw, so he can enter it by hand (needs
  RESEND_API_KEY). It keeps being retried until 7 days after that email, then it is dropped; without a sent email
  it is never dropped.

  One blob per registration, key "<ms since epoch>-<random>", value:
    { lead, ip, queuedAt, attempts, lastTriedAt, lastError, crsSent, alertedAt }

  The store is passed in, so tests use an in-memory one; in a function, pendingStore(event) returns the real store.
*/
import crypto from 'node:crypto';
import { getStore, connectLambda } from '@netlify/blobs';
import { crmApi } from './crm.mjs';
import { sendViaResend } from './invites.mjs';

export const STORE = 'pending-leads';
export const ALERT_AFTER_MS = 24 * 3600 * 1000;
export const DROP_AFTER_ALERT_MS = 7 * 24 * 3600 * 1000;
const ALERT_TO = () => process.env.LEAD_ALERT_TO || 'jerry@baker1031.com';

let testStore = null;
export const _useStore = (s) => { testStore = s; }; // tests only

// A Lambda-style function (exports.handler) has to hand its event to Blobs first; a v2 function does not.
export function pendingStore(event) {
  if (testStore) return testStore;
  if (event && event.blobs) connectLambda(event);
  return getStore(STORE);
}

export async function queueLead(store, { lead, ip = '', error = '', crsSent = false }) {
  const key = `${Date.now()}-${crypto.randomBytes(6).toString('hex')}`;
  const now = new Date().toISOString();
  await store.setJSON(key, { lead, ip, queuedAt: now, attempts: 1, lastTriedAt: now, lastError: String(error || '').slice(0, 300), crsSent: !!crsSent, alertedAt: null });
  return key;
}

const esc = (s) => String(s ?? '').replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
export function alertEmail(entry, { queued = true } = {}) {
  const l = entry.lead || {};
  const who = [l.firstName, l.lastName].filter(Boolean).join(' ') || l.email || 'unknown';
  const F = "'Helvetica Neue', Helvetica, Arial, sans-serif";
  const head = queued ? 'A website registration has not reached the CRM for 24 hours' : 'A website registration did not reach the CRM and could not be kept for a retry';
  const what = queued
    ? `The CRM has refused or not answered ${esc(entry.attempts)} time(s); the last error was: ${esc(entry.lastError || 'no answer')}. The site keeps retrying every 5 minutes. To be safe, enter this person in the CRM by hand; if a retry lands later, the CRM matches them by email and does not create a second contact.`
    : `The CRM call failed (${esc(entry.lastError || 'no answer')}) and the pending-leads store was unavailable, so nothing will retry this one. Please enter this person in the CRM by hand.`;
  const html = `<!doctype html><html><body style="margin:0;padding:24px;background:#FDFBF7;font-family:${F};color:#23232A;">
<p style="font-size:15px;font-weight:bold;margin:0 0 8px;">${head}</p>
<p style="font-size:13px;line-height:20px;margin:0 0 14px;">${esc(who)} &lt;${esc(l.email)}&gt; registered at baker1031.com on ${esc(entry.queuedAt)}. ${what}
${entry.crsSent ? 'The Form CRS receipt was sent from the website when they registered.' : 'No Form CRS receipt has been confirmed for this registration.'}</p>
<p style="font-size:12px;margin:0 0 6px;color:#666666;">The registration exactly as submitted (visitor IP ${esc(entry.ip || 'unavailable')}):</p>
<pre style="font-size:12px;line-height:17px;background:#F5F1E9;padding:12px;white-space:pre-wrap;word-break:break-word;">${esc(JSON.stringify(l, null, 2))}</pre>
</body></html>`;
  return { subject: `Registration not in the CRM - ${who}`, html };
}

/*
  One pass over the store. Returns what happened, for the function log. `send` and `alert` are injectable for tests.
*/
export async function retryPending(store, { now = Date.now(), send = (e) => crmApi('lead', { lead: e.lead, ip: e.ip }, { timeoutMs: 9000 }),
  alert = (e) => { const m = alertEmail(e); return sendViaResend(ALERT_TO(), m.subject, m.html, 'Baker 1031 Website <jerry@baker1031.com>'); }, budgetMs = 20000 } = {}) {
  const out = { checked: 0, delivered: 0, failed: 0, alerted: 0, dropped: 0, left: 0 };
  const started = Date.now();
  const { blobs = [] } = await store.list();
  for (const { key } of blobs.sort((a, b) => (a.key < b.key ? -1 : 1))) {
    if (Date.now() - started > budgetMs) { out.left++; continue; }
    const entry = await store.get(key, { type: 'json' });
    if (!entry || !entry.lead) { await store.delete(key); continue; }
    out.checked++;
    const res = await Promise.resolve().then(() => send(entry)).catch((e) => ({ ok: false, status: 0, body: { error: e.message } }));
    if (res && res.ok && res.body && res.body.ok) {
      await store.delete(key); out.delivered++;
      console.log(`[lead-retry] delivered ${entry.lead.email} to the CRM after ${entry.attempts} failed attempt(s)`);
      continue;
    }
    out.failed++;
    entry.attempts = (entry.attempts || 0) + 1;
    entry.lastTriedAt = new Date(now).toISOString();
    entry.lastError = `CRM ${res?.status || 'unreachable'}${res?.body?.error ? ': ' + String(res.body.error).slice(0, 200) : ''}`;
    const age = now - (Date.parse(entry.queuedAt) || now);
    if (!entry.alertedAt && age >= ALERT_AFTER_MS) {
      if (await Promise.resolve(alert(entry)).catch((e) => { console.error('[lead-retry] alert email:', e.message); return false; })) {
        entry.alertedAt = new Date(now).toISOString(); out.alerted++;
      } else console.error(`[lead-retry] ${entry.lead.email} has failed for 24 h and could not be emailed (is RESEND_API_KEY set?) — kept for retry`);
    }
    if (entry.alertedAt && now - Date.parse(entry.alertedAt) >= DROP_AFTER_ALERT_MS) {
      await store.delete(key); out.dropped++;
      console.error(`[lead-retry] gave up on ${entry.lead.email} (emailed ${entry.alertedAt}); registration: ${JSON.stringify(entry.lead)}`);
      continue;
    }
    await store.setJSON(key, entry);
  }
  return out;
}

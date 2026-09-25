/*
  Baker 1031 — one-click opt-out for automated 1031 deadline reminders.

  GET /api/reminders-off?rid=<Airtable record id>&sig=<HMAC>
  sig = HMAC-SHA256('remoff:' + rid, SESSION_SECRET), base64url, first 32 chars
  (generated per-email by deadline-reminders.mjs — personal, not guessable).

  Sets the row's "Reminders Off" checkbox and shows a small confirmation page.
  Re-enabling: uncheck the box in Airtable (or the investor asks Jerry).
*/

import crypto from 'node:crypto';
import { crmApi, usingCrm } from './lib/crm.mjs';

const AT_BASE = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ';
const AT_TABLE = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';

export const offSig = (rid) => crypto.createHmac('sha256', process.env.SESSION_SECRET || '')
  .update('remoff:' + rid).digest('base64url').slice(0, 32);

const page = (title, body) => ({
  statusCode: 200,
  headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' },
  body: `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>${title} — Baker 1031 Investments</title></head>
<body style="margin:0;background:#F4F5F7;font-family:'Helvetica Neue',Arial,sans-serif;">
<div style="max-width:520px;margin:80px auto;padding:44px 40px;background:#FFFFFF;border-top:3px solid #266EEF;">
<div style="font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#266EEF;margin-bottom:18px;">Baker 1031 Investments</div>
<h1 style="font-size:24px;font-weight:400;color:#202022;margin:0 0 14px;">${title}</h1>
<div style="font-size:15px;line-height:1.7;color:rgba(32,32,34,.8);">${body}</div>
</div></body></html>`,
});

export const handler = async (event) => {
  const q = event.queryStringParameters || {};
  const rid = String(q.rid || '');
  const sig = String(q.sig || '');
  const DONE = ['Reminders stopped', 'Done — you won’t receive any more automated deadline reminders from me. Your portal access and everything else stays exactly as it was. If you change your mind, just reply to any of my emails and I’ll turn them back on. —Jerry'];
  const BAD = ['Link not valid', 'This link doesn’t check out. If you were trying to stop reminder emails, just reply to the email and I’ll take care of it. —Jerry'];
  const OOPS = ['Something went wrong', 'I couldn’t update your preference just now. Reply to the reminder email and I’ll switch it off by hand. —Jerry'];

  // A link from a reminder the CRM sent (?cid=...): the CRM signed it and the CRM checks it.
  if (q.cid) {
    if (!/^[A-Za-z0-9_-]{6,80}$/.test(String(q.cid)) || !sig || !(await usingCrm())) return page(...BAD);
    const r = await crmApi('reminders_off', { cid: String(q.cid), sig: sig.slice(0, 80) });
    return r.ok ? page(...DONE) : r.status === 403 || r.status === 404 ? page(...BAD) : page(...OOPS);
  }
  if (!/^rec[A-Za-z0-9]{14}$/.test(rid) || !sig) return page('Link not valid', 'This link is missing information. If you were trying to stop reminder emails, just reply to the email and I’ll take care of it. —Jerry');
  const want = Buffer.from(offSig(rid));
  const got = Buffer.from(sig);
  if (want.length !== got.length || !crypto.timingSafeEqual(want, got)) {
    return page('Link not valid', 'This link doesn’t check out. If you were trying to stop reminder emails, just reply to the email and I’ll take care of it. —Jerry');
  }
  // A link from a reminder sent before the move, with the site now on the CRM: checked above, switched off in the CRM.
  if (await usingCrm()) {
    const r = await crmApi('reminders_off', { rid, legacy: true });
    return r.ok ? page(...DONE) : r.status === 404 ? page(...BAD) : page(...OOPS);
  }
  try {
    const r = await fetch(`https://api.airtable.com/v0/${AT_BASE}/${AT_TABLE}/${rid}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${process.env.AIRTABLE_TOKEN}`, 'content-type': 'application/json' },
      body: JSON.stringify({ fields: { 'Reminders Off': true } }),
    });
    if (!r.ok) throw new Error(`Airtable ${r.status}`);
  } catch (e) {
    console.error('[reminders-off]', e.message);
    return page('Something went wrong', 'I couldn’t update your preference just now. Reply to the reminder email and I’ll switch it off by hand. —Jerry');
  }
  return page('Reminders stopped', 'Done — you won’t receive any more automated deadline reminders from me. Your portal access and everything else stays exactly as it was. If you change your mind, just reply to any of my emails and I’ll turn them back on. —Jerry');
};

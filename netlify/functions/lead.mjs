/*
  Baker 1031 — registration intake (POST /api/lead), delivered to Attio:
    Person  — upserted by email (name, email, phone) + any matching custom attributes
    Note    — the full submission, human-readable
    Deal    — "Last, First - 1031|Cash - Role", stage ATTIO_DEAL_STAGE (default "Lead"),
              value = estimated commission (equity × 0.9 × 0.05), linked to the person
    List    — optional (ATTIO_LIST)

  Env: ATTIO_API_KEY (required). Optional: ATTIO_DEAL_OWNER, ATTIO_DEAL_STAGE, ATTIO_DEALS=off, ATTIO_LIST.
  Everything else (the Form CRS receipt, the automatic scheduling / fix-your-info emails) runs regardless of
  CRM delivery; a CRM failure is logged, never shown to the visitor.
*/
import crypto from 'node:crypto';
import { accreditedSignal, inviteVariant, noticeKind, buildInvite, buildNotice, sendViaResend, STATUS_FIELD } from './lib/invites.mjs';
import * as attio from './lib/attio.mjs';
import { commissionValue, dealName, addDays, personPairs, dealPairs } from './lib/lead-shape.mjs';

const json = (status, body) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
});

const LABELS = {
  role: 'Role', path: 'Path', fit: 'Exchange fit', objectives: 'Objectives', equity: 'Exchange equity', debt: 'Replacement debt',
  saleDate: 'Sale date', saleDateStatus: 'Sale date is', marital: 'Marital status', netWorth: 'Net worth (ex. residence)',
  income: 'Household income', accreditedLikely: 'Accredited on the ranges given', phoneRegion: 'Phone region',
  submittedAt: 'Acknowledged at', source: 'Form',
};
function summarize(lead) {
  const skip = new Set(['firstName', 'lastName', 'email', 'phone', 'acknowledgments']);
  const money = (n) => '$' + Math.round(Number(n)).toLocaleString('en-US');
  const lines = [];
  for (const [k, v] of Object.entries(lead)) {
    if (skip.has(k) || v == null || v === '' || (Array.isArray(v) && !v.length)) continue;
    let val = Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v);
    if ((k === 'equity' || k === 'debt' || k === 'amount') && !Number.isNaN(Number(v))) val = money(v);
    if (k === 'saleDate' && lead.saleDate) val += ` (45-day: ${addDays(lead.saleDate, 45)}, 180-day: ${addDays(lead.saleDate, 180)})`;
    lines.push(`- **${LABELS[k] || k}:** ${val}`);
  }
  const acks = lead.acknowledgments?.list || [];
  if (acks.length) lines.push(`- **Acknowledged:** ${acks.join(', ')}`);
  return `Registration at baker1031.com — ${lead.firstName || ''} ${lead.lastName || ''} <${lead.email}>${lead.phone ? ', ' + lead.phone : ''}\n\n${lines.join('\n')}`;
}

// ---- delivery to Attio -----------------------------------------------------
async function deliverToAttio(lead) {
  const person = await attio.upsertPerson(lead);
  const personId = person.id.record_id;

  // personal correction link (update-my-info), stored on the person when an "Update Link" attribute exists
  const base = process.env.URL || 'https://baker1031.com';
  const sig = crypto.createHmac('sha256', process.env.SESSION_SECRET || '').update('myinfo:' + personId).digest('hex').slice(0, 32);
  const updateUrl = `${base}/update-my-info/?cid=${personId}&sig=${sig}`;
  await attio.setValues('people', personId, personPairs(lead, { 'Update Link': updateUrl }));

  await attio.addNote('people', personId, `Website registration — ${new Date().toISOString().slice(0, 10)}`, summarize(lead))
    .catch((e) => console.error('[lead] note:', e.message));

  await attio.createDeal({ name: dealName(lead), value: commissionValue(lead), personId, pairs: dealPairs(lead) });
  await attio.addToList(personId);

  // automatic email: scheduling invite for qualified leads, or a fix-your-info notice for leads that miss
  // the residency / accreditation requirements. A repeat submission never re-sends: the "Intro Invite
  // Status" attribute (if it exists in Attio) remembers what went out.
  try {
    const first = lead.firstName || 'there';
    const variant = inviteVariant(lead);
    const kind = noticeKind(lead);
    let prior = '';
    try {
      const flat = attio.flatValues(await attio.getPerson(personId));
      const attrs = await attio.attributes('people');
      const sf = attrs.find((a) => a.title.toLowerCase() === STATUS_FIELD.toLowerCase());
      if (sf) prior = String(flat[sf.slug] || '');
    } catch { /* best effort */ }

    let msg = null, status = null;
    if (variant && !prior.startsWith('invited')) {
      msg = buildInvite(variant, first, base);
      status = `invited ${new Date().toISOString().slice(0, 16)}Z (${variant})`;
    } else if (kind && !prior.startsWith('invited') && !prior.startsWith(`notice-${kind}`)) {
      msg = buildNotice(kind, first, updateUrl);
      status = `notice-${kind} ${new Date().toISOString().slice(0, 16)}Z`;
    }
    if (msg && await sendViaResend(lead.email, msg.subject, msg.html)) {
      await attio.setValues('people', personId, [[STATUS_FIELD, status]]);
    }
  } catch (e) { console.error('[lead] email:', e.message); }

  return 'attio';
}

// ---- Form CRS delivery receipt ------------------------------------------
// Every completed registration requires the visitor to acknowledge reviewing Aurora Securities' Form CRS.
// This sends a compliance receipt of that acknowledgment to crs@baker1031.com with the submission
// details and the visitor's IP address.
const CRS_TO = process.env.CRS_RECEIPT_TO || 'crs@baker1031.com';

async function sendCrsReceipt(lead, ip) {
  const now = new Date();
  const utc = now.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  const pacific = now.toLocaleString('en-US', { timeZone: 'America/Los_Angeles', dateStyle: 'medium', timeStyle: 'medium' }) + ' PT';
  const row = (k, v) => `<tr><td style="padding:6px 14px 6px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#666;white-space:nowrap;vertical-align:top;">${k}</td><td style="padding:6px 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#243856;">${v}</td></tr>`;
  const esc = (s) => String(s ?? '').replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
  const html = `<!doctype html><html><body style="margin:0;padding:24px 20px;background:#ffffff;">
<div style="max-width:640px;">
  <p style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:21px;color:#243856;margin:0 0 4px;font-weight:bold;">Form CRS delivery receipt</p>
  <p style="font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:19px;color:#666;margin:0 0 16px;">The person below completed the registration form at baker1031.com and acknowledged reviewing Aurora Securities&rsquo; Form CRS as part of the final acknowledgments.</p>
  <table cellpadding="0" cellspacing="0" border="0">
    ${row('Name', esc(`${lead.firstName || ''} ${lead.lastName || ''}`.trim()))}
    ${row('Email', esc(lead.email))}
    ${row('Phone', esc(lead.phone || '—'))}
    ${row('Date / time', `${utc}<br>${pacific}`)}
    ${row('IP address', esc(ip || 'unavailable'))}
    ${row('Form submitted at', esc(lead.submittedAt || '—'))}
  </table>
  <p style="font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:16px;color:#999;margin:18px 0 0;">Automated compliance record from the baker1031.com registration form. Retain per books-and-records policy.</p>
</div>
</body></html>`;
  const who = [lead.lastName, lead.firstName].filter(Boolean).join(', ') || lead.email;
  return sendViaResend(CRS_TO, `Form CRS receipt - ${who}`, html, 'Baker 1031 Website <jerry@baker1031.com>');
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  let lead = {};
  try { lead = JSON.parse(event.body || '{}'); } catch { return json(400, { error: 'bad json' }); }

  const email = String(lead.email || '').trim();
  if (!lead.firstName || !email.includes('@')) return json(400, { error: 'missing required fields' });
  if (JSON.stringify(lead).length > 50000) return json(413, { error: 'payload too large' });

  let via = null;
  if (attio.configured()) {
    try { via = await deliverToAttio(lead); }
    catch (e) { console.error('[lead] Attio delivery failed:', e.message); }
  }
  if (!via) console.log('[lead] not delivered to CRM (ATTIO_API_KEY missing or Attio rejected the request) — submission from', email);

  // Compliance receipt — independent of CRM delivery success.
  try {
    const ip = event.headers['x-nf-client-connection-ip']
      || String(event.headers['x-forwarded-for'] || '').split(',')[0].trim();
    await sendCrsReceipt(lead, ip);
  } catch (e) { console.error('[lead] crs receipt:', e.message); }

  return json(200, { ok: true, via });
};

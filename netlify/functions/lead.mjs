/*
  Baker 1031 — registration intake (POST /api/lead)

  The CRM is the only destination. Every registration goes to the CRM (POST crm.baker1031.com/api/site, op "lead"),
  which creates or matches the contact, opens or refreshes the deal, notes the answers, sends the scheduling or
  fix-your-answers email and the Form CRS receipt. investors.baker1031.com manages portal accounts on top of that data.

  If the CRM cannot take it (down, slow, refused), the registration is kept in the Netlify Blobs store "pending-leads"
  and lead-retry.mjs re-sends it every 5 minutes until the CRM confirms; after 24 hours of failures it is emailed to
  Jerry (lib/pending-leads.mjs). The Form CRS receipt is then sent from here straight away. The visitor sees success
  either way. Nothing goes to Attio, Airtable or GoHighLevel on this path.

  Emergency only (CRM_BACKEND=attio): the old Attio delivery below — person, note, deal "Last, First - 1031|Cash - Role"
  at ATTIO_DEAL_STAGE, optional ATTIO_LIST — with ATTIO_API_KEY, plus a site.signup event to the CRM.
*/
import crypto from 'node:crypto';
import { accreditedSignal, inviteVariant, noticeKind, buildInvite, buildNotice, sendViaResend, STATUS_FIELD } from './lib/invites.mjs';
import * as attio from './lib/attio.mjs';
import { tellCrm, crmApi, usingCrm } from './lib/crm.mjs';
import { pendingStore, queueLead, alertEmail } from './lib/pending-leads.mjs';
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

// ---- delivery to Attio (CRM_BACKEND=attio only) -------------------------------
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
  const F = "'Helvetica Neue', Helvetica, Arial, sans-serif";
  const base = (process.env.URL || 'https://baker1031.com').replace(/\/$/, '');
  const row = (k, v) => `<tr><td style="padding:6px 14px 6px 0;font-family:${F};font-size:13px;color:#666666;white-space:nowrap;vertical-align:top;">${k}</td><td style="padding:6px 0;font-family:${F};font-size:13px;color:#202022;">${v}</td></tr>`;
  const esc = (s) => String(s ?? '').replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
  const html = `<!doctype html><html><body style="margin:0;padding:0;background:#FFFFFF;">
<div style="max-width:620px;margin:0;padding:28px 20px;">
  <table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse:collapse;margin:0 0 26px 0"><tbody>
  <tr><td style="padding:0 0 14px 0"><img src="${base}/assets/media/logo.png" alt="Baker 1031 Investments" width="180" height="51" style="display:block;width:180px;height:51px;border:0;outline:none;text-decoration:none"></td></tr>
  <tr><td style="padding:0;border-top:2px solid #266EEF;font-size:0;line-height:0">&nbsp;</td></tr>
  </tbody></table>
  <p style="font-family:${F};font-size:15px;line-height:24px;color:#202022;margin:0 0 4px;font-weight:bold;">Form CRS delivery receipt</p>
  <p style="font-family:${F};font-size:13px;line-height:20px;color:#666666;margin:0 0 18px;">The person below completed the registration form at baker1031.com and acknowledged reviewing Aurora Securities&rsquo; Form CRS as part of the final acknowledgments.</p>
  <table cellpadding="0" cellspacing="0" border="0">
    ${row('Name', esc(`${lead.firstName || ''} ${lead.lastName || ''}`.trim()))}
    ${row('Email', esc(lead.email))}
    ${row('Phone', esc(lead.phone || '—'))}
    ${row('Date / time', `${utc}<br>${pacific}`)}
    ${row('IP address', esc(ip || 'unavailable'))}
    ${row('Form submitted at', esc(lead.submittedAt || '—'))}
  </table>
  <p style="font-family:${F};font-size:11px;line-height:17px;color:#767676;margin:20px 0 0;">Automated compliance record from the baker1031.com registration form. Retain per books-and-records policy.</p>
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

  const ip = event.headers['x-nf-client-connection-ip']
    || String(event.headers['x-forwarded-for'] || '').split(',')[0].trim();

  let via = null, crsSent = false, receiptTried = false;
  const receipt = async () => { receiptTried = true; try { return await sendCrsReceipt(lead, ip); } catch (e) { console.error('[lead] crs receipt:', e.message); return false; } };

  if (await usingCrm()) {
    // The CRM does all of it, including the Form CRS receipt, and says whether that went.
    const res = await crmApi('lead', { lead, ip }, { timeoutMs: 9000 });
    if (res.ok && res.body.ok) { via = 'crm'; crsSent = !!res.body.crs; }
    else {
      const error = `CRM ${res.status || 'unreachable'}${res.body && res.body.error ? ': ' + String(res.body.error).slice(0, 200) : ''}`;
      // The compliance receipt cannot wait for the retry: it goes from here now.
      crsSent = await receipt();
      try {
        const key = await queueLead(pendingStore(event), { lead, ip, error, crsSent });
        via = 'queued';
        console.error(`[lead] ${error} — kept as pending-leads/${key}; lead-retry re-sends it every 5 minutes`);
      } catch (e) {
        // Last resort: the store is unavailable too. The function log keeps the registration and Jerry gets it now.
        console.error('[lead] CRM delivery failed and the registration could not be queued:', error, '/', e.message, JSON.stringify({ lead, ip }));
        const m = alertEmail({ lead, ip, queuedAt: new Date().toISOString(), attempts: 1, lastError: `${error}; not queued: ${e.message}`, crsSent }, { queued: false });
        await sendViaResend(process.env.LEAD_ALERT_TO || 'jerry@baker1031.com', m.subject, m.html, 'Baker 1031 Website <jerry@baker1031.com>')
          .catch((err) => console.error('[lead] alert email:', err.message));
      }
    }
  } else {
    // CRM_BACKEND=attio: the old path, kept for an emergency switch-back.
    if (attio.configured()) {
      try { via = await deliverToAttio(lead); }
      catch (e) { console.error('[lead] Attio delivery failed:', e.message); }
    }
    if (!via) console.log('[lead] not delivered to a CRM — submission from', email);
    // The CRM still hears about the registration: someone new becomes a lead there.
    await tellCrm('site.signup', email, { firstName: lead.firstName || '', lastName: lead.lastName || '', phone: lead.phone || '', role: lead.role || '', path: lead.path || '',
      saleDate: lead.saleDate || '', equity: Number(lead.equity) || 0, debt: Number(lead.debt) || 0 }, [lead.firstName, lead.lastName].filter(Boolean).join(' '));
  }

  // Compliance receipt — independent of delivery. Sent from here whenever the CRM did not confirm it sent it.
  if (!crsSent && !receiptTried) await receipt();

  return json(200, { ok: true, via });
};

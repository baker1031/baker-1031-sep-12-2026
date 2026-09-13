/*
  Baker 1031 — request-access intake (POST /api/lead)
  Delivers each submission to GoHighLevel:
    Contact  — identity + person-level custom fields (profile, preferences, risk, acknowledgments)
    Note     — the full submission, human-readable
    Opportunity — pipeline "Leads", stage "Registered" (overridable via GHL_PIPELINE_ID/GHL_STAGE_ID);
                  name "Last, First - 1031|1033|Cash - Role";
                  value = estimated commission (equity or amount × 0.9 × 0.05);
                  deal-level custom fields (dates, deadlines, equity/debt, fit, objectives)

  Env: GHL_Key (v2 "pit-" private-integration token) + GHL_LOCATION_ID.
       Optional: GHL_WEBHOOK_URL (takes priority), GHL_PIPELINE_ID, GHL_STAGE_ID.
*/

import crypto from 'node:crypto';
import { accreditedSignal, inviteVariant, noticeKind, buildInvite, buildNotice, sendViaResend, hasAppointment, STATUS_FIELD } from './lib/invites.mjs';

const API = 'https://services.leadconnectorhq.com';

const json = (status, body) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
});

// ---- commission + naming -------------------------------------------------
function commissionValue(lead) {
  const base = lead.path === 'exchange' ? lead.equity : lead.amount;
  return base ? Math.round(base * 0.9 * 0.05) : 0;
}

function dealType(lead) {
  if (lead.path !== 'exchange') return 'Cash';
  const objs = lead.objectives || [];
  return objs.includes('Planning a 1033 exchange') && !objs.includes('Planning a 1031 exchange') ? '1033' : '1031';
}

// "Last Name, First Name - 1031/1033/Cash - Role"
function opportunityName(lead) {
  const who = [lead.lastName, lead.firstName].filter(Boolean).join(', ') || lead.email;
  return [who, dealType(lead), lead.role || ''].filter(Boolean).join(' - ');
}

// ---- helpers -------------------------------------------------------------
function addDays(iso, days) {
  const d = new Date(iso + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}


function summarize(lead) {
  const skip = new Set(['firstName', 'lastName', 'email', 'phone']);
  const lines = [];
  for (const [k, v] of Object.entries(lead)) {
    if (skip.has(k) || v == null || v === '' || (Array.isArray(v) && !v.length)) continue;
    lines.push(`${k}: ${Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : v}`);
  }
  return 'Request-access submission (baker1031.com)\n\n' + lines.join('\n');
}

// ---- GHL metadata (cached per warm container) ----------------------------
let fieldCache = null;   // name(lower) -> { id, model }
let pipeCache = null;    // { pipelineId, stageId }

async function loadFields(headers, loc) {
  if (fieldCache) return fieldCache;
  const r = await fetch(`${API}/locations/${loc}/customFields?model=all`, { headers });
  if (!r.ok) throw new Error(`fields ${r.status}`);
  fieldCache = {};
  for (const f of (await r.json()).customFields || []) {
    fieldCache[`${f.model || 'contact'}|${f.name.toLowerCase()}`] = f.id;
  }
  return fieldCache;
}

async function resolvePipeline(headers, loc) {
  if (process.env.GHL_PIPELINE_ID) {
    return { pipelineId: process.env.GHL_PIPELINE_ID, stageId: process.env.GHL_STAGE_ID || null };
  }
  if (pipeCache) return pipeCache;
  const r = await fetch(`${API}/opportunities/pipelines?locationId=${loc}`, { headers });
  if (!r.ok) throw new Error(`pipelines ${r.status}`);
  const pipes = (await r.json()).pipelines || [];
  const leads = pipes.find((p) => p.name.toLowerCase() === 'leads');
  if (!leads) throw new Error('pipeline "Leads" not found');
  const reg = (leads.stages || []).find((s) => s.name.toLowerCase() === 'registered');
  pipeCache = { pipelineId: leads.id, stageId: reg ? reg.id : null };
  return pipeCache;
}

function fieldValues(map, model, pairs) {
  const out = [];
  for (const [name, value] of pairs) {
    if (value == null || value === '' || (Array.isArray(value) && !value.length)) continue;
    const id = map[`${model}|${name.toLowerCase()}`];
    if (id) out.push({ id, field_value: value });
  }
  return out;
}

// ---- delivery ------------------------------------------------------------
async function deliverViaApi(key, lead) {
  const loc = process.env.GHL_LOCATION_ID;
  if (!loc) throw new Error('GHL_LOCATION_ID required');
  const headers = { Authorization: `Bearer ${key}`, Version: '2021-07-28', 'content-type': 'application/json' };
  const fields = await loadFields(headers, loc).catch((e) => { console.error('[lead] field map:', e.message); return {}; });

  // 1. contact upsert with person-level fields
  const contactFields = fieldValues(fields, 'contact', [
    ['Role (This Transaction)', lead.role],
    ['DST Familiarity', lead.familiarity],
    ['Marital Status', lead.marital],
    ['Net Worth Range', lead.netWorth],
    ['Household Income', lead.income],
    ['RE Experience', lead.reExperience],
    ['Risk Comfort', lead.riskComfort],
    ['Liquidity Need', lead.liquidityNeed],
    ['Investment Horizon', lead.horizon],
    ['Decline Response', lead.declineResponse],
    ['Private Placement Experience', lead.ppExperience],
    ['Asset Class Preferences', lead.assets],
    ['Region Preferences', lead.regions],
    ['Market Preferences', lead.markets],
    ['Feature Interests', lead.features],
    ['Accredited Signal', accreditedSignal(lead)],
    ['Acknowledgments Timestamp', lead.submittedAt],
    ['SMS Consent', lead.smsConsent ? `Granted ${lead.submittedAt || ''} (${lead.smsConsentLanguageVersion || ''})`.trim() : null],
    ['SMS Marketing Consent', lead.smsMarketingConsent ? `Granted ${lead.submittedAt || ''} (${lead.smsConsentLanguageVersion || ''})`.trim() : null],
  ]);
  const up = await fetch(`${API}/contacts/upsert`, {
    method: 'POST', headers,
    body: JSON.stringify({
      locationId: loc, firstName: lead.firstName, lastName: lead.lastName,
      email: lead.email, phone: lead.phone, state: lead.state || undefined, source: 'website request-access',
      tags: ['request-access', lead.path === 'exchange' ? '1031-exchange' : 'cash-investor',
        ...(lead.smsConsent ? ['sms-consent'] : []),
        ...(lead.smsMarketingConsent ? ['sms-marketing-consent'] : [])],
      customFields: contactFields,
    }),
  });
  if (!up.ok) throw new Error(`GHL upsert ${up.status}: ${(await up.text()).slice(0, 200)}`);
  const contactId = (await up.json()).contact?.id;
  if (!contactId) return 'api-v2';

  // 1b. personal correction link, stored on the contact for {{contact.update_link}} merge use
  const base = process.env.URL || 'https://baker1031.com';
  const sig = crypto.createHmac('sha256', process.env.SESSION_SECRET || '').update('myinfo:' + contactId).digest('hex').slice(0, 32);
  const updateUrl = `${base}/update-my-info/?cid=${contactId}&sig=${sig}`;
  try {
    const linkField = fields['contact|update link'];
    if (linkField) {
      await fetch(`${API}/contacts/${contactId}`, {
        method: 'PUT', headers,
        body: JSON.stringify({ customFields: [{ id: linkField, field_value: updateUrl }] }),
      });
    }
  } catch (e) { console.error('[lead] update-link:', e.message); }

  // 2. note with the complete submission
  await fetch(`${API}/contacts/${contactId}/notes`, {
    method: 'POST', headers, body: JSON.stringify({ body: summarize(lead).slice(0, 5000) }),
  }).catch((e) => console.error('[lead] note failed:', e.message));

  // 3. opportunity in Leads / Registered
  try {
    const { pipelineId, stageId } = await resolvePipeline(headers, loc);
    const oppFields = fieldValues(fields, 'opportunity', [
      ['Sale Date', lead.saleDate],
      ['45-Day Deadline', lead.saleDate ? addDays(lead.saleDate, 45) : null],
      ['180-Day Deadline', lead.saleDate ? addDays(lead.saleDate, 180) : null],
      ['Exchange Equity', lead.equity],
      ['Replacement Debt', lead.debt],
      ['Exchange Fit', lead.fit],
      ['Objectives', lead.objectives],
      ['Cash Amount', lead.amount],
      ['Primary Use', lead.use],
      ['Cash Horizon', lead.cashHorizon],
    ]);
    const opp = {
      pipelineId, locationId: loc, contactId, status: 'open',
      name: opportunityName(lead),
      monetaryValue: commissionValue(lead),
      customFields: oppFields,
    };
    if (stageId) opp.pipelineStageId = stageId;
    const or = await fetch(`${API}/opportunities/`, { method: 'POST', headers, body: JSON.stringify(opp) });
    if (!or.ok) console.error('[lead] opportunity failed', or.status, (await or.text()).slice(0, 200));
  } catch (e) { console.error('[lead] opportunity:', e.message); }

  // 4. automatic email: scheduling invite for qualified leads, or a fix-your-info
  //    notice for leads that miss the residency/accreditation requirements.
  try {
    const first = lead.firstName || 'there';
    const variant = inviteVariant(lead);
    const kind = noticeKind(lead);

    // Duplicate protection: a re-submitted form never re-sends an email the
    // contact already got. "invited …" blocks everything automatic; a repeat
    // of the same notice is also suppressed. (Same rules as the update flow.)
    let prior = '';
    try {
      const cr = await fetch(`${API}/contacts/${contactId}`, { headers });
      if (cr.ok) {
        const c = (await cr.json()).contact || {};
        const sfId = fields[`contact|${STATUS_FIELD.toLowerCase()}`];
        for (const v of c.customFields || []) {
          if (v.id === sfId) prior = String(v.value ?? v.field_value ?? v.fieldValue ?? '');
        }
      }
    } catch { /* best effort */ }

    let msg = null, status = null;
    if (variant) {
      const booked = prior.startsWith('invited') || await hasAppointment(headers, contactId);
      if (!booked) {
        msg = buildInvite(variant, first, base);
        status = `invited ${new Date().toISOString().slice(0, 16)}Z (${variant})`;
      }
    } else if (kind && !prior.startsWith('invited') && !prior.startsWith(`notice-${kind}`)) {
      msg = buildNotice(kind, first, updateUrl);
      status = `notice-${kind} ${new Date().toISOString().slice(0, 16)}Z`;
    }
    if (msg && await sendViaResend(lead.email, msg.subject, msg.html)) {
      const sf = fields[`contact|${STATUS_FIELD.toLowerCase()}`];
      if (sf) {
        await fetch(`${API}/contacts/${contactId}`, {
          method: 'PUT', headers,
          body: JSON.stringify({ customFields: [{ id: sf, field_value: status }] }),
        }).catch(() => {});
      }
    }
  } catch (e) { console.error('[lead] email:', e.message); }

  return 'api-v2';
}

// ---- Form CRS delivery receipt ------------------------------------------
// Every completed request-access form requires the visitor to acknowledge
// downloading Aurora Securities' Form CRS (step 9). This sends a compliance
// receipt of that acknowledgment to crs@baker1031.com with the submission
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
  <p style="font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:19px;color:#666;margin:0 0 16px;">The person below completed the request-access form at baker1031.com and acknowledged downloading and reviewing Aurora Securities&rsquo; Form CRS as part of the final acknowledgments.</p>
  <table cellpadding="0" cellspacing="0" border="0">
    ${row('Name', esc(`${lead.firstName || ''} ${lead.lastName || ''}`.trim()))}
    ${row('Email', esc(lead.email))}
    ${row('Phone', esc(lead.phone || '—'))}
    ${row('Date / time', `${utc}<br>${pacific}`)}
    ${row('IP address', esc(ip || 'unavailable'))}
    ${row('Form submitted at', esc(lead.submittedAt || '—'))}
  </table>
  <p style="font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:16px;color:#999;margin:18px 0 0;">Automated compliance record from the baker1031.com request-access form. Retain per books-and-records policy.</p>
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
  const raw = JSON.stringify(lead);
  if (raw.length > 50000) return json(413, { error: 'payload too large' });

  let via = null;
  const webhook = process.env.GHL_WEBHOOK_URL;
  const key = process.env.GHL_Key || process.env.GHL_API_KEY;

  if (webhook) {
    try {
      const res = await fetch(webhook, { method: 'POST', headers: { 'content-type': 'application/json' }, body: raw });
      if (res.ok) via = 'webhook'; else console.error('[lead] webhook status', res.status);
    } catch (e) { console.error('[lead] webhook failed:', e.message); }
  }
  if (!via && key) {
    try { via = await deliverViaApi(key, lead); }
    catch (e) { console.error('[lead] api delivery failed:', e.message); }
  }
  if (!via) console.log('[lead] not delivered to CRM (no working GHL config) — submission from', email);

  // Compliance receipt — independent of CRM delivery success.
  try {
    const ip = event.headers['x-nf-client-connection-ip']
      || String(event.headers['x-forwarded-for'] || '').split(',')[0].trim();
    await sendCrsReceipt(lead, ip);
  } catch (e) { console.error('[lead] crs receipt:', e.message); }


  return json(200, { ok: true, via });
};

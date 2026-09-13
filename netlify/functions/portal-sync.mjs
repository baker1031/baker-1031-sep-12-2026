/*
  Baker 1031 — GHL "Portal Access" → Airtable "Investor Access" sync
  (POST /api/portal-sync, called by a GoHighLevel workflow webhook when the
  Portal Access custom field changes)

  Portal Access = Yes → upsert the investor row in Airtable with Access Level
                        "Approved" (creates the row with name/email/start date
                        if it doesn't exist) — the person can log in. Also
                        writes the exchange timeline (Start Date, ID Period
                        Expiration, 1031 Expiration) from the GHL contact's
                        Closing Date / 45-Day / 180-Day fields, falling back
                        to the newest opportunity's Sale Date / deadlines.
  Portal Access = No  → set the row's Access Level to "Revoked" — login stops
                        working immediately (auth.mjs re-verifies every page
                        load), while Deals Reviewed history is preserved.

  Auth: requests must carry the shared key (header x-portal-key, or ?key=).
  Env:  PORTAL_SYNC_KEY, GHL_Key, GHL_LOCATION_ID, AIRTABLE_TOKEN,
        ACCESS_BASE_ID (default appiKLSyAUmP0h8cJ), ACCESS_TABLE_ID (default tblbuFMpfv5R4DIyp).
*/

import { buildWelcome, sendViaResend } from './lib/invites.mjs';
import { linkSig } from './login-link.mjs';

const GHL = 'https://services.leadconnectorhq.com';
const AT_BASE = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ';
const AT_TABLE = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';

const json = (status, body) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
});

async function at(pathname, init = {}) {
  const res = await fetch(`https://api.airtable.com/v0/${AT_BASE}/${AT_TABLE}${pathname}`, {
    ...init,
    headers: { Authorization: `Bearer ${process.env.AIRTABLE_TOKEN}`, 'content-type': 'application/json', ...(init.headers || {}) },
  });
  if (!res.ok) throw new Error(`Airtable ${res.status}: ${(await res.text()).slice(0, 150)}`);
  return res.json();
}

async function findInvestorByEmail(email) {
  const clean = String(email || '').trim().toLowerCase().replace(/"/g, '');
  if (!clean.includes('@')) return null;
  const formula = encodeURIComponent(`LOWER({Email Address}) = "${clean}"`);
  const data = await at(`?filterByFormula=${formula}&maxRecords=1`);
  return (data.records && data.records[0]) || null;
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });

  const key = event.headers['x-portal-key'] || (event.queryStringParameters || {}).key;
  if (!process.env.PORTAL_SYNC_KEY || key !== process.env.PORTAL_SYNC_KEY) return json(403, { error: 'forbidden' });
  if (!process.env.AIRTABLE_TOKEN) return json(500, { error: 'AIRTABLE_TOKEN not configured' });

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { /* some webhooks send form-encoded; contact id may be in query */ }
  const contactId = body.contact_id || body.contactId || body.id
    || (body.contact && body.contact.id) || (event.queryStringParameters || {}).contact_id;
  if (!contactId) return json(400, { error: 'no contact id in payload' });

  // Pull the contact fresh from GHL — the webhook payload shape varies, the API doesn't.
  const gh = { Authorization: `Bearer ${process.env.GHL_Key || process.env.GHL_API_KEY}`, Version: '2021-07-28', 'content-type': 'application/json' };
  const cr = await fetch(`${GHL}/contacts/${contactId}`, { headers: gh });
  if (!cr.ok) return json(502, { error: `GHL contact fetch ${cr.status}` });
  const c = (await cr.json()).contact || {};

  // Find the Portal Access value among the contact's custom fields.
  // model=all is required — the default can omit one model's fields.
  const fr = await fetch(`${GHL}/locations/${process.env.GHL_LOCATION_ID}/customFields?model=all`, { headers: gh });
  const fields = fr.ok ? (await fr.json()).customFields || [] : [];
  const byName = (name, model) => fields.find((f) => (f.model || 'contact') === model && f.name.toLowerCase() === name.toLowerCase());
  const paField = byName('portal access', 'contact');
  if (!paField) return json(500, { error: 'Portal Access field not found in GHL' });
  const cf = {};
  for (const v of c.customFields || []) cf[v.id] = v.value ?? v.field_value ?? v.fieldValue;
  const portal = String(cf[paField.id] || '').trim().toLowerCase();
  if (portal !== 'yes' && portal !== 'no') return json(200, { ok: true, skipped: `Portal Access is "${portal || 'empty'}" — nothing to do` });

  // Exchange timeline → Airtable date columns. Contact-level fields first
  // (legacy-migrated data lives there); fall back to the newest opportunity's
  // fields (where new registrations store them).
  const asDate = (v) => {
    const s = String(v || '').slice(0, 10);
    return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null;
  };
  const pick = (names, source) => {
    for (const [name, model] of names) {
      const f = byName(name, model);
      if (f && asDate(source[f.id])) return asDate(source[f.id]);
    }
    return null;
  };
  let startDate = pick([['Closing Date', 'contact']], cf);
  let idExp = pick([['45-Day Deadline', 'contact']], cf);
  let exchExp = pick([['180-Day Deadline', 'contact']], cf);
  if (!startDate || !idExp || !exchExp) {
    try {
      const or = await fetch(`${GHL}/opportunities/search?location_id=${process.env.GHL_LOCATION_ID}&contact_id=${contactId}&limit=20`, { headers: gh });
      const opps = or.ok ? (await or.json()).opportunities || [] : [];
      opps.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
      for (const o of opps) {
        const ocf = {};
        for (const v of o.customFields || []) ocf[v.id] = v.value ?? v.fieldValue ?? v.field_value ?? (Array.isArray(v.fieldValueArray) ? v.fieldValueArray[0] : undefined);
        startDate = startDate || pick([['Sale Date', 'opportunity']], ocf);
        idExp = idExp || pick([['45-Day Deadline', 'opportunity']], ocf);
        exchExp = exchExp || pick([['180-Day Deadline', 'opportunity']], ocf);
        if (startDate && idExp && exchExp) break;
      }
    } catch (e) { console.error('[portal-sync] opp dates:', e.message); }
  }
  const dateFields = {};
  if (startDate) dateFields['Start Date'] = startDate;
  if (idExp) dateFields['ID Period Expiration'] = idExp;
  if (exchExp) dateFields['1031 Expiration'] = exchExp;

  const email = c.email;
  if (!email) return json(400, { error: 'contact has no email' });
  const existing = await findInvestorByEmail(email);

  let action;
  if (portal === 'yes') {
    let rid, welcomeSent;
    if (existing) {
      rid = existing.id;
      welcomeSent = existing.fields['Welcome Email Sent'];
      await at(`/${rid}`, {
        method: 'PATCH',
        body: JSON.stringify({ fields: { 'Access Level': 'Approved', ...dateFields }, typecast: true }),
      });
      action = `approved existing investor row for ${email}`;
    } else {
      const created = await at('', {
        method: 'POST',
        body: JSON.stringify({
          records: [{ fields: {
            'First Name': c.firstName || '',
            'Last Name': c.lastName || '',
            'Email Address': email,
            'Access Level': 'Approved',
            'Start Date': new Date().toISOString().slice(0, 10),
            ...dateFields,
          } }],
          typecast: true,
        }),
      });
      rid = created.records && created.records[0] && created.records[0].id;
      action = `created investor row for ${email}`;
    }

    // Welcome email with a first-time auto-login link — sent once per investor.
    // Clearing "Welcome Email Sent" in Airtable allows a re-send on the next sync.
    if (rid && !welcomeSent && process.env.SESSION_SECRET) {
      try {
        const base = process.env.URL || 'https://baker1031.com';
        const t = Date.now();
        const loginLink = `${base}/api/login-link?rid=${rid}&t=${t}&sig=${linkSig(rid, t)}`;
        const msg = buildWelcome(c.firstName || 'there', loginLink, base);
        if (await sendViaResend(email, msg.subject, msg.html)) {
          await at(`/${rid}`, {
            method: 'PATCH',
            body: JSON.stringify({ fields: { 'Welcome Email Sent': `${new Date().toISOString().slice(0, 16)}Z` } }),
          }).catch(() => {});
          action += ' + welcome email sent';
        }
      } catch (e) { console.error('[portal-sync] welcome:', e.message); }
    }
  } else {
    if (!existing) return json(200, { ok: true, skipped: `no investor row for ${email} — nothing to revoke` });
    await at(`/${existing.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ fields: { 'Access Level': 'Revoked' }, typecast: true }),
    });
    action = `revoked portal access for ${email}`;
  }

  // Leave a breadcrumb on the GHL contact.
  await fetch(`${GHL}/contacts/${contactId}/notes`, {
    method: 'POST', headers: gh,
    body: JSON.stringify({ body: `Portal sync: ${action} (${new Date().toISOString().slice(0, 16)}Z)` }),
  }).catch(() => {});

  return json(200, { ok: true, action });
};

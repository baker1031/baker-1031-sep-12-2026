/*
  Baker 1031 — Attio "Portal Access" → Airtable "Investor Access" sync (POST /api/portal-sync)

  Trigger it from an Attio webhook (record.updated on people — ideally filtered to the "Portal Access"
  attribute) or by hand with {"email": "..."} / {"record_id": "..."}.

  Portal Access = Yes → upsert the investor row in Airtable with Access Level "Approved" (creating the row
                        with name / email / start date if it doesn't exist) — the person can log in. Also
                        writes the exchange timeline (Start Date, ID Period Expiration, 1031 Expiration) from
                        the person's Closing Date / 45-Day / 180-Day attributes, falling back to the newest
                        open deal's Sale Date / deadlines. Sends the welcome email once (Welcome Email Sent).
  Portal Access = No  → set the row's Access Level to "Revoked" — login stops working immediately
                        (auth.mjs re-verifies every page load); Deals Reviewed history is preserved.

  "Portal Access" is a select (Yes / No) or checkbox attribute on the People object in Attio.

  "Portal Access - Level 2" (Yes / Requested / No) is the second tier, for the restricted pages listed in
  gate.js. It syncs to the Airtable "Level 2 Access" field the same way, stamps "Level 2 Approved On" the
  first time it is granted, and emails the investor once to tell them. It is independent of the portal
  flag: level 2 without portal access does nothing, since the gate checks both.

  Auth: an Attio webhook is verified with its signing secret (ATTIO_WEBHOOK_SECRET, header Attio-Signature);
        otherwise the request must carry the shared key (header x-portal-key, or ?key=PORTAL_SYNC_KEY).
  Env:  ATTIO_API_KEY, AIRTABLE_TOKEN, PORTAL_SYNC_KEY and/or ATTIO_WEBHOOK_SECRET,
        ACCESS_BASE_ID (default appiKLSyAUmP0h8cJ), ACCESS_TABLE_ID (default tblbuFMpfv5R4DIyp).
*/
import crypto from 'node:crypto';
import { buildWelcome, buildLevel2Granted, sendViaResend } from './lib/invites.mjs';
import { linkSig } from './login-link.mjs';
import * as attio from './lib/attio.mjs';

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

function signedByAttio(event) {
  const secret = process.env.ATTIO_WEBHOOK_SECRET;
  const sig = event.headers['attio-signature'] || event.headers['x-attio-signature'];
  if (!secret || !sig) return false;
  const want = crypto.createHmac('sha256', secret).update(event.body || '', 'utf8').digest('hex');
  return want.length === sig.length && crypto.timingSafeEqual(Buffer.from(want), Buffer.from(sig));
}

const asDate = (v) => { const s = String(v || '').slice(0, 10); return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null; };

async function syncOne(recordId) {
  const person = await attio.getPerson(recordId);
  const pAttrs = await attio.attributes('people');
  const flat = attio.flatValues(person);
  const val = (title) => { const a = pAttrs.find((x) => x.title.toLowerCase() === title.toLowerCase()); return a ? flat[a.slug] : undefined; };

  const raw = val('Portal Access');
  const portal = raw === true ? 'yes' : raw === false ? 'no' : String(raw ?? '').trim().toLowerCase();
  if (portal !== 'yes' && portal !== 'no') return { skipped: `Portal Access is "${portal || 'empty'}" — nothing to do` };

  const email = Array.isArray(flat.email_addresses) ? flat.email_addresses[0] : flat.email_addresses;
  if (!email) return { error: 'person has no email' };
  const name = Array.isArray(flat.name) ? flat.name[0] : flat.name;
  const firstName = name?.first_name || '';

  // exchange timeline: person attributes first, then the newest open deal
  let startDate = asDate(val('Closing Date')) || asDate(val('Sale Date'));
  let idExp = asDate(val('45-Day Deadline'));
  let exchExp = asDate(val('180-Day Deadline'));
  if (!startDate || !idExp || !exchExp) {
    const deal = await attio.openDeal(recordId);
    if (deal) {
      const dAttrs = await attio.attributes('deals');
      const df = attio.flatValues(deal);
      const dv = (title) => { const a = dAttrs.find((x) => x.title.toLowerCase() === title.toLowerCase()); return a ? df[a.slug] : undefined; };
      startDate = startDate || asDate(dv('Sale Date'));
      idExp = idExp || asDate(dv('45-Day Deadline'));
      exchExp = exchExp || asDate(dv('180-Day Deadline'));
    }
  }
  const dateFields = {};
  if (startDate) dateFields['Start Date'] = startDate;
  if (idExp) dateFields['ID Period Expiration'] = idExp;
  if (exchExp) dateFields['1031 Expiration'] = exchExp;

  // Level 2 — the second approval tier. Mirrors whatever Attio says, so revoking there revokes here.
  const rawL2 = val('Portal Access - Level 2');
  const l2 = rawL2 === true ? 'yes' : rawL2 === false ? 'no' : String(rawL2 ?? '').trim().toLowerCase();
  const L2_MAP = { yes: 'Approved', requested: 'Requested', no: 'Not Approved' };
  const level2 = L2_MAP[l2] || null;

  const existing = await findInvestorByEmail(email);
  let action;
  if (portal === 'yes') {
    let rid, welcomeSent;
    if (existing) {
      rid = existing.id;
      welcomeSent = existing.fields['Welcome Email Sent'];
      const l2Fields = {};
      if (level2) {
        l2Fields['Level 2 Access'] = level2;
        if (level2 === 'Approved' && !existing.fields['Level 2 Approved On']) l2Fields['Level 2 Approved On'] = new Date().toISOString().slice(0, 10);
      }
      await at(`/${rid}`, { method: 'PATCH', body: JSON.stringify({ fields: { 'Access Level': 'Approved', ...dateFields, ...l2Fields }, typecast: true }) });
      action = `approved existing investor row for ${email}`;
      if (level2 === 'Approved' && existing.fields['Level 2 Access'] !== 'Approved') action += ' + level 2 granted';
    } else {
      const created = await at('', {
        method: 'POST',
        body: JSON.stringify({ records: [{ fields: {
          'First Name': firstName, 'Last Name': name?.last_name || '', 'Email Address': email,
          'Access Level': 'Approved', 'Start Date': new Date().toISOString().slice(0, 10), ...dateFields,
          ...(level2 ? { 'Level 2 Access': level2 } : {}),
          ...(level2 === 'Approved' ? { 'Level 2 Approved On': new Date().toISOString().slice(0, 10) } : {}),
        } }], typecast: true }),
      });
      rid = created.records && created.records[0] && created.records[0].id;
      action = `created investor row for ${email}`;
    }
    // Level-2 grant: one email, the first time. Re-sending is a matter of clearing the date field.
    if (rid && level2 === 'Approved' && existing && existing.fields['Level 2 Access'] !== 'Approved') {
      try {
        const base = process.env.URL || 'https://baker1031.com';
        const msg = buildLevel2Granted(firstName || 'there', base);
        if (await sendViaResend(email, msg.subject, msg.html)) action += ' + level 2 email sent';
      } catch (e) { console.error('[portal-sync] level2 email:', e.message); }
    }

    // Welcome email with a first-time auto-login link — sent once per investor.
    // Clearing "Welcome Email Sent" in Airtable allows a re-send on the next sync.
    if (rid && !welcomeSent && process.env.SESSION_SECRET) {
      try {
        const base = process.env.URL || 'https://baker1031.com';
        const t = Date.now();
        const loginLink = `${base}/api/login-link?rid=${rid}&t=${t}&sig=${linkSig(rid, t)}`;
        const msg = buildWelcome(firstName || 'there', loginLink, base);
        if (await sendViaResend(email, msg.subject, msg.html)) {
          await at(`/${rid}`, { method: 'PATCH', body: JSON.stringify({ fields: { 'Welcome Email Sent': `${new Date().toISOString().slice(0, 16)}Z` } }) }).catch(() => {});
          action += ' + welcome email sent';
        }
      } catch (e) { console.error('[portal-sync] welcome:', e.message); }
    }
  } else {
    if (!existing) return { skipped: `no investor row for ${email} — nothing to revoke` };
    await at(`/${existing.id}`, { method: 'PATCH', body: JSON.stringify({ fields: { 'Access Level': 'Revoked' }, typecast: true }) });
    action = `revoked portal access for ${email}`;
  }

  await attio.addNote('people', recordId, 'Portal sync', `${action} (${new Date().toISOString().slice(0, 16)}Z)`, 'plaintext').catch(() => {});
  return { action };
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  const key = event.headers['x-portal-key'] || (event.queryStringParameters || {}).key;
  const keyed = !!process.env.PORTAL_SYNC_KEY && key === process.env.PORTAL_SYNC_KEY;
  if (!keyed && !signedByAttio(event)) return json(403, { error: 'forbidden' });
  if (!process.env.AIRTABLE_TOKEN) return json(500, { error: 'AIRTABLE_TOKEN not configured' });
  if (!attio.configured()) return json(500, { error: 'ATTIO_API_KEY not configured' });

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { /* fall through to query */ }

  // record ids: Attio webhook batch, a single event, or a manual call by record_id / email
  const ids = new Set();
  for (const ev of body.events || []) if (ev?.id?.record_id) ids.add(ev.id.record_id);
  if (body.id?.record_id) ids.add(body.id.record_id);
  if (body.record_id) ids.add(body.record_id);
  if (body.email) { const p = await attio.findPersonByEmail(body.email); if (p) ids.add(p.id.record_id); }
  if (!ids.size) return json(400, { error: 'no record id in payload' });

  const results = {};
  for (const id of ids) {
    try { results[id] = await syncOne(id); }
    catch (e) { console.error('[portal-sync]', id, e.message); results[id] = { error: e.message }; }
  }
  return json(200, { ok: true, results });
};

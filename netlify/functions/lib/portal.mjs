/*
  Baker 1031 — the investor-access flags, kept in step between Attio and Airtable in BOTH directions.

  Two systems hold the same two switches:

    Attio (People)                     Airtable (Investors)
    Portal Access            Yes/No -> Access Level      Approved / Call Needed / Revoked
    Portal Access - Level 2  Yes/Requested/No ->
                                        Level 2 Access   Approved / Requested / Not Approved

  Airtable is what the login actually reads (auth.mjs re-checks it on every page load), so it has to be
  right; Attio is where the decision gets made. Either one can be edited by hand, so this module works
  out which side was edited last and pushes that way:

    Access Changed At  (Airtable, automatic lastModifiedTime on the two access fields)
    Access Synced At   (Airtable, written here after every access write, in either direction)

  Airtable edited since the last sync -> push Airtable to Attio.  Otherwise -> push Attio to Airtable.
  An empty Access Synced At means the row has never been through here, and Attio wins: a blank stamp is
  not evidence that Airtable is newer, and guessing the other way would let a stale row overwrite a
  decision in the CRM.

  The Attio-to-Airtable direction only writes when the mapped value actually differs, which is what
  keeps "Call Needed" alive. Attio has no Call Needed option, so it maps to No; if it wrote No as
  "Revoked" on every pass it would quietly demote everyone waiting on an intro call.

  Env: ATTIO_API_KEY, AIRTABLE_TOKEN, ACCESS_BASE_ID (default appiKLSyAUmP0h8cJ),
       ACCESS_TABLE_ID (default tblbuFMpfv5R4DIyp), SESSION_SECRET (welcome-email login link), RESEND_API_KEY.
*/
import { buildWelcome, buildLevel2Granted, sendViaResend } from './invites.mjs';
import { linkSig } from '../login-link.mjs';
import * as attio from './attio.mjs';

export const AT_BASE = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ';
export const AT_TABLE = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';

const CHANGED_AT = 'Access Changed At';   // automatic in Airtable
const SYNCED_AT = 'Access Synced At';     // written here

// Attio value -> the Airtable value it means. Attio has no "Call Needed"; see the header.
const PORTAL_TO_AT = { yes: 'Approved', no: 'Revoked' };
const L2_TO_AT = { yes: 'Approved', requested: 'Requested', no: 'Not Approved' };
// and back
const AT_TO_PORTAL = { Approved: 'Yes', Revoked: 'No', 'Call Needed': 'No' };
const AT_TO_L2 = { Approved: 'Yes', Requested: 'Requested', 'Not Approved': 'No' };

export async function at(pathname, init = {}) {
  const res = await fetch(`https://api.airtable.com/v0/${AT_BASE}/${AT_TABLE}${pathname}`, {
    ...init,
    headers: { Authorization: `Bearer ${process.env.AIRTABLE_TOKEN}`, 'content-type': 'application/json', ...(init.headers || {}) },
  });
  if (!res.ok) throw new Error(`Airtable ${res.status}: ${(await res.text()).slice(0, 150)}`);
  return res.json();
}

export async function findInvestorByEmail(email) {
  const clean = String(email || '').trim().toLowerCase().replace(/"/g, '');
  if (!clean.includes('@')) return null;
  const formula = encodeURIComponent(`LOWER({Email Address}) = "${clean}"`);
  const data = await at(`?filterByFormula=${formula}&maxRecords=1`);
  return (data.records && data.records[0]) || null;
}

const asDate = (v) => { const s = String(v || '').slice(0, 10); return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null; };
const lower = (v) => (v === true ? 'yes' : v === false ? 'no' : String(v ?? '').trim().toLowerCase());
const stamp = () => new Date().toISOString();

/* Write to an investor row and then record that the write came from here. Two calls on purpose: the
   second sets Access Synced At to the row's own new Access Changed At, so the comparison that decides
   direction next time is exact rather than "within a few seconds". Access Synced At is not one of the
   fields Access Changed At watches, so stamping it does not bump the thing it is being compared with. */
async function patchAccess(rid, fields) {
  const res = await at(`/${rid}`, { method: 'PATCH', body: JSON.stringify({ fields, typecast: true }) });
  const changedAt = res?.fields?.[CHANGED_AT];
  await at(`/${rid}`, { method: 'PATCH', body: JSON.stringify({ fields: { [SYNCED_AT]: changedAt || stamp() } }) }).catch(() => {});
  return res;
}

/* The two flags and the exchange dates off an Attio person record that is already in hand. The
   attribute list is cached, so after the first call this costs no requests at all -- which is what
   lets the scheduled reconcile decide 117 rows without 117 round trips. */
export async function personValues(record) {
  const pAttrs = await attio.attributes('people');
  const flat = attio.flatValues(record);
  const val = (title) => { const a = pAttrs.find((x) => x.title.toLowerCase() === title.toLowerCase()); return a ? flat[a.slug] : undefined; };
  const name = Array.isArray(flat.name) ? flat.name[0] : flat.name;
  return {
    recordId: record?.id?.record_id || record?.id,
    record,
    email: Array.isArray(flat.email_addresses) ? flat.email_addresses[0] : flat.email_addresses,
    firstName: name?.first_name || '',
    lastName: name?.last_name || '',
    portal: lower(val('Portal Access')),
    level2: lower(val('Portal Access - Level 2')),
    closing: asDate(val('Closing Date')) || asDate(val('Sale Date')),
    day45: asDate(val('45-Day Deadline')),
    day180: asDate(val('180-Day Deadline')),
  };
}

/* Read the two flags off an Attio person, with the person's exchange dates. */
async function readPerson(recordId) {
  return personValues(await attio.getPerson(recordId));
}

/* The exchange timeline for the Airtable row: the person's own dates, else the newest open deal's. */
async function timelineFields(p) {
  let { closing, day45, day180 } = p;
  if (!closing || !day45 || !day180) {
    const deal = await attio.openDeal(p.recordId);
    if (deal) {
      const dAttrs = await attio.attributes('deals');
      const df = attio.flatValues(deal);
      const dv = (title) => { const a = dAttrs.find((x) => x.title.toLowerCase() === title.toLowerCase()); return a ? df[a.slug] : undefined; };
      closing = closing || asDate(dv('Sale Date'));
      day45 = day45 || asDate(dv('45-Day Deadline'));
      day180 = day180 || asDate(dv('180-Day Deadline'));
    }
  }
  const out = {};
  if (closing) out['Start Date'] = closing;
  if (day45) out['ID Period Expiration'] = day45;
  if (day180) out['1031 Expiration'] = day180;
  return out;
}

/* ---- Attio -> Airtable -------------------------------------------------------------------------- */
export async function syncOne(recordId) {
  const p = await readPerson(recordId);
  if (p.portal !== 'yes' && p.portal !== 'no') return { skipped: `Portal Access is "${p.portal || 'empty'}" — nothing to do` };
  if (!p.email) return { error: 'person has no email' };

  const wantLevel = PORTAL_TO_AT[p.portal];
  const wantL2 = L2_TO_AT[p.level2] || null;
  const dateFields = await timelineFields(p);
  const existing = await findInvestorByEmail(p.email);
  let action;

  if (p.portal === 'yes') {
    let rid, welcomeSent, l2Before;
    if (existing) {
      rid = existing.id;
      welcomeSent = existing.fields['Welcome Email Sent'];
      l2Before = existing.fields['Level 2 Access'];
      const fields = { ...dateFields };
      if (existing.fields['Access Level'] !== 'Approved') fields['Access Level'] = 'Approved';
      if (wantL2 && l2Before !== wantL2) {
        fields['Level 2 Access'] = wantL2;
        if (wantL2 === 'Approved' && !existing.fields['Level 2 Approved On']) fields['Level 2 Approved On'] = stamp().slice(0, 10);
      }
      await patchAccess(rid, fields);
      action = `approved existing investor row for ${p.email}`;
      if (wantL2 === 'Approved' && l2Before !== 'Approved') action += ' + level 2 granted';
    } else {
      const created = await at('', {
        method: 'POST',
        body: JSON.stringify({ records: [{ fields: {
          'First Name': p.firstName, 'Last Name': p.lastName, 'Email Address': p.email,
          'Access Level': 'Approved', 'Start Date': stamp().slice(0, 10), ...dateFields,
          ...(wantL2 ? { 'Level 2 Access': wantL2 } : {}),
          ...(wantL2 === 'Approved' ? { 'Level 2 Approved On': stamp().slice(0, 10) } : {}),
          [SYNCED_AT]: stamp(),
        } }], typecast: true }),
      });
      rid = created.records && created.records[0] && created.records[0].id;
      action = `created investor row for ${p.email}`;
    }

    if (rid && wantL2 === 'Approved' && existing && l2Before !== 'Approved') {
      try {
        const msg = buildLevel2Granted(p.firstName || 'there', process.env.URL || 'https://baker1031.com');
        if (await sendViaResend(p.email, msg.subject, msg.html)) action += ' + level 2 email sent';
      } catch (e) { console.error('[portal] level2 email:', e.message); }
    }
    if (rid && !welcomeSent && process.env.SESSION_SECRET) {
      try {
        const base = process.env.URL || 'https://baker1031.com';
        const t = Date.now();
        const msg = buildWelcome(p.firstName || 'there', `${base}/api/login-link?rid=${rid}&t=${t}&sig=${linkSig(rid, t)}`, base);
        if (await sendViaResend(p.email, msg.subject, msg.html)) {
          await at(`/${rid}`, { method: 'PATCH', body: JSON.stringify({ fields: { 'Welcome Email Sent': `${stamp().slice(0, 16)}Z` } }) }).catch(() => {});
          action += ' + welcome email sent';
        }
      } catch (e) { console.error('[portal] welcome:', e.message); }
    }
  } else {
    if (!existing) return { skipped: `no investor row for ${p.email} — nothing to revoke` };
    // Attio's No means "not approved". Only Approved is a demotion; Call Needed is already not approved
    // and is the site's own pre-approval state, so it is left alone.
    if (existing.fields['Access Level'] !== 'Approved') {
      return { skipped: `Access Level is already "${existing.fields['Access Level'] || 'empty'}" for ${p.email}` };
    }
    await patchAccess(existing.id, { 'Access Level': 'Revoked' });
    action = `revoked portal access for ${p.email}`;
  }

  await attio.addNote('people', recordId, 'Portal sync', `${action} (${stamp().slice(0, 16)}Z)`, 'plaintext').catch(() => {});
  return { action, direction: 'attio->airtable' };
}

/* ---- Airtable -> Attio -------------------------------------------------------------------------- */
export async function pushToAttio(row, person = null) {
  const email = row.fields['Email Address'];
  const p = person || (await (async () => {
    const found = await attio.findPersonByEmail(email);
    return found ? readPerson(found.id.record_id) : null;
  })());
  if (!p) return { error: `no Attio person for ${email}` };

  const wantPortal = AT_TO_PORTAL[row.fields['Access Level']] || null;
  const wantL2 = AT_TO_L2[row.fields['Level 2 Access']] || null;
  const pairs = [];
  if (wantPortal && lower(wantPortal) !== p.portal) pairs.push(['Portal Access', wantPortal]);
  if (wantL2 && lower(wantL2) !== p.level2) pairs.push(['Portal Access - Level 2', wantL2]);
  if (!pairs.length) return { skipped: `Attio already matches Airtable for ${email}` };

  await attio.setValues('people', p.recordId, pairs);
  const what = pairs.map(([k, v]) => `${k} = ${v}`).join(', ');
  await attio.addNote('people', p.recordId, 'Portal sync (from Airtable)',
    `Set from the Investors table in Airtable: ${what} (${stamp().slice(0, 16)}Z)`, 'plaintext').catch(() => {});
  await at(`/${row.id}`, { method: 'PATCH', body: JSON.stringify({ fields: { [SYNCED_AT]: row.fields[CHANGED_AT] || stamp() } }) }).catch(() => {});
  return { action: `pushed to Attio: ${what}`, direction: 'airtable->attio' };
}

/* ---- whichever side was edited last ------------------------------------------------------------- */
export function airtableIsNewer(row) {
  const changed = row.fields[CHANGED_AT];
  const synced = row.fields[SYNCED_AT];
  if (!changed) return false;
  if (!synced) return false;           // never synced: Attio wins. See the header.
  return new Date(changed).getTime() > new Date(synced).getTime() + 1000;
}

export async function reconcileRow(row) {
  if (!row.fields['Email Address']) return { skipped: 'row has no email' };
  if (airtableIsNewer(row)) return pushToAttio(row);
  const found = await attio.findPersonByEmail(row.fields['Email Address']);
  if (!found) return { skipped: `no Attio person for ${row.fields['Email Address']}` };
  return syncOne(found.id.record_id);
}

/* Every investor row, oldest page first. Used by the scheduled reconcile. */
export async function allInvestors() {
  const rows = [];
  let offset;
  do {
    const data = await at(`?pageSize=100${offset ? `&offset=${offset}` : ''}`);
    rows.push(...(data.records || []));
    offset = data.offset;
  } while (offset);
  return rows;
}

/* ---- the scheduled reconcile ---------------------------------------------------------------------

   reconcileRow is right for one investor and wrong for all of them: per row it searches Attio for the
   person, fetches the person, fetches the person again for the deal lookup, then fetches each linked
   deal. Over 117 rows that is several hundred sequential requests, which no function invocation has
   time for -- and because a row with no Portal Access value writes nothing, a run that dies partway
   leaves no trace at all. That is exactly what the 2026-09-18 00:17Z pass did: nothing written, no
   note, no stamp.

   So the scheduled pass works the other way round. It reads the investor table once, pulls the whole
   access-flagged population out of Attio in five paged queries, matches the two in memory, and only
   then spends a request -- on the rows that actually differ. Roughly ten requests instead of five
   hundred.

   Two deliberate splits:
     - Access is decided for every row, always. It is what the login reads, so it is never the thing
       that gets dropped when time runs short.
     - The exchange dates are enrichment. They need a deal lookup, so they happen afterwards, capped,
       with whatever budget is left, and carry over to the next hour if they do not fit.
   -------------------------------------------------------------------------------------------------- */

// Every person who has either flag set. Select attributes are filtered by option title.
const ACCESS_FILTERS = [
  { portal_access: 'Yes' },
  { portal_access: 'No' },
  { portal_access_level_2: 'Yes' },
  { portal_access_level_2: 'Requested' },
  { portal_access_level_2: 'No' },
];

/* Which of the three Airtable date fields the person's own dates can fill. `missing` means the row is
   still short a date that the person record does not have -- an open deal might, so it is worth a look
   later, but never worth a write now. */
function personDateFields(p, row) {
  const f = row.fields || {};
  const fields = {};
  let missing = false;
  for (const [key, value] of [['Start Date', p.closing], ['ID Period Expiration', p.day45], ['1031 Expiration', p.day180]]) {
    if (f[key]) continue;
    if (value) fields[key] = value;
    else missing = true;
  }
  return { fields, missing };
}

/* The whole decision for one row, as a pure function of the row and the Attio person (null when the
   person has neither flag set). No I/O, so the scheduled pass can decide before it spends a request --
   and so this is testable against real data without touching either system. */
export function planRow(row, person) {
  const f = row.fields || {};
  if (!f['Email Address']) return { action: 'skip', reason: 'row has no email' };
  if (airtableIsNewer(row)) return { action: 'push', reason: 'Airtable edited since the last sync' };
  if (!person) return { action: 'skip', reason: 'no Attio person with an access flag' };
  if (person.portal !== 'yes' && person.portal !== 'no') {
    return { action: 'skip', reason: `Portal Access is "${person.portal || 'empty'}"` };
  }

  if (person.portal === 'no') {
    // Attio's No means "not approved". Only Approved is a demotion; Call Needed is the site's own
    // pre-approval state and is left alone.
    if (f['Access Level'] !== 'Approved') {
      return { action: 'skip', reason: `Access Level is already "${f['Access Level'] || 'empty'}"` };
    }
    return { action: 'revoke', fields: { 'Access Level': 'Revoked' } };
  }

  const fields = {};
  if (f['Access Level'] !== 'Approved') fields['Access Level'] = 'Approved';
  const wantL2 = L2_TO_AT[person.level2] || null;
  const grantedL2 = wantL2 === 'Approved' && f['Level 2 Access'] !== 'Approved';
  if (wantL2 && f['Level 2 Access'] !== wantL2) {
    fields['Level 2 Access'] = wantL2;
    if (grantedL2 && !f['Level 2 Approved On']) fields['Level 2 Approved On'] = stamp().slice(0, 10);
  }
  const dates = personDateFields(person, row);
  Object.assign(fields, dates.fields);
  const needsWelcome = !f['Welcome Email Sent'];

  // A missing date on its own is not work: without an open deal to read there is nothing to write.
  if (!Object.keys(fields).length && !grantedL2 && !needsWelcome) {
    return { action: 'skip', reason: 'already in step', datesMissing: dates.missing };
  }
  return { action: 'approve', fields, grantedL2, needsWelcome, datesMissing: dates.missing };
}

/* Carry out a plan. Same writes and same emails as syncOne, from a decision already made. */
async function applyPlan(row, person, plan) {
  if (plan.action === 'revoke') {
    await patchAccess(row.id, plan.fields);
    const action = `revoked portal access for ${person.email}`;
    await attio.addNote('people', person.recordId, 'Portal sync', `${action} (${stamp().slice(0, 16)}Z)`, 'plaintext').catch(() => {});
    return { action, direction: 'attio->airtable' };
  }

  await patchAccess(row.id, plan.fields);
  let action = `approved existing investor row for ${person.email}`;
  const changed = Object.keys(plan.fields);
  if (changed.length) action += ` (${changed.join(', ')})`;

  if (plan.grantedL2) {
    action += ' + level 2 granted';
    try {
      const msg = buildLevel2Granted(person.firstName || 'there', process.env.URL || 'https://baker1031.com');
      if (await sendViaResend(person.email, msg.subject, msg.html)) action += ' + level 2 email sent';
    } catch (e) { console.error('[portal] level2 email:', e.message); }
  }
  if (plan.needsWelcome && process.env.SESSION_SECRET) {
    try {
      const base = process.env.URL || 'https://baker1031.com';
      const t = Date.now();
      const msg = buildWelcome(person.firstName || 'there', `${base}/api/login-link?rid=${row.id}&t=${t}&sig=${linkSig(row.id, t)}`, base);
      if (await sendViaResend(person.email, msg.subject, msg.html)) {
        await at(`/${row.id}`, { method: 'PATCH', body: JSON.stringify({ fields: { 'Welcome Email Sent': `${stamp().slice(0, 16)}Z` } }) }).catch(() => {});
        action += ' + welcome email sent';
      }
    } catch (e) { console.error('[portal] welcome:', e.message); }
  }
  await attio.addNote('people', person.recordId, 'Portal sync', `${action} (${stamp().slice(0, 16)}Z)`, 'plaintext').catch(() => {});
  return { action, direction: 'attio->airtable' };
}

/* Dates off the person's newest open deal, for the fields the row is still missing. */
async function dealDateFields(deal, row) {
  const dAttrs = await attio.attributes('deals');
  const df = attio.flatValues(deal);
  const dv = (title) => { const a = dAttrs.find((x) => x.title.toLowerCase() === title.toLowerCase()); return a ? df[a.slug] : undefined; };
  const f = row.fields || {};
  const out = {};
  for (const [key, title] of [['Start Date', 'Sale Date'], ['ID Period Expiration', '45-Day Deadline'], ['1031 Expiration', '180-Day Deadline']]) {
    if (f[key]) continue;
    const d = asDate(dv(title));
    if (d) out[key] = d;
  }
  return out;
}

export async function reconcileAll({ budgetMs = 20000, maxDealLookups = 25, dry = false } = {}) {
  const started = Date.now();
  const left = () => budgetMs - (Date.now() - started);
  const rows = await allInvestors();

  // The whole access-flagged population, in five paged queries.
  const byEmail = new Map();
  for (const filter of ACCESS_FILTERS) {
    try {
      for (const rec of await attio.queryPeople(filter)) {
        for (const v of rec.values?.email_addresses || []) {
          const em = String(v.email_address || '').trim().toLowerCase();
          if (em && !byEmail.has(em)) byEmail.set(em, rec);
        }
      }
    } catch (e) { console.error('[portal] people query', JSON.stringify(filter), e.message); }
  }

  // If the bulk queries came back with nothing while there are rows to check, something is wrong with
  // them rather than with the data. Fall back to the per-row path so the pass still does its job, and
  // say so loudly in the log.
  if (!byEmail.size && rows.length) {
    console.error('[portal] access-flag queries returned no people — falling back to per-row lookups');
    const results = [];
    let checked = 0;
    for (const row of rows) {
      if (left() < 4000) break;
      checked++;
      try { const r = await reconcileRow(row); if (r.action) results.push({ email: row.fields['Email Address'], ...r }); }
      catch (e) { results.push({ email: row.fields['Email Address'], error: e.message }); }
    }
    return { rows: rows.length, checked, changes: results, fallback: true, ms: Date.now() - started };
  }

  const results = [];
  const deferred = [];
  let checked = 0;
  let skipped = 0;
  let ranOut = false;

  for (const row of rows) {
    if (left() < 3000) { ranOut = true; break; }
    const email = String(row.fields['Email Address'] || '').trim().toLowerCase();
    const rec = email ? byEmail.get(email) || null : null;
    const person = rec ? await personValues(rec) : null;
    const plan = planRow(row, person);
    checked++;

    if (plan.action === 'skip') {
      skipped++;
      if (plan.datesMissing && (rec?.values?.associated_deals || []).length) deferred.push({ row, person });
      continue;
    }
    if (dry) {
      results.push({ email, would: plan.action, fields: plan.fields || {}, welcome: !!plan.needsWelcome, level2: !!plan.grantedL2 });
      continue;
    }
    try {
      const r = plan.action === 'push' ? await pushToAttio(row) : await applyPlan(row, person, plan);
      if (r.action) results.push({ email, ...r });
      else if (r.error) results.push({ email, error: r.error });
    } catch (e) {
      console.error('[portal] reconcile', email, e.message);
      results.push({ email, error: e.message });
    }
    if (plan.datesMissing && (rec?.values?.associated_deals || []).length) deferred.push({ row, person });
  }

  // Enrichment pass: exchange dates, capped, only for people who actually have a deal to read.
  let dealLookups = 0;
  if (!dry) {
    for (const { row, person } of deferred) {
      if (dealLookups >= maxDealLookups || left() < 4000) break;
      dealLookups++;
      try {
        const deal = await attio.openDealFrom(person.record);
        if (!deal) continue;
        const fields = await dealDateFields(deal, row);
        if (!Object.keys(fields).length) continue;
        await patchAccess(row.id, fields);
        results.push({ email: row.fields['Email Address'], action: `exchange dates from the open deal (${Object.keys(fields).join(', ')})`, direction: 'attio->airtable' });
      } catch (e) { console.error('[portal] dates', row.fields['Email Address'], e.message); }
    }
  }

  return {
    rows: rows.length, checked, skipped, flagged: byEmail.size,
    deferredDates: deferred.length, dealLookups, ranOutOfTime: ranOut,
    ms: Date.now() - started, changes: results,
  };
}

/*
  Baker 1031 — investor access, kept in step in both directions (POST /api/access-sync)

  /api/portal-sync carries a decision made in Attio into Airtable. This is the other half: an edit made
  in Airtable, carried back into Attio — and a scheduled pass that reconciles whatever has drifted, so
  neither side has to be the only place a switch can be flipped.

  Which way a row goes is decided per row, by two fields on the Airtable investor row:

      Access Changed At   automatic; when Access Level or Level 2 Access last changed in Airtable
      Access Synced At    written by the sync after every access write, in either direction

  Airtable changed since the last sync -> push Airtable to Attio. Otherwise -> Attio is the authority
  and the usual portal sync runs. A row that has never been synced leaves Attio in charge, because an
  empty stamp is not evidence that Airtable is newer.

  Calls:
    POST /api/access-sync?key=...                 reconcile every investor row (also the schedule)
    POST /api/access-sync?key=...  {"email":"…"}  reconcile one investor
    POST /api/access-sync?key=...&dry=1           report what it would do, change nothing

  Airtable can drive it immediately instead of waiting for the schedule: an automation on the Investors
  table, "When record updated" watching Access Level and Level 2 Access, with a "Send web request"
  step — POST to https://baker1031.com/api/access-sync?key=<PORTAL_SYNC_KEY>, body {"email": "<Email
  Address>"}. Without that the scheduled pass picks it up within the hour.

  Auth: the shared key (header x-portal-key, or ?key=PORTAL_SYNC_KEY). Netlify's scheduler invokes the
        function directly, so a scheduled run carries no key and is allowed through on that basis.
  Env:  ATTIO_API_KEY, AIRTABLE_TOKEN, PORTAL_SYNC_KEY, ACCESS_BASE_ID, ACCESS_TABLE_ID.
*/
import * as attio from './lib/attio.mjs';
import { findInvestorByEmail, reconcileRow, reconcileAll, airtableIsNewer } from './lib/portal.mjs';

const json = (status, body) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
});

const describe = (row) => ({
  email: row.fields['Email Address'],
  airtable: { access: row.fields['Access Level'] || null, level2: row.fields['Level 2 Access'] || null },
  changedAt: row.fields['Access Changed At'] || null,
  syncedAt: row.fields['Access Synced At'] || null,
  direction: airtableIsNewer(row) ? 'airtable->attio' : 'attio->airtable',
});

export const handler = async (event) => {
  const q = event.queryStringParameters || {};
  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { /* no body is fine */ }

  /* Netlify runs a scheduled function by POSTing to it with a JSON body carrying `next_run` -- there
     IS an HTTP request around it. This used to test `!event.httpMethod`, which is never true for a
     scheduled run, so every scheduled pass fell straight through to the key check, returned 403 and
     logged nothing. deadline-reminders and rebuild-watcher in this same directory already key on
     body.next_run; this now matches them. */
  const scheduled = !!body.next_run || !event.httpMethod;
  if (!scheduled) {
    if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
    const key = (event.headers && event.headers['x-portal-key']) || q.key;
    if (!process.env.PORTAL_SYNC_KEY || key !== process.env.PORTAL_SYNC_KEY) return json(403, { error: 'forbidden' });
  }
  if (!process.env.AIRTABLE_TOKEN) return json(500, { error: 'AIRTABLE_TOKEN not configured' });
  if (!attio.configured()) return json(500, { error: 'ATTIO_API_KEY not configured' });

  const dry = q.dry === '1' || body.dry === true;

  // One investor: the thorough per-row path, which is cheap for a single record.
  if (body.email) {
    const row = await findInvestorByEmail(body.email);
    if (!row) return json(200, { ok: true, skipped: `no investor row for ${body.email}` });
    if (dry) return json(200, { ok: true, dry: true, rows: [describe(row)] });
    try {
      const res = await reconcileRow(row);
      console.log(`[access-sync] ${body.email}: ${res.action || res.skipped || res.error || 'no change'}`);
      return json(200, { ok: true, checked: 1, changes: res.action ? [{ email: row.fields['Email Address'], ...res }] : [], result: res });
    } catch (e) {
      console.error('[access-sync]', body.email, e.message);
      return json(500, { error: e.message });
    }
  }

  // Everyone: the bulk pass. It reads the table once, pulls the access-flagged people out of Attio in
  // five paged queries and matches in memory, so it finishes inside the invocation instead of dying
  // partway through a few hundred sequential lookups.
  const budgetMs = Math.min(Math.max(Number(q.budget) || 20000, 5000), 25000);
  const out = await reconcileAll({ dry, budgetMs });
  console.log(`[access-sync] ${out.checked}/${out.rows} row(s) checked against ${out.flagged ?? '?'} flagged people in ${out.ms}ms — `
    + `${out.changes.length} change(s), ${out.dealLookups ?? 0} deal lookup(s)${out.ranOutOfTime ? ', OUT OF TIME' : ''}`);
  return json(200, { ok: true, dry: dry || undefined, ...out });
};

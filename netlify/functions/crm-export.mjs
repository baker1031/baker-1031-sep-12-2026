/*
  Baker 1031 — hands the CRM what Attio and the Airtable investor table hold, for the one-time move (POST /api/crm-export)

  This site already has the keys to both, so the CRM asks here instead of being given keys of its own, and nothing personal is copied by hand.
  Authorization: Bearer CRM_SHARED_KEY. Body { kind, cursor, limit }:

    people     Attio people, oldest first: id, created, name, emails, phones, and every other filled attribute keyed by its title
    deals      Attio deals: id, created, name, stage, value, the people on it, and the filled attributes by title
    notes      every Attio note: id, what it is attached to, title, plain text, created
    tasks      every Attio task: id, text, deadline, done, the people it is linked to
    investors  the Airtable Investors rows (login access, level 2, first-viewed offerings, reminder log, reminders off, welcome stamp, dates)

  Returns { rows, next }; pass next back as cursor until it comes back empty. Read only: nothing in Attio or Airtable is changed.
  Once the move is done this file, lib/attio.mjs and lib/portal.mjs can all be deleted together.
*/
import * as attio from './lib/attio.mjs';
import { fromCrm, crmConfigured } from './lib/crm.mjs';

const json = (status, body) => ({ statusCode: status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) });
const SKIP_TYPES = new Set(['interaction', 'actor-reference', 'record-reference', 'location', 'personal-name', 'email-address', 'phone-number']);

async function byTitle(object, record) {
  const attrs = await attio.attributes(object), flat = attio.flatValues(record), out = {};
  for (const a of attrs) {
    if (SKIP_TYPES.has(a.type)) continue;
    const v = flat[a.slug];
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) continue;
    out[a.title] = v;
  }
  return out;
}
const list = (v) => (v == null ? [] : Array.isArray(v) ? v : [v]);

async function records(object, offset, limit) {
  const res = await attio.attio(`/objects/${object}/records/query`, 'POST', { limit, offset, sorts: [{ attribute: 'created_at', direction: 'asc' }] });
  const data = res.data || [], rows = [];
  for (const rec of data) {
    const flat = attio.flatValues(rec), id = rec.id?.record_id, createdAt = rec.created_at || list(flat.created_at)[0] || '';
    if (object === 'people') {
      const name = list(flat.name)[0] || {};
      rows.push({ id, createdAt, name: { first_name: name.first_name || '', last_name: name.last_name || '', full_name: name.full_name || '' }, emails: list(flat.email_addresses), phones: list(flat.phone_numbers), v: await byTitle('people', rec) });
    } else {
      rows.push({ id, createdAt, name: list(flat.name)[0] || '', stage: attio.dealStage(rec), value: list(flat.value)[0] ?? null, people: list(flat.associated_people), v: await byTitle('deals', rec) });
    }
  }
  return { rows, next: data.length < limit ? '' : String(offset + limit) };
}

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  if (!crmConfigured()) return json(503, { error: 'not configured' });
  if (!fromCrm(event)) { await new Promise((r) => setTimeout(r, 400)); return json(401, { error: 'unauthorized' }); }
  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { return json(400, { error: 'bad json' }); }
  const kind = String(body.kind || ''), limit = Math.min(Math.max(Number(body.limit) || 25, 1), 100);

  try {
    if (kind === 'investors') {
      if (!process.env.AIRTABLE_TOKEN) return json(503, { error: 'AIRTABLE_TOKEN not configured' });
      const base = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ', table = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';
      const cur = /^[\w/.-]{1,200}$/.test(String(body.cursor || '')) ? `&offset=${encodeURIComponent(body.cursor)}` : '';
      const r = await fetch(`https://api.airtable.com/v0/${base}/${table}?pageSize=${limit}${cur}`, { headers: { Authorization: `Bearer ${process.env.AIRTABLE_TOKEN}` } });
      if (!r.ok) return json(502, { error: `Airtable ${r.status}` });
      const data = await r.json();
      return json(200, { rows: (data.records || []).map((x) => ({ id: x.id, createdTime: x.createdTime, f: x.fields || {} })), next: data.offset || '' });
    }
    if (!attio.configured()) return json(503, { error: 'ATTIO_API_KEY not configured' });
    const offset = /^\d{1,7}$/.test(String(body.cursor || '')) ? Number(body.cursor) : 0;
    if (kind === 'people' || kind === 'deals') return json(200, await records(kind, offset, limit));
    if (kind === 'notes' || kind === 'tasks') {
      let res;
      try { res = await attio.attio(`/${kind}?limit=${limit}&offset=${offset}`); }
      catch (e) { if (e.status === 403 || e.status === 401) return json(200, { rows: [], next: '', skipped: `this site's Attio key is not allowed to read ${kind}, so they were left in Attio` }); throw e; }
      const data = res.data || [];
      const rows = kind === 'notes'
        ? data.map((n) => ({ id: n.id?.note_id, parentObject: n.parent_object, parentId: n.parent_record_id, title: n.title || '', text: n.content_plaintext || '', createdAt: n.created_at || '' }))
        : data.map((t) => ({ id: t.id?.task_id, text: t.content_plaintext || '', deadline: t.deadline_at || '', done: !!t.is_completed, createdAt: t.created_at || '',
            people: (t.linked_records || []).filter((l) => (l.target_object || l.target_object_id) && l.target_record_id).map((l) => l.target_record_id) }));
      return json(200, { rows, next: data.length < limit ? '' : String(offset + limit) });
    }
    return json(400, { error: 'kind is people, deals, notes, tasks or investors' });
  } catch (e) {
    console.error('[crm-export]', kind, e.message);
    return json(502, { error: 'could not read ' + kind });
  }
};

/*
  Baker 1031 — Attio CRM helper (REST API v2, https://docs.attio.com)

  Env: ATTIO_API_KEY            single-workspace access token (Workspace settings → Developers → create an
                                integration → access token). Scopes: record_permission:read-write,
                                object_configuration:read, note:read-write, list_entry:read-write (optional),
                                user_management:read (only to auto-pick a deal owner).
       ATTIO_DEAL_OWNER         email of the workspace member who owns website deals (Jerry). Optional —
                                without it the first workspace member is used; if none can be found, no deal is
                                created and the person + note still land.
       ATTIO_DEAL_STAGE         status title for new website deals (default "Lead").
       ATTIO_DEALS=off          skip deals entirely.
       ATTIO_LIST               api_slug (or id) of a list to add each new lead to (optional).

  People are upserted by email. Custom attributes are optional: any person or deal attribute whose title
  matches one of the labels below is filled in; attributes that don't exist are skipped, and the complete
  submission always lands as a note.
*/
const API = 'https://api.attio.com/v2';

export const configured = () => !!process.env.ATTIO_API_KEY;

export async function attio(path, method = 'GET', body) {
  const key = process.env.ATTIO_API_KEY;
  if (!key) throw new Error('ATTIO_API_KEY not set');
  const r = await fetch(API + path, {
    method,
    headers: { Authorization: `Bearer ${key}`, 'content-type': 'application/json', accept: 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
  if (!r.ok) {
    const err = new Error(`Attio ${method} ${path} → ${r.status}: ${(data && (data.message || data.error)) || text.slice(0, 200)}`);
    err.status = r.status; err.body = data;
    throw err;
  }
  return data;
}

// ---- attribute metadata (cached per warm container) ------------------------------------------------
const attrCache = {};   // object slug -> [{slug, title, type, multi}]
export async function attributes(object) {
  if (attrCache[object]) return attrCache[object];
  const res = await attio(`/objects/${object}/attributes?limit=500`);
  attrCache[object] = (res.data || []).map((a) => ({
    slug: a.api_slug, title: String(a.title || ''), type: a.type, multi: !!a.is_multiselect,
  }));
  return attrCache[object];
}

const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

// [[label, value], ...] -> { api_slug: value } for the attributes that exist, with type-aware formatting.
// `strict=false` leaves out select/status attributes (whose options must already exist) — used as the retry
// when Attio rejects a batch because an option title is unknown.
export function mapValues(attrs, pairs, { strict = true } = {}) {
  const out = {};
  for (const [label, value] of pairs) {
    if (value == null || value === '' || (Array.isArray(value) && !value.length)) continue;
    const a = attrs.find((x) => norm(x.title) === norm(label) || x.slug === label);
    if (!a) continue;
    switch (a.type) {
      case 'text': out[a.slug] = Array.isArray(value) ? value.join(', ') : String(value); break;
      case 'number': { const n = Number(String(value).replace(/[^0-9.-]/g, '')); if (!Number.isNaN(n)) out[a.slug] = n; break; }
      case 'currency': { const n = Number(String(value).replace(/[^0-9.-]/g, '')); if (!Number.isNaN(n)) out[a.slug] = { currency_value: n }; break; }
      case 'date': { const d = String(value).slice(0, 10); if (/^\d{4}-\d{2}-\d{2}$/.test(d)) out[a.slug] = d; break; }
      case 'timestamp': { const t = new Date(value); if (!Number.isNaN(t.getTime())) out[a.slug] = t.toISOString(); break; }
      case 'checkbox': out[a.slug] = value === true || value === 'true' || value === 'yes'; break;
      case 'select': if (strict) out[a.slug] = a.multi ? [].concat(value).map(String) : String(Array.isArray(value) ? value[0] : value); break;
      case 'status': if (strict) out[a.slug] = String(value); break;
      default: break; // references, locations, etc. are not written from the form
    }
  }
  return out;
}

// ---- people -----------------------------------------------------------------------------------------
export function e164(phone, region) {
  const raw = String(phone || '').trim();
  if (!raw) return null;
  if (/^\+\d{8,15}$/.test(raw.replace(/[\s().-]/g, ''))) return raw.replace(/[\s().-]/g, '');
  const d = raw.replace(/\D/g, '');
  if (d.length === 10 && (!region || region === 'US')) return '+1' + d;
  if (d.length === 11 && d.startsWith('1')) return '+' + d;
  return null;
}

export async function upsertPerson(lead) {
  const values = {
    email_addresses: [{ email_address: String(lead.email).trim().toLowerCase() }],
    name: [{ first_name: lead.firstName || '', last_name: lead.lastName || '', full_name: [lead.firstName, lead.lastName].filter(Boolean).join(' ') }],
  };
  const phone = e164(lead.phone, lead.phoneRegion);
  if (phone) values.phone_numbers = [{ original_phone_number: phone }];
  const res = await attio('/objects/people/records?matching_attribute=email_addresses', 'PUT', { data: { values } });
  return res.data;
}

export async function findPersonByEmail(email) {
  if (!email) return null;
  try {
    const res = await attio('/objects/people/records/query', 'POST', { filter: { email_addresses: String(email).trim().toLowerCase() }, limit: 1 });
    return (res.data || [])[0] || null;
  } catch (e) { console.error('[attio] find by email:', e.message); return null; }
}

export async function getPerson(recordId) {
  const res = await attio(`/objects/people/records/${recordId}`);
  return res.data;
}

/* Every person matching a filter, paged. The scheduled reconcile uses this to pull the whole
   access-flagged population in a handful of requests instead of one query per investor row. */
export async function queryPeople(filter, { pageSize = 500, maxPages = 20 } = {}) {
  const out = [];
  for (let page = 0; page < maxPages; page++) {
    const res = await attio('/objects/people/records/query', 'POST', {
      filter, limit: pageSize, offset: page * pageSize,
    });
    const batch = res.data || [];
    out.push(...batch);
    if (batch.length < pageSize) break;
  }
  return out;
}

/* Deals by id, memoised for the life of the container. reconcileAll looks the same deal up for
   several people, and a warm container keeps them between runs. */
const dealCache = new Map();
export async function getDeal(id) {
  if (dealCache.has(id)) return dealCache.get(id);
  try {
    const d = (await attio(`/objects/deals/records/${id}`)).data;
    dealCache.set(id, d);
    return d;
  } catch (e) { console.error('[attio] get deal:', e.message); dealCache.set(id, null); return null; }
}

/* openDeal, but for a person record already in hand: no second fetch of the person. */
export async function openDealFrom(personRecord) {
  const ids = (personRecord?.values?.associated_deals || []).map((v) => v.target_record_id).filter(Boolean);
  let best = null;
  for (const id of ids) {
    const d = await getDeal(id);
    if (!d) continue;
    const stage = d.values?.stage?.[0]?.status?.title || '';
    if (/won|lost/i.test(stage)) continue;
    if (!best || new Date(d.created_at) > new Date(best.created_at)) best = d;
  }
  return best;
}

// flatten an Attio record's values to { slug: first value (or array for multiselect) }
export function flatValues(record) {
  const out = {};
  for (const [slug, arr] of Object.entries(record?.values || {})) {
    const vals = (arr || []).map((v) => {
      if (v == null) return null;
      if ('email_address' in v) return v.email_address;
      if ('phone_number' in v) return v.phone_number;
      if ('full_name' in v) return v;
      if ('currency_value' in v) return v.currency_value;
      if ('option' in v) return v.option?.title ?? null;
      if ('status' in v) return v.status?.title ?? null;
      if ('target_record_id' in v) return v.target_record_id;
      if ('value' in v) return v.value;
      return v;
    }).filter((x) => x !== null && x !== undefined);
    out[slug] = vals.length > 1 ? vals : vals[0] ?? null;
  }
  return out;
}

// Write custom attributes by label. Never throws: an unknown select option makes Attio reject the whole
// batch, so the retry drops select/status values and keeps the rest.
export async function setValues(object, recordId, pairs) {
  const attrs = await attributes(object);
  let values = mapValues(attrs, pairs);
  if (!Object.keys(values).length) return {};
  try {
    await attio(`/objects/${object}/records/${recordId}`, 'PATCH', { data: { values } });
  } catch (e) {
    console.error(`[attio] ${object} values rejected (${e.message}); retrying without select values`);
    values = mapValues(attrs, pairs, { strict: false });
    if (Object.keys(values).length) {
      try { await attio(`/objects/${object}/records/${recordId}`, 'PATCH', { data: { values } }); }
      catch (e2) { console.error('[attio] values retry failed:', e2.message); return {}; }
    }
  }
  return values;
}

// ---- notes ------------------------------------------------------------------------------------------
export async function addNote(object, recordId, title, content, format = 'markdown') {
  return attio('/notes', 'POST', { data: { parent_object: object, parent_record_id: recordId, title, format, content: content.slice(0, 20000) } });
}

// ---- deals ------------------------------------------------------------------------------------------
let ownerCache = null;
async function dealOwner() {
  if (process.env.ATTIO_DEAL_OWNER) return { workspace_member_email_address: process.env.ATTIO_DEAL_OWNER };
  if (ownerCache) return ownerCache;
  try {
    const res = await attio('/workspace_members');
    const m = (res.data || []).find((x) => x.access_level === 'admin') || (res.data || [])[0];
    if (m) ownerCache = { referenced_actor_type: 'workspace-member', referenced_actor_id: m.id?.workspace_member_id || m.id };
  } catch (e) { console.error('[attio] workspace members:', e.message); }
  return ownerCache;
}

export async function createDeal({ name, value, personId, pairs = [] }) {
  if (String(process.env.ATTIO_DEALS || '').toLowerCase() === 'off') return null;
  const owner = await dealOwner();
  if (!owner) { console.error('[attio] no deal owner (set ATTIO_DEAL_OWNER) — deal skipped'); return null; }
  const attrs = await attributes('deals');
  const values = {
    name, stage: process.env.ATTIO_DEAL_STAGE || 'Lead', owner: [owner],
    associated_people: [{ target_object: 'people', target_record_id: personId }],
    ...(value ? { value: { currency_value: value } } : {}),
    ...mapValues(attrs, pairs),
  };
  try {
    const res = await attio('/objects/deals/records', 'POST', { data: { values } });
    return res.data;
  } catch (e) {
    // custom attribute batch rejected? retry with the core fields only
    console.error('[attio] deal create:', e.message);
    if (!pairs.length) return null;
    const core = { name, stage: values.stage, owner: values.owner, associated_people: values.associated_people, ...(value ? { value: { currency_value: value } } : {}) };
    try { return (await attio('/objects/deals/records', 'POST', { data: { values: core } })).data; }
    catch (e2) { console.error('[attio] deal create retry:', e2.message); return null; }
  }
}

// most recent deal linked to the person that is not Won/Lost
export async function openDeal(personId) {
  try {
    const person = await getPerson(personId);
    const ids = (person.values?.associated_deals || []).map((v) => v.target_record_id).filter(Boolean);
    let best = null;
    for (const id of ids) {
      const d = (await attio(`/objects/deals/records/${id}`)).data;
      const stage = d.values?.stage?.[0]?.status?.title || '';
      if (/won|lost/i.test(stage)) continue;
      if (!best || new Date(d.created_at) > new Date(best.created_at)) best = d;
    }
    return best;
  } catch (e) { console.error('[attio] open deal:', e.message); return null; }
}

export async function updateDeal(dealId, { name, value, pairs = [] }) {
  const attrs = await attributes('deals');
  const values = { ...(name ? { name } : {}), ...(value ? { value: { currency_value: value } } : {}), ...mapValues(attrs, pairs) };
  if (!Object.keys(values).length) return;
  try { await attio(`/objects/deals/records/${dealId}`, 'PATCH', { data: { values } }); }
  catch (e) {
    console.error('[attio] deal update:', e.message);
    const core = { ...(name ? { name } : {}), ...(value ? { value: { currency_value: value } } : {}), ...mapValues(attrs, pairs, { strict: false }) };
    try { await attio(`/objects/deals/records/${dealId}`, 'PATCH', { data: { values: core } }); } catch (e2) { console.error('[attio] deal update retry:', e2.message); }
  }
}

// ---- lists ------------------------------------------------------------------------------------------
export async function addToList(personId) {
  const list = process.env.ATTIO_LIST;
  if (!list) return;
  try {
    await attio(`/lists/${list}/entries`, 'POST', { data: { parent_object: 'people', parent_record_id: personId, entry_values: {} } });
  } catch (e) {
    if (e.status === 409) return; // already on the list
    console.error('[attio] list entry:', e.message);
  }
}

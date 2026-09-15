#!/usr/bin/env node
/*
  Baker 1031 — one-time import of the two GoHighLevel accounts into Attio.

  Reads the merged export (263 people, 193 opportunities, 1,364 notes — the two GHL accounts combined
  with duplicates removed) and writes it into Attio: people upserted by email, deals created on the
  website pipeline and linked to their person, every GHL note carried across, and every custom field
  mapped to an Attio attribute (creating the ones that don't exist yet).

  Run it from the repo root, with the key in the shell rather than in a file:

      read -s ATTIO_API_KEY
      export ATTIO_API_KEY && echo "length: ${#ATTIO_API_KEY}"
      node build/attio-import.mjs --dry        # plan: what would be created, nothing written
      node build/attio-import.mjs              # import

  It is resumable and safe to re-run: every record and note it writes is recorded in
  build/.attio-import-state.json, and a second run picks up where the last one stopped and skips
  everything already done. Interrupt it with Ctrl-C whenever you like.

  Options:
      --dry              plan only
      --contacts=PATH    default build/ghl-contacts.json
      --deals=PATH       default build/ghl-opportunities.json
      --only=attrs|people|deals      run one phase
      --notes=off        skip notes
      --limit=N          first N records of each phase (for a trial run)

  Env: ATTIO_API_KEY (required), ATTIO_DEAL_OWNER (workspace member email that owns imported deals).
*/
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const API = 'https://api.attio.com/v2';
const KEY = process.env.ATTIO_API_KEY;
const argv = process.argv.slice(2);
const flag = (n, d) => { const a = argv.find((x) => x.startsWith(`--${n}=`)); return a ? a.slice(n.length + 3) : d; };
const DRY = argv.includes('--dry');
const ONLY = flag('only', '');
const NOTES = flag('notes', 'on') !== 'off';
const LIMIT = Number(flag('limit', '0')) || 0;
const CONTACTS = flag('contacts', path.join(HERE, 'ghl-contacts.json'));
const DEALS = flag('deals', path.join(HERE, 'ghl-opportunities.json'));
const STATE_FILE = path.join(HERE, '.attio-import-state.json');

if (!KEY) { console.error('ATTIO_API_KEY is not set. Run:  read -s ATTIO_API_KEY   then   export ATTIO_API_KEY'); process.exit(1); }
for (const f of [CONTACTS, DEALS]) if (!fs.existsSync(f)) { console.error(`missing data file: ${f}`); process.exit(1); }

// ---- state -------------------------------------------------------------------------------------
const state = fs.existsSync(STATE_FILE) ? JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')) : { people: {}, deals: {}, notes: {} };
for (const k of ['people', 'deals', 'notes']) state[k] = state[k] || {};
let dirty = false;
const save = () => { if (dirty && !DRY) { fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 1)); dirty = false; } };
setInterval(save, 5000).unref();
process.on('SIGINT', () => { save(); console.log('\ninterrupted — progress saved, re-run to continue'); process.exit(130); });

// ---- http --------------------------------------------------------------------------------------
let calls = 0;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function api(p, method = 'GET', body, tries = 0) {
  calls++;
  let r;
  try {
    r = await fetch(API + p, {
      method,
      headers: { Authorization: `Bearer ${KEY}`, 'content-type': 'application/json', accept: 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    // the connection itself failed (dropped wifi, DNS hiccup, reset socket) — worth another go
    if (tries >= 8) throw new Error(`${method} ${p} → network error after ${tries} retries: ${err.message}`);
    const wait = Math.min(20000, 1000 * 2 ** tries);
    if (tries === 0) process.stdout.write(`   (connection dropped on ${method} ${p} — retrying)\n`);
    await sleep(wait);
    return api(p, method, body, tries + 1);
  }
  if (r.status === 429 || r.status >= 500) {
    if (tries >= 8) throw new Error(`${method} ${p} → ${r.status} after ${tries} retries`);
    const wait = Number(r.headers.get('retry-after')) * 1000 || Math.min(30000, 800 * 2 ** tries);
    await sleep(wait);
    return api(p, method, body, tries + 1);
  }
  const text = await r.text();
  let data = null; try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
  if (!r.ok) {
    const detail = data?.validation_errors?.length
      ? ' ' + JSON.stringify(data.validation_errors).slice(0, 300)
      : '';
    const e = new Error(`${method} ${p} → ${r.status}: ${(data && (data.message || data.error)) || text.slice(0, 200)}${detail}`);
    e.status = r.status; e.body = data; throw e;
  }
  await sleep(35);
  return data;
}
const slugify = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 45);

// ---- the shape of the GHL data in Attio ----------------------------------------------------------
// GHL custom-field / contact-field title -> Attio attribute type. Anything not listed becomes text.
const TYPES = {
  'Total Investment Size': 'currency', 'Anticipated Investment': 'currency', Equity: 'currency', Debt: 'currency',
  'Exchange Equity': 'currency', 'Replacement Debt': 'currency', 'Cash Amount': 'currency',
  'In-Place LTV %': 'number',
  'CRS Delivery Date': 'date', 'Closing Date': 'date', '45-Day Deadline': 'date', '180-Day Deadline': 'date', 'Sale Date': 'date',
  'Acknowledgments Timestamp': 'timestamp', 'GHL Created': 'timestamp', 'GHL Updated': 'timestamp',
  'Do Not Disturb': 'checkbox',
};
// contact fields that are not GHL custom fields but still worth keeping
const PERSON_EXTRA = (p) => ({
  'Preferred Name': p.customFields?.['Preferred Name'] || null,
  'Company Name': p.companyName || null,
  Address: [p.address, p.city, p.state, p.postalCode, p.country].filter(Boolean).join(', ') || null,
  Website: p.website || null,
  Tags: (p.tags || []).join(', ') || null,
  'Contact Type': p.type || null,
  'Do Not Disturb': p.dnd === true,
  'Lead Source': [p.source, p.attribution?.sessionSource, p.attribution?.medium].filter(Boolean).join(' / ') || null,
  'Landing Page': p.attribution?.url || null,
  'GHL Account': (p.sources || []).map((s) => s.location).join(' + ') || null,
  'Phone (unparsed)': (p.phones || []).filter((x) => x && !e164(x)).join(', ') || null,
  'GHL Contact ID': (p.ghlIds || []).join(', ') || null,
  'GHL Created': p.dateAdded || null,
  'GHL Updated': p.dateUpdated || null,
});
const DEAL_EXTRA = (d) => ({
  'GHL Status': d.status || null,
  'GHL Pipeline': (d.sources || []).map((s) => s.pipeline).filter(Boolean).join(' + ') || null,
  'GHL Created': d.createdAt || null,
  'GHL Updated': d.updatedAt || null,
});
// a handful of legacy values that are the same thing the website already offers, spelled differently
const NORMALIZE = {
  'Marital Status': { Divorced: 'Divorced or separated', Separated: 'Divorced or separated', 'Domestic Partnership': 'Domestic partnership' },
  'Net Worth Range': { '$10M+': '$10,000,000 or more', '$5M–$9.99M': '$5,000,000 – $9,999,999', '$2.5M–$4.99M': '$2,500,000 – $4,999,999' },
};
const STATUS_STAGE = { won: 'Won', lost: 'Lost', abandoned: 'Lost' };

const clean = (v) => {
  if (v === null || v === undefined) return null;
  if (Array.isArray(v)) { const s = v.filter((x) => x !== null && x !== '').join(', '); return s || null; }
  const s = String(v).replace(/\|/g, ', ').trim();
  return s === '' ? null : s;
};
const normalize = (title, v) => (NORMALIZE[title] && NORMALIZE[title][v]) || v;

// A North-American number Attio will accept: area code and exchange both start 2-9.
const nanp = (d) => (/^[2-9]\d{2}[2-9]\d{6}$/.test(d) ? '+1' + d : null);
function e164(phone) {
  const raw = String(phone || '').trim();
  if (!raw) return null;
  const compact = raw.replace(/[\s().-]/g, '');
  const d = compact.replace(/\D/g, '');
  if (compact.startsWith('+1') || (!compact.startsWith('+') && (d.length === 10 || (d.length === 11 && d[0] === '1')))) {
    return nanp(d.length === 11 && d[0] === '1' ? d.slice(1) : d);   // null for impossible US numbers
  }
  if (/^\+\d{8,15}$/.test(compact)) return compact;                 // international, left as given
  return null;
}

// ---- load --------------------------------------------------------------------------------------
const people = JSON.parse(fs.readFileSync(CONTACTS, 'utf8'));
const deals = JSON.parse(fs.readFileSync(DEALS, 'utf8'));
const personFields = (p) => ({ ...Object.fromEntries(Object.entries(p.customFields || {}).map(([k, v]) => [k, clean(v)])), ...PERSON_EXTRA(p) });
const dealFields = (d) => ({ ...Object.fromEntries(Object.entries(d.customFields || {}).map(([k, v]) => [k, clean(v)])), ...DEAL_EXTRA(d) });

// ---- attributes ---------------------------------------------------------------------------------
const attrCache = {};
async function attributes(object, refresh = false) {
  if (!refresh && attrCache[object]) return attrCache[object];
  const res = await api(`/objects/${object}/attributes?limit=500`);
  attrCache[object] = (res.data || []).map((a) => ({
    id: a.id.attribute_id, slug: a.api_slug, title: String(a.title || ''), type: a.type, multi: !!a.is_multiselect,
  }));
  return attrCache[object];
}
const findAttr = (attrs, title) => attrs.find((a) => a.title.toLowerCase() === String(title).toLowerCase());

async function ensureAttributes() {
  const plan = { created: [], options: [], failed: [] };
  for (const [object, rows, shape] of [['people', people, personFields], ['deals', deals, dealFields]]) {
    const wanted = new Map();                    // title -> Set of values seen
    for (const r of rows) for (const [k, v] of Object.entries(shape(r))) {
      if (v === null || v === undefined || v === '') continue;
      if (!wanted.has(k)) wanted.set(k, new Set());
      wanted.get(k).add(normalize(k, v));
    }
    let attrs = await attributes(object, true);
    for (const [title, values] of wanted) {
      let a = findAttr(attrs, title);
      if (!a) {
        const type = TYPES[title] || 'text';
        if (!DRY) {
          const body = { data: { title, description: `Imported from GoHighLevel`, api_slug: slugify(title), type, is_required: false, is_unique: false, is_multiselect: false, default_value: null, config: {} } };
          if (type === 'currency') body.data.config = { currency: { default_currency_code: 'USD', display_type: 'symbol' } };
          try {
            const created = await api(`/objects/${object}/attributes`, 'POST', body);
            a = { id: created.data.id.attribute_id, slug: created.data.api_slug, title, type, multi: false };
            attrs.push(a);
            plan.created.push(`${object}.${title} (${type})`);
          } catch (e) {
            plan.failed.push(`${object}.${title} (${type}) — ${e.message.slice(0, 180)}`);
          }
        } else plan.created.push(`${object}.${title} (${type})`);
        continue;
      }
      if (a.type === 'select') {                 // an existing select needs every incoming value as an option
        const have = new Set(((await api(`/objects/${object}/attributes/${a.id}/options`)).data || [])
          .filter((o) => !o.is_archived).map((o) => o.title));
        for (const v of values) {
          for (const one of a.multi ? String(v).split(', ') : [String(v)]) {
            if (have.has(one) || !one) continue;
            have.add(one);
            plan.options.push(`${object}.${title} → "${one}"`);
            if (!DRY) await api(`/objects/${object}/attributes/${a.id}/options`, 'POST', { data: { title: one } });
          }
        }
      }
    }
    await attributes(object, true);
  }
  console.log(`attributes: ${plan.created.length} ${DRY ? 'would be created' : 'created'}, ${plan.options.length} select options ${DRY ? 'would be added' : 'added'}`);
  for (const x of plan.created) console.log('   +', x);
  if (plan.failed.length) {
    console.log(`   ${plan.failed.length} attribute(s) Attio would not create — their values are skipped, everything else still imports:`);
    for (const x of plan.failed) console.log('   !', x);
  }
  if (plan.options.length) console.log('   ' + plan.options.length + ' option(s): ' + plan.options.slice(0, 12).join('; ') + (plan.options.length > 12 ? ' …' : ''));
  // stages
  try {
    const st = ((await api('/objects/deals/attributes/stage/statuses')).data || []).filter((s) => !s.is_archived).map((s) => s.title);
    const need = [...new Set(deals.map((d) => STATUS_STAGE[d.status] || d.stage))].filter((s) => s && !st.includes(s));
    for (const s of need) {
      console.log(`   ${DRY ? 'would add' : 'add'} deal stage "${s}"`);
      if (!DRY) await api('/objects/deals/attributes/stage/statuses', 'POST', { data: { title: s, celebration_enabled: false } });
    }
  } catch (e) { console.log('   deal stages:', e.message); }
}

// ---- value mapping --------------------------------------------------------------------------------
function values(attrs, fields) {
  const out = {};
  for (const [title, raw] of Object.entries(fields)) {
    if (raw === null || raw === undefined || raw === '') continue;
    const a = findAttr(attrs, title);
    if (!a) continue;
    const v = normalize(title, raw);
    switch (a.type) {
      case 'text': out[a.slug] = String(v); break;
      case 'number': { const n = Number(String(v).replace(/[^0-9.-]/g, '')); if (!Number.isNaN(n)) out[a.slug] = n; break; }
      case 'currency': { const n = Number(String(v).replace(/[^0-9.-]/g, '')); if (!Number.isNaN(n)) out[a.slug] = { currency_value: n }; break; }
      case 'date': { const d = String(v).slice(0, 10); if (/^\d{4}-\d{2}-\d{2}$/.test(d)) out[a.slug] = d; break; }
      case 'timestamp': { const t = new Date(v); if (!Number.isNaN(t.getTime())) out[a.slug] = t.toISOString(); break; }
      case 'checkbox': out[a.slug] = v === true || v === 'true' || v === 'Yes' || v === 'yes'; break;
      case 'select': out[a.slug] = a.multi ? String(v).split(', ').filter(Boolean) : String(v); break;
      case 'status': out[a.slug] = String(v); break;
      default: break;
    }
  }
  return out;
}

// ---- notes ----------------------------------------------------------------------------------------
async function addNotes(object, recordId, notes, who) {
  let n = 0;
  for (const note of notes || []) {
    const id = note.id || `${who}:${(note.body || '').slice(0, 40)}`;
    if (state.notes[id]) continue;
    const when = (note.dateAdded || '').slice(0, 10);
    const title = `GoHighLevel note${when ? ' — ' + when : ''}`;
    if (DRY) state.notes[id] = true;   // never saved in a dry run; keeps the count honest
    else {
      await api('/notes', 'POST', { data: { parent_object: object, parent_record_id: recordId, title, format: 'plaintext', content: String(note.body || '').slice(0, 20000), created_at: note.dateAdded || undefined } });
      state.notes[id] = true; dirty = true;
    }
    n++;
  }
  return n;
}

// ---- people ------------------------------------------------------------------------------------------
async function importPeople() {
  const attrs = await attributes('people');
  let created = 0, skipped = 0, noteCount = 0, failed = 0;
  const rows = LIMIT ? people.slice(0, LIMIT) : people;
  for (const [i, p] of rows.entries()) {
    const key = p.key || p.emails[0] || p.fullName;
    try {
      let rid = state.people[key];
      if (!rid) {
        const name = [{ first_name: p.firstName || '', last_name: p.lastName || '', full_name: [p.firstName, p.lastName].filter(Boolean).join(' ') || p.fullName || '' }];
        const core = { name };
        const emails = (p.emails || []).filter(Boolean).map((e) => ({ email_address: String(e).trim().toLowerCase() }));
        if (emails.length) core.email_addresses = emails;
        const phones = (p.phones || []).map(e164).filter(Boolean).map((n) => ({ original_phone_number: n }));
        if (phones.length) core.phone_numbers = phones;
        if (DRY) { rid = 'dry'; }
        else {
          const write = (v) => (emails.length
            ? api('/objects/people/records?matching_attribute=email_addresses', 'PUT', { data: { values: v } })
            : api('/objects/people/records', 'POST', { data: { values: v } }));
          let res;
          try { res = await write(core); }
          catch (err) {
            if (!/phone_numbers/.test(err.message)) throw err;
            const { phone_numbers, ...rest } = core;     // eslint-disable-line no-unused-vars
            console.error(`   ! ${key}: Attio rejected the phone number — importing without it`);
            res = await write(rest);
          }
          rid = res.data.id.record_id;
          state.people[key] = rid; dirty = true;
        }
        created++;
      } else skipped++;
      const vals = values(attrs, personFields(p));
      if (!DRY && Object.keys(vals).length) {
        try { await api(`/objects/people/records/${rid}`, 'PATCH', { data: { values: vals } }); }
        catch (e) { console.error(`   ! ${key}: values rejected (${e.message.slice(0, 120)})`); }
      }
      if (NOTES) noteCount += await addNotes('people', rid, p.notes, key);
    } catch (e) { failed++; console.error(`   ! ${key}: ${e.message.slice(0, 160)}`); }
    if ((i + 1) % 25 === 0) { save(); console.log(`   … ${i + 1}/${rows.length} people`); }
  }
  save();
  console.log(`people: ${created} ${DRY ? 'to create/update' : 'created or matched'}, ${skipped} already done, ${noteCount} notes${failed ? `, ${failed} failed` : ''}`);
}

// ---- deals -------------------------------------------------------------------------------------------
async function importDeals() {
  const attrs = await attributes('deals');
  // The owner has to be a real workspace member — an address that only forwards mail is rejected by Attio,
  // and every deal fails. Resolve it against the member list before writing anything.
  const members = ((await api('/workspace_members')).data || []).filter((m) => m.access_level !== 'suspended');
  const wanted = String(process.env.ATTIO_DEAL_OWNER || '').trim().toLowerCase();
  let m = wanted && members.find((x) => String(x.email_address || '').toLowerCase() === wanted);
  if (wanted && !m) {
    m = members.find((x) => x.access_level === 'admin') || members[0];
    console.log(`   ATTIO_DEAL_OWNER="${process.env.ATTIO_DEAL_OWNER}" is not a member of this Attio workspace.`);
    console.log(`   Members: ${members.map((x) => x.email_address).join(', ') || '(none)'}`);
    console.log(`   Using ${m ? m.email_address : 'no owner'} instead.`);
  } else if (!wanted) m = members.find((x) => x.access_level === 'admin') || members[0];
  const owner = m ? { referenced_actor_type: 'workspace-member', referenced_actor_id: m.id?.workspace_member_id || m.id } : null;
  if (!owner) { console.error('deals: no workspace member to own the deals — add one in Attio and re-run'); return; }
  let created = 0, skipped = 0, noteCount = 0, failed = 0, orphan = 0;
  const rows = LIMIT ? deals.slice(0, LIMIT) : deals;
  for (const [i, d] of rows.entries()) {
    const key = `${d.personKey || d.contactEmail || '?'}|${d.name}`;
    try {
      let rid = state.deals[key];
      if (!rid) {
        const personId = state.people[d.personKey] || state.people[d.contactEmail];
        if (!personId && !DRY) orphan++;
        const core = {
          name: d.name,
          stage: STATUS_STAGE[d.status] || d.stage || 'Lead',
          owner: [owner],
          ...(d.value ? { value: { currency_value: Number(d.value) } } : {}),
          ...(personId ? { associated_people: [{ target_object: 'people', target_record_id: personId }] } : {}),
          ...values(attrs, dealFields(d)),
        };
        if (DRY) rid = 'dry';
        else {
          let res;
          try { res = await api('/objects/deals/records', 'POST', { data: { values: core } }); }
          catch (e) {
            console.error(`   ! ${d.name}: ${e.message.slice(0, 120)} — retrying with core fields only`);
            const bare = { name: core.name, stage: core.stage, ...(core.value ? { value: core.value } : {}), ...(core.associated_people ? { associated_people: core.associated_people } : {}) };
            res = await api('/objects/deals/records', 'POST', { data: { values: bare } });
          }
          rid = res.data.id.record_id;
          state.deals[key] = rid; dirty = true;
        }
        created++;
      } else skipped++;
      if (NOTES) noteCount += await addNotes('deals', rid, d.notes, key);
    } catch (e) { failed++; console.error(`   ! ${d.name}: ${e.message.slice(0, 160)}`); }
    if ((i + 1) % 25 === 0) { save(); console.log(`   … ${i + 1}/${rows.length} deals`); }
  }
  save();
  console.log(`deals: ${created} ${DRY ? 'to create' : 'created'}, ${skipped} already done, ${noteCount} notes not already on the person${failed ? `, ${failed} failed` : ''}${orphan ? `, ${orphan} with no matching person` : ''}`);
}

// ---- go ------------------------------------------------------------------------------------------------
(async () => {
  console.log(`${DRY ? 'DRY RUN — nothing will be written.\n' : ''}${people.length} people, ${deals.length} deals, ` +
    `${people.reduce((n, p) => n + (p.notes || []).length, 0)} notes in the export.`);
  try { const me = await api('/self'); console.log(`workspace: ${me.workspace_name || me.workspace_id || 'ok'}`); }
  catch (e) { console.log('token check skipped:', e.message); }
  if (!ONLY || ONLY === 'attrs') await ensureAttributes();
  if (!ONLY || ONLY === 'people') await importPeople();
  if (!ONLY || ONLY === 'deals') await importDeals();
  save();
  console.log(`\n${DRY ? 'Dry run complete — nothing written.' : 'Done.'}  ${calls} API calls.`);
  if (!DRY) console.log('Progress is in build/.attio-import-state.json — re-running skips everything already imported.');
})().catch((e) => { save(); console.error('\nFailed:', e.message); if (/403|scope/i.test(e.message)) console.error('→ the token is missing a scope: Attio → Developers → your integration → enable object_configuration:read-write, record_permission:read-write and note:read-write, then re-run.'); process.exit(1); });

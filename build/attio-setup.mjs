#!/usr/bin/env node
/*
  Baker 1031 — one-time Attio workspace setup for the website integration.
  Creates (idempotently) the People and Deal attributes the site fills in, their select options, and the
  deal pipeline stages. Safe to re-run: existing attributes, options and stages are left alone.

  Run from Terminal (Node 18+), without putting the key in your shell history:
      read -s ATTIO_API_KEY && export ATTIO_API_KEY
      node build/attio-setup.mjs           # apply
      node build/attio-setup.mjs --dry     # show what would change, write nothing

  The token needs: object_configuration:read-write, record_permission:read (plus the scopes the site uses).
*/
const API = 'https://api.attio.com/v2';
const KEY = process.env.ATTIO_API_KEY;
const DRY = process.argv.includes('--dry');
if (!KEY) { console.error('ATTIO_API_KEY is not set. Run:  read -s ATTIO_API_KEY && export ATTIO_API_KEY'); process.exit(1); }

async function api(path, method = 'GET', body) {
  const r = await fetch(API + path, { method, headers: { Authorization: `Bearer ${KEY}`, 'content-type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  const text = await r.text(); let data = null; try { data = JSON.parse(text); } catch { data = { raw: text }; }
  if (!r.ok) throw new Error(`${method} ${path} → ${r.status}: ${data?.message || text.slice(0, 200)}`);
  return data;
}
const slug = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');

// ---- what the site writes (titles must match lib/lead-shape.mjs / my-info.mjs / portal-sync.mjs) ----------
const PEOPLE = [
  { title: 'Role (This Transaction)', type: 'text', description: 'From the website registration: who the person is in the transaction (Investor, Realtor…, Other: …)' },
  { title: 'Marital Status', type: 'select', options: ['Single', 'Married', 'Domestic partnership', 'Divorced or separated', 'Widowed'] },
  { title: 'Net Worth Range', type: 'select', options: ['Under $1,000,000', '$1,000,000 – $2,499,999', '$2,500,000 – $4,999,999', '$5,000,000 – $9,999,999', '$10,000,000 or more'], description: 'Excluding primary residence, as selected on the website' },
  { title: 'Household Income', type: 'select', options: ['Under $200,000', '$200,000 – $299,999', '$300,000 – $499,999', '$500,000 – $999,999', '$1,000,000 or more'] },
  { title: 'Accredited Signal', type: 'select', options: ['Indicated', 'Unclear'], description: 'Indicated when the ranges given meet the accredited-investor thresholds' },
  { title: 'Exchange Fit', type: 'text', description: '1031 situation from the website ("Yes — in 45-day identification period", or "No: <what they want>")' },
  { title: 'Lead Source', type: 'text' },
  { title: 'Acknowledgments Timestamp', type: 'timestamp', description: 'When the four registration acknowledgments (incl. Form CRS) were accepted' },
  { title: 'Update Link', type: 'text', description: 'Personal update-my-info link (signed; sent in reminder emails)' },
  { title: 'Intro Invite Status', type: 'text', description: 'Set by the site when the scheduling invite / fix-your-info notice is emailed — prevents duplicates' },
  { title: 'Portal Access', type: 'select', options: ['Yes', 'No'], description: 'Yes = approved for the investor portal (synced to Airtable + welcome email); No = revoked' },
  { title: 'Closing Date', type: 'date', description: 'Sale closing date (day the 45/180-day clocks start)' },
  { title: '45-Day Deadline', type: 'date' },
  { title: '180-Day Deadline', type: 'date' },
];
const DEALS = [
  { title: 'Deal Type', type: 'select', options: ['1031', '1033', 'Cash'] },
  { title: 'Sale Date', type: 'date' },
  { title: '45-Day Deadline', type: 'date' },
  { title: '180-Day Deadline', type: 'date' },
  { title: 'Exchange Equity', type: 'currency' },
  { title: 'Replacement Debt', type: 'currency' },
  { title: 'Cash Amount', type: 'currency' },
  { title: 'Exchange Fit', type: 'text' },
  { title: 'Objectives', type: 'text' },
];
// Pipeline (deal "stage" statuses), in order. The two closed stages keep Attio's defaults.
const STAGES = ['Lead', 'Intro Call Scheduled', 'Reviewing Opportunities', 'Actively Reviewing', 'Completing Paperwork', 'Closing'];
const RENAME = { 'In Progress': 'Intro Call Scheduled' };   // Attio's default second stage → our first live stage

async function ensureAttributes(object, wanted) {
  const existing = (await api(`/objects/${object}/attributes?limit=500`)).data || [];
  const byTitle = (t) => existing.find((a) => a.title.toLowerCase() === t.toLowerCase());
  for (const w of wanted) {
    let attr = byTitle(w.title);
    if (!attr) {
      const body = { data: { title: w.title, description: w.description || null, api_slug: slug(w.title), type: w.type, is_required: false, is_unique: false, is_multiselect: false, default_value: null, config: {} } };
      if (w.type === 'currency') body.data.config = { currency: { default_currency_code: 'USD', display_type: 'symbol' } };
      console.log(`${DRY ? '[dry] would create' : 'create'} ${object}.${w.title} (${w.type})`);
      if (!DRY) attr = (await api(`/objects/${object}/attributes`, 'POST', body)).data;
    } else {
      console.log(`ok     ${object}.${w.title} (${attr.type})${attr.type !== w.type ? `  ← exists as ${attr.type}, expected ${w.type}; the site adapts to the existing type` : ''}`);
    }
    if (w.options && attr && (attr.type === 'select')) {
      const opts = (await api(`/objects/${object}/attributes/${attr.id.attribute_id}/options`)).data || [];
      const have = new Set(opts.filter((o) => !o.is_archived).map((o) => o.title));
      for (const o of w.options) {
        if (have.has(o)) continue;
        console.log(`${DRY ? '[dry] would add' : 'add'}    option "${o}" → ${object}.${w.title}`);
        if (!DRY) await api(`/objects/${object}/attributes/${attr.id.attribute_id}/options`, 'POST', { data: { title: o } });
      }
    }
  }
}

async function ensureStages() {
  let statuses;
  try { statuses = (await api('/objects/deals/attributes/stage/statuses')).data || []; }
  catch (e) { console.log('deals: cannot read stages —', e.message, '\n       → enable the Deals object first (Attio → Settings → Objects → Deals).'); return; }
  const live = statuses.filter((s) => !s.is_archived);
  const titles = () => live.map((s) => s.title);
  for (const [from, to] of Object.entries(RENAME)) {
    const s = live.find((x) => x.title === from);
    if (s && !live.find((x) => x.title === to)) {
      console.log(`${DRY ? '[dry] would rename' : 'rename'} stage "${from}" → "${to}"`);
      if (!DRY) await api(`/objects/deals/attributes/stage/statuses/${s.id.status_id}`, 'PATCH', { data: { title: to } });
      s.title = to;
    }
  }
  for (const t of STAGES) {
    if (titles().includes(t)) { console.log(`ok     stage "${t}"`); continue; }
    console.log(`${DRY ? '[dry] would add' : 'add'}    stage "${t}"`);
    if (!DRY) { const c = (await api('/objects/deals/attributes/stage/statuses', 'POST', { data: { title: t, celebration_enabled: false } })).data; live.push(c); }
  }
  const closed = live.filter((s) => /won|lost/i.test(s.title)).map((s) => s.title);
  console.log(`pipeline: ${[...STAGES, ...closed].join(' → ')}`);
  console.log('       (drag to reorder in Attio → Deals → board view if the order differs)');
}

(async () => {
  try {
    const me = await api('/self');
    console.log(`Attio workspace: ${me.workspace_name || me.workspace_id || 'ok'}${me.active === false ? '  (token reported INACTIVE)' : ''}`);
  } catch (e) { console.log('token check skipped:', e.message); }
  const objs = (await api('/objects')).data || [];
  if (!objs.some((o) => o.api_slug === 'deals')) console.log('NOTE: the Deals object is not enabled — enable it in Attio → Settings → Objects, then re-run for the deal fields and stages.');
  console.log('\nPeople attributes'); await ensureAttributes('people', PEOPLE);
  if (objs.some((o) => o.api_slug === 'deals')) {
    console.log('\nDeal attributes'); await ensureAttributes('deals', DEALS);
    console.log('\nDeal stages'); await ensureStages();
  }
  console.log(DRY ? '\nDry run — nothing written.' : '\nDone.');
})().catch((e) => { console.error('\nFailed:', e.message); if (/403|scope/i.test(e.message)) console.error('→ the token is missing a scope: open the integration in Attio → Developers and enable object_configuration:read-write, then re-run.'); process.exit(1); });

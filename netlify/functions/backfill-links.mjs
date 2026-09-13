/*
  Baker 1031 — one-shot/utility backfill of self-service update links
  (/.netlify/functions/backfill-links?key=<PORTAL_SYNC_KEY>)

  Contacts who registered through the new request-access form get a personal
  "Update Link" (signed /update-my-info/ URL) stamped by lead.mjs. Contacts
  migrated from the legacy CRM predate the feature and have the field empty,
  so {{contact.update_link}} merges blank for them in GHL emails. This walks
  every contact in the location and fills the field where it's missing.

  Sync-function friendly: processes a slice per invocation and returns a
  cursor; call repeatedly until {done:true}. Idempotent — existing links
  (which embed the contact's own id) are left untouched.

  Params: key (required) · dry=1 (count only) · startAfterId/startAfter
  (cursor from the previous response) · max (updates per call, default 20)
*/
import crypto from 'node:crypto';

const API = 'https://services.leadconnectorhq.com';
const json = (s, b) => ({ statusCode: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(b) });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export const handler = async (event) => {
  const q = (event && event.queryStringParameters) || {};
  if (!process.env.PORTAL_SYNC_KEY || q.key !== process.env.PORTAL_SYNC_KEY) return json(403, { error: 'forbidden' });
  const dry = q.dry === '1';
  const maxUpdates = Math.min(parseInt(q.max || '20', 10) || 20, 50);
  const loc = process.env.GHL_LOCATION_ID;
  const gh = { Authorization: `Bearer ${process.env.GHL_Key}`, Version: '2021-07-28', 'content-type': 'application/json' };
  const base = process.env.URL || 'https://baker1031.com';

  try {
    // Resolve the "Update Link" contact custom field id.
    const fr = await fetch(`${API}/locations/${loc}/customFields?model=contact`, { headers: gh });
    if (!fr.ok) return json(502, { error: `fields ${fr.status}` });
    const linkField = ((await fr.json()).customFields || []).find((f) => /^update link$/i.test(f.name || ''));
    if (!linkField) return json(500, { error: 'no "Update Link" contact field in this location' });

    let startAfterId = q.startAfterId || undefined;
    let startAfter = q.startAfter || undefined;
    let scanned = 0, updated = 0, already = 0, failed = 0, done = false;
    let lastId = null, lastStamp = null; // cursor of the last contact actually processed

    while (updated < maxUpdates) {
      const u = new URL(`${API}/contacts/`);
      u.searchParams.set('locationId', loc);
      u.searchParams.set('limit', '100');
      if (startAfterId) { u.searchParams.set('startAfterId', startAfterId); u.searchParams.set('startAfter', startAfter); }
      const r = await fetch(u, { headers: gh });
      if (!r.ok) return json(502, { error: `contacts ${r.status}` });
      const d = await r.json();
      const contacts = d.contacts || [];
      if (!contacts.length) { done = true; break; }

      for (const c of contacts) {
        scanned++;
        lastId = c.id; lastStamp = String(new Date(c.dateAdded || Date.now()).getTime());
        const existing = (c.customFields || []).find((f) => f.id === linkField.id);
        if (existing && typeof existing.value === 'string' && existing.value.startsWith('http')) { already++; continue; }
        if (dry) { updated++; continue; }
        const sig = crypto.createHmac('sha256', process.env.SESSION_SECRET || '').update('myinfo:' + c.id).digest('hex').slice(0, 32);
        const link = `${base}/update-my-info/?cid=${c.id}&sig=${sig}`;
        for (let attempt = 0; attempt < 3; attempt++) {
          const put = await fetch(`${API}/contacts/${c.id}`, {
            method: 'PUT', headers: gh,
            body: JSON.stringify({ customFields: [{ id: linkField.id, field_value: link }] }),
          });
          if (put.ok) { updated++; break; }
          if (put.status === 429) { await sleep(1200); continue; }
          console.error(`[backfill-links] ${c.id} PUT ${put.status}`);
          failed++; break;
        }
        await sleep(120);
        if (updated >= maxUpdates) break;
      }

      // Resume from the last contact we actually processed, so an early break
      // at maxUpdates never skips the remainder of the current page.
      startAfterId = lastId;
      startAfter = lastStamp;
      if (contacts.length < 100 && updated < maxUpdates) { done = true; break; }
    }

    return json(200, { ok: true, dry, scanned, updated, already, failed, done,
      ...(done ? {} : { next: { startAfterId, startAfter } }) });
  } catch (e) {
    console.error('[backfill-links]', e.message);
    return json(500, { error: e.message });
  }
};

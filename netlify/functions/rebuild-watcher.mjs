/*
  Baker 1031 — Airtable → Netlify rebuild watcher
  Runs every 15 minutes (netlify.toml schedule). Compares the newest
  "Last Modified" timestamp on the Offering Data table of the Investment
  Data (Live) base against the live site's build timestamp (/build-info.json,
  written by build.js). When an offering changed after the last publish, POSTs
  the Netlify build hook so the site rebuilds from the linked GitHub repo with
  fresh Airtable data.

  This watches OFFERINGS only. An edit to Past Performance (the Results page,
  the homepage chart, the sponsor track records) does not trigger a rebuild —
  that table has no Last Modified field to compare against — so those changes
  reach the site on the next deploy from any other cause.

  Why this exists: Airtable's automation API can't create "run script"
  actions, so the site polls instead — same outcome, ~15 minute latency,
  and no manual Airtable configuration to maintain.

  Env: AIRTABLE_TOKEN (read on Investment Data (Live)), NETLIFY_BUILD_HOOK (this site's build hook URL). Manual run:
  POST ?key=<PORTAL_SYNC_KEY> (&dry=1 to report without triggering).
*/

// The Investment Data (Live) base, same source the build reads. Note these are AIRTABLE_BASE_ID /
// AIRTABLE_TABLE_ID — different env vars from the build's AIRTABLE_BASE / AIRTABLE_TABLE. If either is
// still set in Netlify to the retired Investment Offerings base, this watches a table nobody edits.
const BASE_ID = process.env.AIRTABLE_BASE_ID || 'appTSWSTIsB2arukB';
const TABLE_ID = process.env.AIRTABLE_TABLE_ID || 'tblMiNHG8EGFcvngt';
// Build hook URL of THIS site (Site configuration -> Build & deploy -> Build hooks). Without it the watcher only reports.
const HOOK = process.env.NETLIFY_BUILD_HOOK || '';

const json = (s, b) => ({ statusCode: s, headers: { 'content-type': 'application/json' }, body: JSON.stringify(b) });

export const handler = async (event) => {
  const q = (event && event.queryStringParameters) || {};
  let body = {};
  try { body = JSON.parse((event && event.body) || '{}'); } catch {}
  const isScheduled = !!body.next_run;
  const keyed = process.env.PORTAL_SYNC_KEY && q.key === process.env.PORTAL_SYNC_KEY;
  if (!isScheduled && !keyed) return json(403, { error: 'forbidden' });

  try {
    // Newest offering modification (paginated; only the Last Modified field).
    let latest = '', offset;
    do {
      const url = `https://api.airtable.com/v0/${BASE_ID}/${encodeURIComponent(TABLE_ID)}?pageSize=100&fields%5B%5D=Last%20Modified${offset ? `&offset=${offset}` : ''}`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${process.env.AIRTABLE_TOKEN}` } });
      if (!r.ok) return json(502, { error: `Airtable ${r.status}` });
      const d = await r.json();
      for (const rec of d.records || []) {
        const v = rec.fields && rec.fields['Last Modified'];
        if (v && v > latest) latest = v;
      }
      offset = d.offset;
    } while (offset);

    // Timestamp of the currently published build.
    const site = (process.env.URL || 'https://baker1031.com').replace(/\/$/, '');
    const br = await fetch(`${site}/build-info.json`, { headers: { 'cache-control': 'no-cache' } });
    const builtAt = br.ok ? ((await br.json()).builtAt || '') : '';

    const stale = !!latest && (!builtAt || latest > builtAt);
    if (stale && !HOOK) return json(200, { ok: true, triggered: false, stale, latest, builtAt, note: 'NETLIFY_BUILD_HOOK not set' });
    if (stale && !(keyed && q.dry === '1')) {
      const hr = await fetch(HOOK, { method: 'POST' });
      console.log(`[rebuild-watcher] offerings changed (${latest} > ${builtAt || 'unknown'}) → hook ${hr.status}`);
      return json(200, { ok: true, triggered: true, latest, builtAt });
    }
    return json(200, { ok: true, triggered: false, stale, latest, builtAt });
  } catch (e) {
    console.error('[rebuild-watcher]', e.message);
    return json(500, { error: e.message });
  }
};

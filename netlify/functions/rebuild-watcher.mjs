/*
  Baker 1031 — Opportunities tool → Netlify rebuild watcher (backstop)
  Runs every 15 minutes (netlify.toml schedule). The Opportunities tool (opportunities.baker1031.com) already
  fires this site's build hook about a minute after any change settles; this watcher only catches a missed
  ping. It compares the newest updatedAt in the public opportunities feed against the live build timestamp
  (/build-info.json) and POSTs NETLIFY_BUILD_HOOK when the feed is newer.

  Env: NETLIFY_BUILD_HOOK (this site's build hook URL), OPPORTUNITIES_FEED (optional override).
  Manual run: POST ?key=<PORTAL_SYNC_KEY> (&dry=1 to report without triggering).
*/
const FEED = process.env.OPPORTUNITIES_FEED || 'https://opportunities.baker1031.com/api/public/opportunities';
const HOOK = (process.env.NETLIFY_BUILD_HOOK || '').split(/\s+/).filter(Boolean)[0] || '';

const json = (s, b) => ({ statusCode: s, headers: { 'content-type': 'application/json' }, body: JSON.stringify(b) });

export const handler = async (event) => {
  const q = (event && event.queryStringParameters) || {};
  let body = {};
  try { body = JSON.parse((event && event.body) || '{}'); } catch {}
  const isScheduled = !!body.next_run;
  const keyed = process.env.PORTAL_SYNC_KEY && q.key === process.env.PORTAL_SYNC_KEY;
  if (!isScheduled && !keyed) return json(403, { error: 'forbidden' });
  try {
    const r = await fetch(FEED, { headers: { 'cache-control': 'no-cache' } });
    if (!r.ok) return json(502, { error: `feed ${r.status}` });
    const d = await r.json();
    let latest = '';
    for (const o of d.opportunities || []) if (o.updatedAt && o.updatedAt > latest) latest = o.updatedAt;
    const site = (process.env.URL || 'https://baker1031.com').replace(/\/$/, '');
    const br = await fetch(`${site}/build-info.json`, { headers: { 'cache-control': 'no-cache' } });
    const builtAt = br.ok ? ((await br.json()).builtAt || '') : '';
    const stale = !!latest && (!builtAt || latest > builtAt);
    if (stale && !HOOK) return json(200, { ok: true, triggered: false, stale, latest, builtAt, note: 'NETLIFY_BUILD_HOOK not set' });
    if (stale && !(keyed && q.dry === '1')) {
      const hr = await fetch(HOOK, { method: 'POST' });
      console.log(`[rebuild-watcher] opportunities changed (${latest} > ${builtAt || 'unknown'}) → hook ${hr.status}`);
      return json(200, { ok: true, triggered: true, latest, builtAt });
    }
    return json(200, { ok: true, triggered: false, stale, latest, builtAt });
  } catch (e) {
    console.error('[rebuild-watcher]', e.message);
    return json(500, { error: e.message });
  }
};

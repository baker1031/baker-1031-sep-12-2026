/*
  Baker 1031 — Attio "Portal Access" -> Airtable "Investors" sync (POST /api/portal-sync)

  Trigger it from an Attio webhook (record.updated on people — ideally filtered to the Portal Access
  attributes) or by hand with {"email": "..."} / {"record_id": "..."}.

  Portal Access = Yes -> the investor row is created or approved in Airtable, with the exchange timeline
                         (Start Date, ID Period Expiration, 1031 Expiration) from the person's Closing
                         Date / 45-Day / 180-Day attributes, falling back to the newest open deal. The
                         welcome email with its first-time auto-login link goes out once.
  Portal Access = No  -> an Approved row is set to Revoked and login stops working immediately
                         (auth.mjs re-verifies every page load). A row sitting on Call Needed is left
                         alone: that is the site's own pre-approval state, not a decision to demote.

  "Portal Access - Level 2" (Yes / Requested / No) is the second tier, for the restricted pages listed
  in gate.js. It mirrors to "Level 2 Access", stamps "Level 2 Approved On" the first time it is granted,
  and emails the investor once. Level 2 without portal access does nothing; the gate checks both.

  The reverse direction — an edit made in Airtable, pushed back to Attio — is /api/access-sync. The
  shared logic for both lives in lib/portal.mjs.

  Auth: an Attio webhook is verified with its signing secret (ATTIO_WEBHOOK_SECRET, header
        Attio-Signature); otherwise the request must carry the shared key (header x-portal-key, or
        ?key=PORTAL_SYNC_KEY).
  Env:  ATTIO_API_KEY, AIRTABLE_TOKEN, PORTAL_SYNC_KEY and/or ATTIO_WEBHOOK_SECRET,
        ACCESS_BASE_ID, ACCESS_TABLE_ID.
*/
import crypto from 'node:crypto';
import * as attio from './lib/attio.mjs';
import { syncOne } from './lib/portal.mjs';

const json = (status, body) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
});

/* Attio signs with a SHA256 HMAC of the raw request body, hex-encoded, in Attio-Signature
   (X-Attio-Signature is the legacy duplicate) -- https://docs.attio.com/rest-api/guides/webhooks.
   Two details that will silently fail an otherwise correct secret, so both are handled here:
   Netlify hands the body over base64-encoded when it decides the payload is binary, and the HMAC has
   to be taken over the decoded bytes; and a hex digest compared case-sensitively will not match if
   the two sides disagree on case. A mismatch returns 403, which Attio counts as a failed delivery and
   retries 10 times over ~3 days before disabling the webhook -- so log enough to tell a wrong secret
   apart from a missing one without ever printing either. */
function signedByAttio(event) {
  const secret = process.env.ATTIO_WEBHOOK_SECRET;
  const sig = event.headers['attio-signature'] || event.headers['x-attio-signature'];
  if (!secret) { console.error('[portal-sync] ATTIO_WEBHOOK_SECRET is not set — webhook cannot be verified'); return false; }
  if (!sig) { console.error('[portal-sync] no Attio-Signature header on the request'); return false; }
  const raw = event.isBase64Encoded ? Buffer.from(event.body || '', 'base64') : Buffer.from(event.body || '', 'utf8');
  const want = crypto.createHmac('sha256', secret).update(raw).digest('hex');
  const got = String(sig).trim().toLowerCase();
  if (want.length !== got.length || !crypto.timingSafeEqual(Buffer.from(want), Buffer.from(got))) {
    console.error(`[portal-sync] Attio signature did not verify (body ${raw.length}B, base64=${!!event.isBase64Encoded}) — the secret in ATTIO_WEBHOOK_SECRET is not the one Attio is signing with`);
    return false;
  }
  return true;
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

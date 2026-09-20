/*
  Baker 1031 — re-sends registrations the CRM missed (scheduled every 5 minutes, netlify.toml)

  lead.mjs keeps a registration in the Netlify Blobs store "pending-leads" when the CRM could not take it. This goes
  through that store, sends each one to the CRM again (POST crm.baker1031.com/api/site, op "lead") and deletes it once
  the CRM confirms. After 24 hours of failures the raw registration is emailed to jerry@baker1031.com once
  (RESEND_API_KEY; LEAD_ALERT_TO overrides the address). The rules live in lib/pending-leads.mjs.

  A modern (v2) function so Netlify Blobs is wired in without the Lambda event. Scheduled functions cannot be called
  by URL in production; to see what is waiting, open the store in the Netlify UI (Blobs -> pending-leads).
  Env: CRM_SHARED_KEY, RESEND_API_KEY.
*/
import { getStore } from '@netlify/blobs';
import { retryPending, STORE } from './lib/pending-leads.mjs';

export default async () => {
  const out = await retryPending(getStore(STORE));
  if (out.checked || out.left) console.log('[lead-retry]', JSON.stringify(out));
  return new Response(JSON.stringify({ ok: true, ...out }), { headers: { 'content-type': 'application/json' } });
};

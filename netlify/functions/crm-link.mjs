/*
  Baker 1031 — personal update link, on request from the CRM (POST /api/crm-link)

  The CRM shows each client's "update my information" link so Jerry can paste it into an email. The link
  is signed with this site's SESSION_SECRET, which never leaves this project, so the CRM asks for the link
  instead of building it: Authorization: Bearer CRM_SHARED_KEY, body { email, firstName, lastName }.

  The person is looked up in Attio by email, and created there when the CRM knows someone this site has
  not met yet (the update page reads and writes the Attio person, so one has to exist). The link is the
  same one lead.mjs and the deadline reminders produce, and it is stored on the person's "Update Link".

  Returns { url, created }. 401 for a wrong key, 503 when the key or Attio is not configured.
*/
import crypto from 'node:crypto';
import * as attio from './lib/attio.mjs';
import { fromCrm, crmConfigured } from './lib/crm.mjs';

const json = (status, body) => ({ statusCode: status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) });

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  if (!crmConfigured() || !attio.configured() || !process.env.SESSION_SECRET) return json(503, { error: 'not configured' });
  if (!fromCrm(event)) { await new Promise((r) => setTimeout(r, 400)); return json(401, { error: 'unauthorized' }); }

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { return json(400, { error: 'bad json' }); }
  const email = String(body.email || '').trim().toLowerCase();
  if (!/^[\w.+'-]+@[\w-]+(?:\.[\w-]+)+$/.test(email)) return json(400, { error: 'a valid email is required' });

  try {
    let person = await attio.findPersonByEmail(email);
    let created = false;
    if (!person) {
      person = await attio.upsertPerson({ email, firstName: String(body.firstName || '').slice(0, 80), lastName: String(body.lastName || '').slice(0, 80) });
      created = true;
    }
    const cid = person.id.record_id;
    const sig = crypto.createHmac('sha256', process.env.SESSION_SECRET).update('myinfo:' + cid).digest('hex').slice(0, 32);
    const url = `${(process.env.URL || 'https://baker1031.com').replace(/\/$/, '')}/update-my-info/?cid=${cid}&sig=${sig}`;
    await attio.setValues('people', cid, [['Update Link', url]]).catch((e) => console.error('[crm-link] store:', e.message));
    return json(200, { url, created });
  } catch (e) {
    console.error('[crm-link]', e.message);
    return json(502, { error: 'could not reach the contact record' });
  }
};

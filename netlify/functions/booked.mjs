/*
  Baker 1031 — a booked intro call, recorded in the CRM (POST /api/booked)

  Until now a booking existed only in Cal.com and in the browser tab: the register form recorded it in
  its own state and called window.onLeadBooked, which nothing defined. The deal never left "Lead" and
  the person's record never showed that a call was on the calendar.

  What this does, for a person who already exists in Attio (the registration itself creates them, at
  the acknowledgments step, before the calendar appears):

    - moves their newest open deal to ATTIO_BOOKED_STAGE (default "Intro Call Scheduled")
    - writes a note on the person with the date, time, event type and Cal.com booking id
    - VERIFIED CALLS ONLY: sets Portal Access = Yes and runs the portal sync, which creates or approves
      the Airtable investor row, writes the exchange timeline and sends the welcome email

  Why "verified calls only" for the access grant: this endpoint has to be reachable from the browser,
  and anyone can POST an email address to a public URL. Moving a deal stage and adding a note are
  recoverable; opening the offering documents to a stranger is not. So the browser call does the first
  two and stops, and access is granted only when the request is provably from Cal.com or from Jerry.

  A request counts as verified when either:
    - it carries a valid Cal.com webhook signature (x-cal-signature-256 = HMAC-SHA256 of the raw body
      with CAL_WEBHOOK_SECRET), or
    - it carries the shared key (header x-portal-key or ?key=PORTAL_SYNC_KEY) — for manual runs.

  To turn the access grant on, add a webhook in Cal.com (Settings -> Developer -> Webhooks):
      URL     https://baker1031.com/api/booked
      Trigger Booking created
      Secret  the same value as CAL_WEBHOOK_SECRET
  Until that exists, bookings still move the deal and land a note; access stays a manual flip.

  Env: ATTIO_API_KEY (required), CAL_WEBHOOK_SECRET / PORTAL_SYNC_KEY (to verify), AIRTABLE_TOKEN +
       SESSION_SECRET + RESEND_API_KEY (for the access grant), ATTIO_BOOKED_STAGE.
*/
import crypto from 'node:crypto';
import * as attio from './lib/attio.mjs';
import { tellCrm } from './lib/crm.mjs';
import { syncOne } from './lib/portal.mjs';
import { isInvestor } from './lib/invites.mjs';

const STAGE = process.env.ATTIO_BOOKED_STAGE || 'Intro Call Scheduled';

const json = (status, body) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
});

function signedByCal(event) {
  const secret = process.env.CAL_WEBHOOK_SECRET;
  const sig = event.headers['x-cal-signature-256'] || event.headers['x-cal-signature'];
  if (!secret || !sig) return false;
  const want = crypto.createHmac('sha256', secret).update(event.body || '', 'utf8').digest('hex');
  const a = Buffer.from(want), b = Buffer.from(String(sig).trim());
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

/* One shape out of either a Cal.com webhook or the register form's own POST. */
function readBooking(body) {
  const p = body.payload || body;                       // Cal.com nests the booking under payload
  const b = p.booking || p;
  const attendee = (p.attendees && p.attendees[0]) || (b.attendees && b.attendees[0]) || {};
  const email = String(body.email || p.email || attendee.email || '').trim().toLowerCase();
  const start = b.startTime || p.startTime || b.start || p.date || null;
  return {
    email,
    firstName: body.firstName || String(attendee.name || '').split(' ')[0] || '',
    uid: b.uid || p.uid || null,
    start,
    end: b.endTime || p.endTime || b.end || null,
    eventType: (p.eventType && (p.eventType.slug || p.eventType.title)) || b.eventType || p.title || '25min',
    bookedAt: body.bookedAt || b.bookedAt || new Date().toISOString(),
  };
}

const when = (iso) => {
  if (!iso) return 'time not supplied';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso)
    : d.toLocaleString('en-US', { timeZone: 'America/Los_Angeles', weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) + ' PT';
};

export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return json(405, { error: 'POST only' });
  if (!attio.configured()) return json(500, { error: 'ATTIO_API_KEY not configured' });

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { return json(400, { error: 'bad JSON' }); }

  // Cal.com fires on several triggers if the webhook is set broadly; only a new booking is ours.
  const trigger = body.triggerEvent || body.trigger || '';
  if (trigger && !/BOOKING_CREATED|BOOKING_RESCHEDULED/i.test(trigger)) return json(200, { ok: true, ignored: trigger });

  const key = event.headers['x-portal-key'] || (event.queryStringParameters || {}).key;
  const verified = signedByCal(event) || (!!process.env.PORTAL_SYNC_KEY && key === process.env.PORTAL_SYNC_KEY);

  const bk = readBooking(body);
  if (!bk.email.includes('@')) return json(400, { error: 'no attendee email in payload' });

  await tellCrm('site.booking', bk.email, { when: when(bk.start), eventType: String(bk.eventType || '').slice(0, 120), verified });

  const found = await attio.findPersonByEmail(bk.email);
  if (!found) return json(200, { ok: true, skipped: `no Attio person for ${bk.email} — nothing to update` });
  const personId = found.id.record_id;
  const done = [];

  // the deal moves to "call scheduled"
  try {
    const deal = await attio.openDeal(personId);
    if (deal) {
      // forward-only: a reschedule or a second booking never drags a deal back from a later stage
      const res = await attio.advanceDeal(deal, STAGE);
      done.push(res === 'moved' ? `deal moved to ${STAGE}` : `deal left in "${attio.dealStage(deal)}" (${res})`);
    } else {
      done.push('no open deal to move');
    }
  } catch (e) { console.error('[booked] deal stage:', e.message); done.push(`deal stage failed: ${e.message}`); }

  // and the booking itself goes on the record
  const lines = [
    `When: ${when(bk.start)}`,
    `Event type: ${bk.eventType}`,
    bk.uid ? `Cal.com booking: ${bk.uid}` : null,
    `Recorded: ${new Date().toISOString().slice(0, 16)}Z${verified ? ' (Cal.com)' : ' (from the registration form, unverified)'}`,
  ].filter(Boolean);
  await attio.addNote('people', personId, 'Introductory call booked', lines.join('\n'), 'plaintext')
    .then(() => done.push('note added'))
    .catch((e) => { console.error('[booked] note:', e.message); done.push(`note failed: ${e.message}`); });

  // portal access, on a verified booking only
  if (!verified) {
    return json(200, { ok: true, verified: false, done, access: 'not granted — an unverified call cannot open the portal' });
  }
  try {
    const pAttrs = await attio.attributes('people');
    const flat = attio.flatValues(await attio.getPerson(personId));
    const cur = pAttrs.find((a) => a.title.toLowerCase() === 'portal access');
    const already = cur && String(flat[cur.slug] ?? '').trim().toLowerCase() === 'yes';
    // Someone who registered to help an investor (realtor, attorney, CPA, advisor, family) was never asked
    // the accreditation questions, so a booking alone does not open the offerings to them. Jerry can still
    // set Portal Access to Yes by hand in Attio.
    const roleAttr = pAttrs.find((a) => a.title.toLowerCase() === 'role (this transaction)');
    const role = roleAttr ? String(flat[roleAttr.slug] ?? '') : '';
    if (!already && !isInvestor({ role })) {
      done.push(`Portal Access left as is - registered as "${role}", not as the investor`);
      return json(200, { ok: true, verified: true, done });
    }
    if (!already) {
      await attio.setValues('people', personId, [['Portal Access', 'Yes']]);
      done.push('Portal Access set to Yes');
    }
    if (process.env.AIRTABLE_TOKEN) {
      const res = await syncOne(personId);
      done.push(`portal sync: ${res.action || res.skipped || res.error}`);
    }
  } catch (e) { console.error('[booked] access:', e.message); done.push(`access failed: ${e.message}`); }

  return json(200, { ok: true, verified: true, done });
};

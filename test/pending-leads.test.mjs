/*
  Registrations the CRM missed: kept in the "pending-leads" store, re-sent by lead-retry every 5 minutes, deleted once
  the CRM confirms, emailed to Jerry once after 24 hours of failures. No network: the CRM call and the email are stubbed.
  Run:  npm test   (or node --test test/*.test.mjs, after npm install)
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import { queueLead, retryPending, alertEmail, ALERT_AFTER_MS, DROP_AFTER_ALERT_MS } from '../netlify/functions/lib/pending-leads.mjs';
import { memoryStore } from './helpers/memory-store.mjs';

const lead = { firstName: 'Dana', lastName: 'West', email: 'dana@example.org', role: 'Investor', equity: 650000 };
const H = 3600 * 1000;

test('a delivered retry is deleted; a failed one is kept with its count and error', async () => {
  const store = memoryStore();
  await queueLead(store, { lead, ip: '203.0.113.9', error: 'CRM 0', crsSent: true });
  const sent = [];
  let out = await retryPending(store, { send: (e) => { sent.push(e); return { ok: false, status: 503, body: { error: 'maintenance' } }; }, alert: () => assert.fail('too early to alert') });
  assert.deepEqual([out.checked, out.failed, out.delivered], [1, 1, 0]);
  assert.deepEqual([sent[0].lead.email, sent[0].ip], ['dana@example.org', '203.0.113.9'], 'the raw registration and the visitor IP go to the CRM again');
  const e = JSON.parse([...store.m.values()][0]); assert.equal(e.attempts, 2); assert.equal(e.lastError, 'CRM 503: maintenance');
  out = await retryPending(store, { send: () => ({ ok: true, status: 200, body: { ok: true, contactId: 'c_1' } }) });
  assert.equal(out.delivered, 1); assert.equal(store.m.size, 0);
});

test('a CRM answer that is not ok:true is a failure, and a throwing sender does not stop the pass', async () => {
  const store = memoryStore();
  await queueLead(store, { lead }); await queueLead(store, { lead: { ...lead, email: 'b@example.org' } });
  let n = 0;
  const out = await retryPending(store, { send: () => { n++; if (n === 1) throw new Error('boom'); return { ok: true, status: 200, body: { error: 'bad_request' } }; } });
  assert.deepEqual([out.checked, out.failed], [2, 2]); assert.equal(store.m.size, 2);
});

test('after 24 hours of failures Jerry is emailed once; the entry is kept, then dropped 7 days after the email', async () => {
  const store = memoryStore();
  await queueLead(store, { lead, crsSent: false });
  const t0 = Date.now(), alerts = [], fail = () => ({ ok: false, status: 0, body: {} });
  await retryPending(store, { now: t0 + 23 * H, send: fail, alert: (e) => { alerts.push(e); return true; } });
  assert.equal(alerts.length, 0);
  let out = await retryPending(store, { now: t0 + ALERT_AFTER_MS + 60000, send: fail, alert: (e) => { alerts.push(e); return true; } });
  assert.equal(out.alerted, 1); assert.equal(alerts[0].lead.email, 'dana@example.org'); assert.equal(store.m.size, 1, 'still retried after the email');
  await retryPending(store, { now: t0 + ALERT_AFTER_MS + 2 * H, send: fail, alert: (e) => { alerts.push(e); return true; } });
  assert.equal(alerts.length, 1, 'only one email');
  out = await retryPending(store, { now: t0 + ALERT_AFTER_MS + DROP_AFTER_ALERT_MS + 2 * H, send: fail, alert: () => true });
  assert.equal(out.dropped, 1); assert.equal(store.m.size, 0);
});

test('without a sent email (no RESEND_API_KEY) nothing is ever dropped', async () => {
  const store = memoryStore();
  await queueLead(store, { lead });
  const out = await retryPending(store, { now: Date.now() + 30 * 24 * H, send: () => ({ ok: false, status: 0, body: {} }), alert: () => false });
  assert.deepEqual([out.alerted, out.dropped], [0, 0]); assert.equal(store.m.size, 1);
  assert.equal(JSON.parse([...store.m.values()][0]).alertedAt, null, 'it will try the email again next pass');
});

test('the email carries the raw registration, escaped', () => {
  const m = alertEmail({ lead: { ...lead, lastName: '<b>West</b>' }, ip: '203.0.113.9', queuedAt: '2026-09-19T10:00:00.000Z', attempts: 289, lastError: 'CRM 0', crsSent: true });
  assert.match(m.subject, /Registration not in the CRM - Dana <b>West<\/b>/);
  assert.match(m.html, /&quot;equity&quot;: 650000/); assert.doesNotMatch(m.html, /<b>West/); assert.match(m.html, /203\.0\.113\.9/); assert.match(m.html, /289 time/);
});

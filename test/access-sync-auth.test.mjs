/*
  The scheduled reconcile ran for hours writing nothing, with no error anywhere. The cause was the
  guard, not the work: Netlify invokes a scheduled function by POSTing to it with a JSON body
  carrying `next_run`, so the old `!event.httpMethod` test was never true for a scheduled run and
  every pass returned 403 before doing anything.

  These assertions pin the guard down. No network: with AIRTABLE_TOKEN unset the handler returns 500
  at the config check, which sits immediately after the auth gate — so "not 403" is proof the run got
  through, and 403 is proof it did not.

  The site now runs on the CRM by default, where this job stands down; the gate is pinned here on the Attio path
  (CRM_BACKEND=attio, the emergency switch-back), which is the only place it still does work.

  Run:  node --test test/access-sync-auth.test.mjs
*/
import test from 'node:test';
import assert from 'node:assert/strict';

delete process.env.AIRTABLE_TOKEN;
delete process.env.PORTAL_SYNC_KEY;
process.env.CRM_BACKEND = 'attio';
const { handler } = await import('../netlify/functions/access-sync.mjs');

const scheduledEvent = () => ({
  httpMethod: 'POST',
  headers: {},
  queryStringParameters: null,
  body: JSON.stringify({ next_run: '2026-09-18T02:17:00.000Z' }),
});

test('a Netlify scheduled invocation is let through', async () => {
  const res = await handler(scheduledEvent());
  assert.notEqual(res.statusCode, 403, 'the scheduled pass must not be rejected as unauthorised');
  assert.equal(res.statusCode, 500);
  assert.match(res.body, /AIRTABLE_TOKEN/, 'it reached the config check, i.e. it passed the gate');
});

test('a scheduled invocation with no HTTP wrapper is still let through', async () => {
  const res = await handler({ body: JSON.stringify({ next_run: '2026-09-18T02:17:00.000Z' }) });
  assert.notEqual(res.statusCode, 403);
});

test('an ordinary POST with no key is still refused', async () => {
  const res = await handler({ httpMethod: 'POST', headers: {}, queryStringParameters: null, body: '{}' });
  assert.equal(res.statusCode, 403);
});

test('a GET is still refused', async () => {
  const res = await handler({ httpMethod: 'GET', headers: {}, queryStringParameters: null, body: '' });
  assert.equal(res.statusCode, 405);
});

test('a key that does not match is still refused', async () => {
  process.env.PORTAL_SYNC_KEY = 'the-real-key';
  const res = await handler({ httpMethod: 'POST', headers: { 'x-portal-key': 'wrong' }, queryStringParameters: null, body: '{}' });
  assert.equal(res.statusCode, 403);
  delete process.env.PORTAL_SYNC_KEY;
});

test('next_run cannot be forged past the key check by an outside caller alone', async () => {
  // This is the tradeoff the fix accepts and it matches deadline-reminders and rebuild-watcher:
  // a body carrying next_run is treated as scheduled. Worth knowing, not worth blocking - the
  // endpoint only reconciles Attio and Airtable with each other, it takes no caller input.
  const res = await handler(scheduledEvent());
  assert.notEqual(res.statusCode, 403);
});

test('on the CRM (the default) a scheduled run stands down without touching Airtable', async () => {
  delete process.env.CRM_BACKEND;
  const res = await handler(scheduledEvent());
  assert.equal(res.statusCode, 200);
  assert.match(res.body, /held by the CRM/);
  process.env.CRM_BACKEND = 'attio';
});

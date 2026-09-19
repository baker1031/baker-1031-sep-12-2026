// The website's side of the CRM link: events go out only with a key, carry the right shape, never throw; /api/crm-link refuses anyone without the key.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';

const KEY = 'test-shared-key-0123456789abcdef';
const seen = [];
const server = http.createServer((req, res) => { let b = ''; req.on('data', (c) => { b += c; }); req.on('end', () => { seen.push({ auth: req.headers.authorization, body: JSON.parse(b || '{}') }); res.writeHead(200, { 'content-type': 'application/json' }); res.end('{"saved":1}'); }); });
await new Promise((r) => server.listen(0, '127.0.0.1', r));
process.env.CRM_EVENTS_URL = `http://127.0.0.1:${server.address().port}/api/events`;
const { tellCrm, crmConfigured, fromCrm } = await import('../netlify/functions/lib/crm.mjs');

test('nothing is sent until the key is set', async () => {
  delete process.env.CRM_SHARED_KEY;
  assert.equal(crmConfigured(), false);
  assert.equal(await tellCrm('site.login', 'a@example.org'), false);
  assert.equal(seen.length, 0);
});
test('an event carries the key, a lowercased email and the data', async () => {
  process.env.CRM_SHARED_KEY = KEY;
  assert.equal(await tellCrm('site.view', ' Pat@Example.org ', { slug: 'x-dst', pv: 'abc12345' }, 'Pat Tester'), true);
  assert.equal(seen[0].auth, 'Bearer ' + KEY);
  const ev = seen[0].body.events[0];
  assert.deepEqual([ev.type, ev.email, ev.name, ev.data.slug], ['site.view', 'pat@example.org', 'Pat Tester', 'x-dst']);
});
test('an unreachable CRM is swallowed', async () => {
  process.env.CRM_EVENTS_URL = 'http://127.0.0.1:9/api/events';
  assert.equal(await tellCrm('site.login', 'a@example.org'), false);
});
test('fromCrm accepts only the exact bearer key', () => {
  assert.equal(fromCrm({ headers: { authorization: 'Bearer ' + KEY } }), true);
  assert.equal(fromCrm({ headers: { authorization: 'Bearer nope' } }), false);
  assert.equal(fromCrm({ headers: {} }), false);
});
test('/api/crm-link: 503 unconfigured, 401 without the key, 405 on GET', async () => {
  const { handler } = await import('../netlify/functions/crm-link.mjs');
  delete process.env.ATTIO_API_KEY;
  assert.equal((await handler({ httpMethod: 'POST', headers: {}, body: '{}' })).statusCode, 503);
  assert.equal((await handler({ httpMethod: 'GET', headers: {} })).statusCode, 405);
  process.env.ATTIO_API_KEY = 'x'; process.env.SESSION_SECRET = 's'.repeat(40);
  assert.equal((await handler({ httpMethod: 'POST', headers: { authorization: 'Bearer wrong' }, body: '{}' })).statusCode, 401);
  assert.equal((await handler({ httpMethod: 'POST', headers: { authorization: 'Bearer ' + KEY }, body: '{"email":"not-an-email"}' })).statusCode, 400);
});
test.after(() => server.close());

// The site with the CRM behind it: the switch, and each function handing its job to POST /api/site instead of Attio and Airtable.
// A local HTTP server stands in for the CRM and records what it was asked; Resend is stubbed so a stray local send would be seen.
import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import crypto from 'node:crypto';

const KEY = 'test-shared-key-0123456789abcdef', asked = [], mail = [];
let mode = 'crm', down = false, reply = {};
const server = http.createServer((req, res) => { let b = ''; req.on('data', (c) => { b += c; }); req.on('end', () => {
  if (down) { res.writeHead(500); return res.end('{}'); }
  const body = JSON.parse(b || '{}'); if (req.url === '/api/site' && body.op !== 'mode') asked.push({ auth: req.headers.authorization, ...body });
  const out = req.url !== '/api/site' ? { saved: 1 } : body.op === 'mode' ? { mode } : (reply[body.op] || { ok: true });
  res.writeHead(out._status || 200, { 'content-type': 'application/json' }); res.end(JSON.stringify(out)); }); });
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const at = `http://127.0.0.1:${server.address().port}`;
Object.assign(process.env, { CRM_SHARED_KEY: KEY, CRM_SITE_URL: at + '/api/site', CRM_EVENTS_URL: at + '/api/events', SESSION_SECRET: 'unit-test-session-secret', RESEND_API_KEY: 're_unit' });
delete process.env.ATTIO_API_KEY; delete process.env.AIRTABLE_TOKEN; delete process.env.CRM_BACKEND;
const realFetch = globalThis.fetch;
const airtable = [];
globalThis.fetch = async (u, init) => (/api\.airtable\.com|api\.attio\.com/.test(String(u)) ? (airtable.push(String(u)), new Response('{}', { status: 599 })) : String(u).startsWith('https://api.resend.com/') ? (mail.push(JSON.parse(init.body)), new Response('{"id":"x"}', { status: 200 })) : realFetch(u, init));

const crm = await import('../netlify/functions/lib/crm.mjs');
const ev = (body, extra = {}) => ({ httpMethod: 'POST', headers: {}, queryStringParameters: {}, body: JSON.stringify(body), ...extra });
const cookieOf = (res) => (res.multiValueHeaders?.['set-cookie'] || []).find((c) => c.startsWith('b31_session='))?.split(';')[0] || '';
const last = () => asked.at(-1);

test('the backend: the CRM by default with no call to ask; CRM_BACKEND=attio switches back; =switch follows the CRM setting', async () => {
  let modeCalls = 0; const count = globalThis.fetch; globalThis.fetch = async (u, init) => { if (init && String(init.body || '').includes('"op":"mode"')) modeCalls++; return count(u, init); };
  crm._resetBackend(); mode = 'attio';
  assert.equal(await crm.backend(), 'crm'); assert.equal(modeCalls, 0, 'no round trip to find out');
  down = true; assert.equal(await crm.backend(), 'crm', 'an outage never flips the site'); down = false;
  const key = process.env.CRM_SHARED_KEY; delete process.env.CRM_SHARED_KEY; assert.equal(await crm.backend(), 'crm', 'even without the key'); process.env.CRM_SHARED_KEY = key;
  process.env.CRM_BACKEND = 'attio'; assert.equal(await crm.backend(), 'attio'); assert.equal(await crm.usingCrm(), false);
  process.env.CRM_BACKEND = 'crm'; assert.equal(await crm.backend(), 'crm');
  process.env.CRM_BACKEND = 'switch';
  assert.equal(await crm.backend(), 'attio', 'the CRM setting, asked'); assert.equal(modeCalls, 1);
  mode = 'crm'; assert.equal(await crm.backend(), 'attio', 'remembered for a minute'); assert.equal(modeCalls, 1);
  crm._resetBackend(); down = true; assert.equal(await crm.backend(), 'crm', 'never reached the CRM: stay on the CRM'); down = false;
  crm._resetBackend(); assert.equal(await crm.backend(), 'crm'); down = true; assert.equal(await crm.backend(), 'crm', 'the last answer is kept through an outage'); down = false;
  delete process.env.CRM_BACKEND; crm._resetBackend(); globalThis.fetch = count;
});

test('a registration goes to the CRM with the visitor IP; the receipt is sent here only if the CRM did not confirm it', async () => {
  const { handler } = await import('../netlify/functions/lead.mjs');
  reply.lead = { ok: true, contactId: 'c_1', crs: true };
  let res = await handler(ev({ firstName: 'Dana', email: 'dana@example.org', role: 'Investor' }, { headers: { 'x-nf-client-connection-ip': '203.0.113.9' } }));
  assert.deepEqual(JSON.parse(res.body), { ok: true, via: 'crm' }); assert.deepEqual([last().op, last().auth, last().ip, last().lead.email], ['lead', 'Bearer ' + KEY, '203.0.113.9', 'dana@example.org']); assert.equal(mail.length, 0);
  reply.lead = { ok: true, contactId: 'c_1', crs: false }; await handler(ev({ firstName: 'Dana', email: 'dana@example.org' })); assert.equal(mail.length, 1); assert.deepEqual(mail[0].to, ['crs@baker1031.com']);
  const pl = await import('../netlify/functions/lib/pending-leads.mjs'), { memoryStore } = await import('./helpers/memory-store.mjs'), store = memoryStore(); pl._useStore(store);
  const outside = []; const f0 = globalThis.fetch; globalThis.fetch = async (u, init) => { if (/attio|airtable|leadconnector|gohighlevel/.test(String(u))) outside.push(String(u)); return f0(u, init); };
  process.env.ATTIO_API_KEY = 'attio-unit'; process.env.AIRTABLE_TOKEN = 'at-unit';
  down = true; res = await handler(ev({ firstName: 'Dana', email: 'dana@example.org' }));
  assert.deepEqual(JSON.parse(res.body), { ok: true, via: 'queued' }, 'the visitor still sees success');
  assert.equal(mail.length, 2, 'CRM unreachable: the compliance receipt still goes, from here'); assert.equal(store.m.size, 1, 'kept for the retry');
  const kept = JSON.parse([...store.m.values()][0]); assert.deepEqual([kept.lead.email, kept.crsSent, kept.attempts], ['dana@example.org', true, 1]); assert.match(kept.lastError, /^CRM 500/);
  assert.deepEqual(outside, [], 'no Attio, Airtable or GoHighLevel fallback'); down = false;
  pl._useStore(memoryStore({ failWrites: true })); down = true; res = await handler(ev({ firstName: 'Eve', email: 'eve@example.org' }));
  assert.equal(JSON.parse(res.body).ok, true); assert.deepEqual(mail.at(-1).to, ['jerry@baker1031.com'], 'the store is down too: Jerry gets the registration now'); assert.match(mail.at(-1).html, /eve@example.org/); down = false;
  pl._useStore(null); globalThis.fetch = f0; delete process.env.ATTIO_API_KEY; delete process.env.AIRTABLE_TOKEN;
});

test('the portal door reads the CRM', async () => {
  Object.assign(process.env, { AIRTABLE_TOKEN: 'at-unit', ATTIO_API_KEY: 'attio-unit' }); // present, and still never used on the CRM
  const { handler } = await import('../netlify/functions/auth.mjs');
  reply.login = { status: 'call_needed' }; assert.equal(JSON.parse((await handler(ev({ action: 'login', email: 'a@example.org' }))).body).status, 'call_needed');
  reply.login = { status: 'not_found' }; assert.equal(JSON.parse((await handler(ev({ action: 'login', email: 'a@example.org' }))).body).status, 'not_found');
  reply.login = { status: 'ok', rid: 'c_dana', firstName: 'Dana', lastName: 'W', email: 'dana@example.org', level: 1, approved: true };
  let res = await handler(ev({ action: 'login', email: 'Dana@example.org' })); const cookie = cookieOf(res); assert.ok(cookie); assert.deepEqual(JSON.parse(res.body), { status: 'ok', firstName: 'Dana', level: 1 });
  const withCookie = (body) => ev(body, { headers: { cookie } });
  reply.person = { ok: true, rid: 'c_dana', firstName: 'Dana', lastName: 'W', email: 'dana@example.org', approved: true, level: 2 };
  res = await handler(withCookie({ action: 'me' })); assert.deepEqual(JSON.parse(res.body), { authed: true, firstName: 'Dana', level: 2 }); assert.ok(cookieOf(res), 'level changed: the cookie is re-issued'); assert.equal(last().rid, 'c_dana');
  reply.person = { ...reply.person, approved: false }; res = await handler(withCookie({ action: 'me' })); assert.equal(JSON.parse(res.body).authed, false); assert.match(res.multiValueHeaders['set-cookie'][0], /Max-Age=0/);
  down = true; res = await handler(withCookie({ action: 'me' })); assert.equal(JSON.parse(res.body).authed, true, 'an outage is not a revocation'); assert.equal(res.multiValueHeaders, undefined); down = false;
  reply.person = { ...reply.person, approved: true };
  await handler(withCookie({ action: 'track_view', slug: 'harbor-point-dst' })); assert.deepEqual([last().op, last().rid, last().slug], ['track_view', 'c_dana', 'harbor-point-dst']);
  reply.level2_request = { ok: true }; res = await handler(withCookie({ action: 'request_level2', path: '/invest/restricted/' })); assert.deepEqual(JSON.parse(res.body), { ok: true }); assert.equal(last().op, 'level2_request');
  res = await handler(ev({ action: 'track_view', slug: 'x' })); assert.equal(res.statusCode, 401);
  res = await handler(withCookie({ action: 'track', kind: 'download', href: '/offerings/x/docs/ppm.pdf', name: 'PPM' })); assert.deepEqual(JSON.parse(res.body), { ok: true });
});

test('update links: the CRM checks its own, this site still checks the ones it issued', async () => {
  const { handler } = await import('../netlify/functions/my-info.mjs');
  reply.myinfo_get = { firstName: 'Omar' }; const get = (cid, sig) => handler({ httpMethod: 'GET', headers: {}, queryStringParameters: { cid, sig }, body: null });
  let res = await get('c_omar1', 'abc123'); assert.equal(JSON.parse(res.body).firstName, 'Omar'); assert.deepEqual([last().op, last().cid, last().sig, last().legacy], ['myinfo_get', 'c_omar1', 'abc123', undefined]);
  const old = '11111111-1111-4111-8111-111111111111', sig = crypto.createHmac('sha256', 'unit-test-session-secret').update('myinfo:' + old).digest('hex').slice(0, 32), n = asked.length;
  res = await get(old, 'f'.repeat(32)); assert.equal(res.statusCode, 403); assert.equal(asked.length, n, 'a bad old link never reaches the CRM');
  res = await get(old, sig); assert.equal(res.statusCode, 200); assert.deepEqual([last().cid, last().legacy, last().sig], [old, true, undefined]);
  reply.myinfo_post = { ok: true, invited: true }; res = await handler(ev({ cid: 'c_omar1', sig: 'abc123', saleDate: '2026-10-01', equity: 650000 })); assert.deepEqual(JSON.parse(res.body), { ok: true, invited: true }); assert.deepEqual(last().fields, { saleDate: '2026-10-01', equity: 650000 });
  reply.myinfo_get = { _status: 403, error: 'invalid link' }; assert.equal((await get('c_omar1', 'wrong')).statusCode, 403);
});

test('one-click login and stop-reminders links from the CRM; a browser-reported booking is passed on as unverified', async () => {
  const ll = (await import('../netlify/functions/login-link.mjs')).handler, off = (await import('../netlify/functions/reminders-off.mjs')).handler, booked = (await import('../netlify/functions/booked.mjs')).handler;
  reply.login_link = { ok: true, rid: 'c_dana', firstName: 'Dana', email: 'dana@example.org', level: 1 };
  let res = await ll({ queryStringParameters: { cid: 'c_dana', t: String(Date.now()), sig: 'abc' }, headers: {} }); assert.equal(res.statusCode, 302); assert.equal(res.headers.location, '/invest/?welcome=1'); assert.ok(cookieOf(res));
  reply.login_link = { ok: false }; res = await ll({ queryStringParameters: { cid: 'c_dana', t: String(Date.now()), sig: 'abc' }, headers: {} }); assert.equal(res.headers.location, '/login/?ll=expired');
  const rid = 'recAAAAAAAAAAAAAA', t = String(Date.now()), { linkSig } = await import('../netlify/functions/login-link.mjs'); reply.person = { ok: true, approved: true, rid: 'c_greta', firstName: 'Greta', email: 'g@example.org', level: 1 };
  res = await ll({ queryStringParameters: { rid, t, sig: linkSig(rid, t) }, headers: {} }); assert.equal(res.headers.location, '/invest/?welcome=1'); assert.deepEqual([last().op, last().rid], ['person', rid]);
  reply.reminders_off = { ok: true }; res = await off({ queryStringParameters: { cid: 'c_dana', sig: 'abc' } }); assert.match(res.body, /Reminders stopped/); assert.equal(last().op, 'reminders_off');
  reply.reminders_off = { _status: 403, error: 'invalid link' }; res = await off({ queryStringParameters: { cid: 'c_dana', sig: 'bad' } }); assert.match(res.body, /Link not valid/);
  reply.booked = { ok: true, verified: false, done: [] }; res = await booked(ev({ email: 'dana@example.org', startTime: '2026-10-01T17:00:00Z', uid: 'bk1' })); assert.equal(res.statusCode, 200); assert.deepEqual([last().op, last().verified, last().booking.email, last().booking.uid], ['booked', false, 'dana@example.org', 'bk1']);
});

test('the old jobs stand down instead of double-sending or erroring', async () => {
  const rem = (await import('../netlify/functions/deadline-reminders.mjs')).handler, sync = (await import('../netlify/functions/access-sync.mjs')).handler;
  assert.match((await rem({ body: JSON.stringify({ next_run: 'x' }) })).body, /sent by the CRM/); assert.match((await sync({ httpMethod: 'POST', headers: {}, body: JSON.stringify({ next_run: 'x' }) })).body, /held by the CRM/);
  const psync = (await import('../netlify/functions/portal-sync.mjs')).handler; process.env.PORTAL_SYNC_KEY = 'unit-portal-key';
  assert.match((await psync({ httpMethod: 'POST', headers: { 'x-portal-key': 'unit-portal-key' }, body: '{"email":"a@example.org"}' })).body, /held by the CRM/); delete process.env.PORTAL_SYNC_KEY;
});

test('/api/crm-export: key required, read only', async () => {
  delete process.env.AIRTABLE_TOKEN; delete process.env.ATTIO_API_KEY;
  const { handler } = await import('../netlify/functions/crm-export.mjs');
  assert.equal((await handler({ httpMethod: 'GET', headers: {} })).statusCode, 405); assert.equal((await handler(ev({ kind: 'people' }))).statusCode, 401);
  assert.equal((await handler(ev({ kind: 'people' }, { headers: { authorization: 'Bearer ' + KEY } }))).statusCode, 503, 'no Attio key in this test');
  assert.equal((await handler(ev({ kind: 'investors' }, { headers: { authorization: 'Bearer ' + KEY } }))).statusCode, 503);
});
test('on the CRM, login, update links, one-click links, bookings and opt-outs never read Airtable or Attio', () => {
  assert.deepEqual(airtable, []);
});
test.after(() => server.close());

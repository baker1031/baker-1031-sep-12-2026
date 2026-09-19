/*
  Who gets which email after registering, and which way a deal may move. Both are pure decisions, so
  they are pinned here.   Run:  node --test test/
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import { isInvestor, accreditedSignal, inviteVariant, noticeKind, buildInvite } from '../netlify/functions/lib/invites.mjs';
import { stageRank, advanceDeal } from '../netlify/functions/lib/attio.mjs';

const investor = (o = {}) => ({ role: 'Investor', path: 'exchange', phoneRegion: 'US', accreditedLikely: true, ...o });
const HELPERS = ['Realtor, agent, or broker', 'Loved one or friend', 'Attorney, CPA, or investment advisor', 'Other: property manager'];

test('an accredited U.S. investor is invited', () => {
  assert.equal(inviteVariant(investor()), 'exchange');
  assert.equal(inviteVariant(investor({ path: 'cash' })), 'cash');
  assert.equal(noticeKind(investor()), null);
});
test('an investor who misses a screen still gets the matching notice', () => {
  assert.equal(inviteVariant(investor({ accreditedLikely: false })), null);
  assert.equal(noticeKind(investor({ accreditedLikely: false })), 'accreditation');
  assert.equal(noticeKind(investor({ phoneRegion: 'INTL' })), 'residency');
});
test('a lead with no role (previous form) is screened as the investor', () => {
  assert.equal(isInvestor({}), true);
  assert.equal(noticeKind({ netWorth: 'Under $1,000,000', income: 'Under $200,000' }), 'accreditation');
});
for (const role of HELPERS) {
  test(`"${role}" bypasses the accreditation and residency screens`, () => {
    // exactly what the form sends for them: no net worth, no income, accreditedLikely false
    const lead = { role, path: 'exchange', phoneRegion: 'US', accreditedLikely: false };
    assert.equal(isInvestor(lead), false);
    assert.equal(noticeKind(lead), null, 'never the "may not be accredited" notice');
    assert.equal(noticeKind({ ...lead, phoneRegion: 'CA' }), null);
    assert.equal(inviteVariant(lead), 'assist-exchange');
    assert.equal(inviteVariant({ ...lead, path: 'cash' }), 'assist-cash');
    assert.equal(accreditedSignal(lead), '', 'no Accredited Signal is written for someone who was not asked');
  });
}
test('the helper invite links to the right calendar and does not promise them the offerings', () => {
  const ex = buildInvite('assist-exchange', 'Dana', 'https://baker1031.com'), cash = buildInvite('assist-cash', 'Dana', 'https://baker1031.com');
  assert.match(ex.html, /https:\/\/baker1031\.com\/schedule-call\//); assert.match(cash.html, /\/schedule-consultation\//);
  assert.doesNotMatch(ex.html, /open the current investments to you/);
  assert.match(buildInvite('exchange', 'Dana', 'https://baker1031.com').html, /open the current investments to you/);
});

const deal = (title) => ({ id: { record_id: 'd1' }, values: { stage: [{ status: { title } }] } });
test('stages only move forward', async () => {
  assert.ok(stageRank('Lead') < stageRank('Intro Call Scheduled') && stageRank('Intro Call Scheduled') < stageRank('reviewing opportunities'));
  assert.equal(await advanceDeal(deal('Actively Reviewing'), 'Reviewing Opportunities'), 'further-along');
  assert.equal(await advanceDeal(deal('Closing'), 'Intro Call Scheduled'), 'further-along', 'a reschedule never drags a deal back');
  assert.equal(await advanceDeal(deal('Reviewing Opportunities'), 'reviewing opportunities'), 'already-there');
  assert.equal(await advanceDeal(deal('Nurture (GHL)'), 'Reviewing Opportunities'), 'off-pipeline');
});
test('Lead and Intro Call Scheduled are promoted on a first offering view', async () => {
  const calls = []; const real = globalThis.fetch; process.env.ATTIO_API_KEY = 'test';
  globalThis.fetch = async (url, init) => { calls.push([String(url), init.method, JSON.parse(init.body)]); return new Response(JSON.stringify({ data: {} }), { status: 200, headers: { 'content-type': 'application/json' } }); };
  try {
    for (const from of ['Lead', 'Intro Call Scheduled']) assert.equal(await advanceDeal(deal(from), 'Reviewing Opportunities'), 'moved');
  } finally { globalThis.fetch = real; }
  assert.equal(calls.length, 2); assert.equal(calls[0][1], 'PATCH'); assert.match(calls[0][0], /\/objects\/deals\/records\/d1$/);
  assert.deepEqual(calls[0][2], { data: { values: { stage: 'Reviewing Opportunities' } } });
});

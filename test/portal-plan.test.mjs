/*
  The scheduled access reconcile decides what to do per row in planRow(), which is pure: row in,
  Attio person in, an action out. Everything expensive (the Attio queries, the Airtable writes, the
  emails) hangs off that decision, so this is the piece worth pinning down.

  Run:  node --test test/
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import { planRow, airtableIsNewer } from '../netlify/functions/lib/portal.mjs';

const row = (fields = {}) => ({ id: 'recTEST', fields: { 'Email Address': 'a@b.com', ...fields } });
const person = (o = {}) => ({
  recordId: 'per_1', email: 'a@b.com', firstName: 'A', lastName: 'B',
  portal: '', level2: '', closing: null, day45: null, day180: null, record: { values: {} }, ...o,
});
const dated = { 'Start Date': '2026-01-01', 'ID Period Expiration': '2026-02-15', '1031 Expiration': '2026-06-30' };
const settled = { 'Access Level': 'Approved', 'Welcome Email Sent': '2026-09-03', ...dated };

test('a row with no email is skipped', () => {
  assert.equal(planRow({ id: 'r', fields: {} }, person()).action, 'skip');
});

test('an unsynced row leaves Attio in charge', () => {
  // Access Changed At set, Access Synced At empty: a blank stamp is not evidence Airtable is newer.
  assert.equal(airtableIsNewer(row({ 'Access Changed At': '2026-09-03T01:14:00.000Z' })), false);
});

test('a row edited in Airtable since the last sync is pushed to Attio', () => {
  const r = row({ 'Access Changed At': '2026-09-18T02:00:00.000Z', 'Access Synced At': '2026-09-18T01:00:00.000Z' });
  assert.equal(airtableIsNewer(r), true);
  assert.equal(planRow(r, person({ portal: 'yes' })).action, 'push');
});

test('no Attio person with a flag set means nothing to carry over', () => {
  const p = planRow(row(settled), null);
  assert.equal(p.action, 'skip');
  assert.match(p.reason, /no Attio person/);
});

test('an empty Portal Access is not a decision', () => {
  const p = planRow(row(settled), person({ portal: '' }));
  assert.equal(p.action, 'skip');
  assert.match(p.reason, /empty/);
});

test('Portal Access = No demotes an Approved row', () => {
  const p = planRow(row(settled), person({ portal: 'no' }));
  assert.equal(p.action, 'revoke');
  assert.deepEqual(p.fields, { 'Access Level': 'Revoked' });
});

test('Portal Access = No leaves Call Needed alone', () => {
  // Attio has no Call Needed option, so it maps to No. Writing Revoked here would quietly demote
  // everyone still waiting on an intro call.
  const p = planRow(row({ ...settled, 'Access Level': 'Call Needed' }), person({ portal: 'no' }));
  assert.equal(p.action, 'skip');
  assert.match(p.reason, /already "Call Needed"/);
});

test('Portal Access = No does not re-revoke', () => {
  assert.equal(planRow(row({ ...settled, 'Access Level': 'Revoked' }), person({ portal: 'no' })).action, 'skip');
});

test('a row already in step costs nothing', () => {
  const p = planRow(row(settled), person({ portal: 'yes' }));
  assert.equal(p.action, 'skip');
  assert.equal(p.reason, 'already in step');
});

test('Portal Access = Yes approves a Call Needed row', () => {
  const p = planRow(row({ ...settled, 'Access Level': 'Call Needed' }), person({ portal: 'yes' }));
  assert.equal(p.action, 'approve');
  assert.equal(p.fields['Access Level'], 'Approved');
});

test('an approved row with no welcome stamp still gets the welcome', () => {
  const f = { ...settled };
  delete f['Welcome Email Sent'];
  const p = planRow(row(f), person({ portal: 'yes' }));
  assert.equal(p.action, 'approve');
  assert.equal(p.needsWelcome, true);
  assert.deepEqual(p.fields, {}, 'nothing to change, but the email is owed');
});

test('a migrated row is not re-welcomed', () => {
  const p = planRow(row({ ...settled, 'Welcome Email Sent': 'Migrated 2026-09-03 (legacy portal user — no email sent)' }), person({ portal: 'yes' }));
  assert.equal(p.action, 'skip');
});

test('level 2 granted in Attio is written and flagged for the email', () => {
  const p = planRow(row({ ...settled, 'Level 2 Access': 'Requested' }), person({ portal: 'yes', level2: 'yes' }));
  assert.equal(p.action, 'approve');
  assert.equal(p.fields['Level 2 Access'], 'Approved');
  assert.match(p.fields['Level 2 Approved On'], /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(p.grantedL2, true);
});

test('level 2 already approved sends nothing', () => {
  const p = planRow(row({ ...settled, 'Level 2 Access': 'Approved' }), person({ portal: 'yes', level2: 'yes' }));
  assert.equal(p.action, 'skip');
});

test('a level 2 request is recorded without an email', () => {
  const p = planRow(row({ ...settled, 'Level 2 Access': 'Not Approved' }), person({ portal: 'yes', level2: 'requested' }));
  assert.equal(p.fields['Level 2 Access'], 'Requested');
  assert.equal(p.grantedL2, false);
  assert.equal('Level 2 Approved On' in p.fields, false);
});

test("the person's exchange dates fill the empty date fields", () => {
  const p = planRow(row({ 'Access Level': 'Approved', 'Welcome Email Sent': 'x' }),
    person({ portal: 'yes', closing: '2026-10-01', day45: '2026-11-15', day180: '2027-03-30' }));
  assert.equal(p.action, 'approve');
  assert.equal(p.fields['Start Date'], '2026-10-01');
  assert.equal(p.fields['ID Period Expiration'], '2026-11-15');
  assert.equal(p.fields['1031 Expiration'], '2027-03-30');
});

test('dates already on the row are never overwritten', () => {
  const p = planRow(row(settled), person({ portal: 'yes', closing: '2099-01-01', day45: '2099-01-02', day180: '2099-01-03' }));
  assert.equal(p.action, 'skip');
});

test('a date neither side has is deferred, not written', () => {
  const f = { 'Access Level': 'Approved', 'Welcome Email Sent': 'x' };
  const p = planRow(row(f), person({ portal: 'yes' }));
  assert.equal(p.action, 'skip', 'a missing date on its own is not work');
  assert.equal(p.datesMissing, true, 'but an open deal is worth a look later');
});

test("Jerry's own row, as it actually stands", () => {
  // Airtable: Approved, no Welcome Email Sent, no dates. Attio: Portal Access set to Yes at 00:02Z.
  const r = row({ 'Email Address': 'jerry@baker1031.com', 'Access Level': 'Approved', 'Access Changed At': '2026-09-03T01:14:00.000Z' });
  const p = planRow(r, person({ email: 'jerry@baker1031.com', portal: 'yes' }));
  assert.equal(p.action, 'approve');
  assert.equal(p.needsWelcome, true);
  assert.deepEqual(p.fields, {});
  assert.equal(p.datesMissing, true);
});

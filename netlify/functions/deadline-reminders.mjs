/*
  Baker 1031 — automated 1031-exchange deadline reminders
  Runs daily (netlify.toml schedule, 15:00 UTC ≈ 8am PT); reads the Airtable
  "Investors" table and emails via Resend.

  Three email types (built in lib/invites.mjs):
    - 45-day identification reminders  → 30 / 14 / 7 / 2 days before
      "ID Period Expiration"
    - 180-day completion reminders     → DISABLED per Jerry (SEND_180_REMINDERS
      flag below; flip to true to enable at 60 / 30 / 14 / 7 days)
    - Sale-date check-ins              → monthly while "Start Date" is more
      than 45 days away (asks for updates before the clock starts)

  Opt-out: every email carries a personal "stop these reminders" link
  (/api/reminders-off) that checks the row's "Reminders Off" box; checked
  rows are skipped entirely. Uncheck in Airtable to resume.

  Access Level "Approved"  → magic portal login button (30-day link)
  anything else (not Revoked) → schedule-a-call button
  Revoked rows and rows without an email are skipped.

  Every email includes a personal "update my dates" link (the same signed
  /update-my-info/ link the qualification emails use), built by looking up the
  contact in GHL by email. If the contact can't be found, the email says
  "reply to update" instead.

  Duplicate protection: each send appends a line to the row's "Reminder Log"
  (e.g. "id-14 sent 2026-09-03"). A reminder key that already appears in the
  log is never re-sent — delete the line in Airtable to allow a re-send.
  At most ONE email per investor per day (most urgent wins: id > exchange >
  check-in).

  Manual runs: POST ?key=<PORTAL_SYNC_KEY>          → live run
               POST ?key=<PORTAL_SYNC_KEY>&dry=1    → report only, no sends
               add &only=<email>                     → restrict to one row
  Scheduled invocations (Netlify sends {"next_run":...}) always run live.
*/

import crypto from 'node:crypto';
import { buildDeadlineReminder, buildSaleCheckin, sendViaResend } from './lib/invites.mjs';
import { linkSig } from './login-link.mjs';
import { offSig } from './reminders-off.mjs';

const GHL = 'https://services.leadconnectorhq.com';
const AT_BASE = process.env.ACCESS_BASE_ID || 'appiKLSyAUmP0h8cJ';
const AT_TABLE = process.env.ACCESS_TABLE_ID || 'tblbuFMpfv5R4DIyp';

// Ascending: the selector picks the TIGHTEST bracket >= days-left, so each
// threshold fires once as the deadline approaches (30 → 14 → 7 → 2), and a
// row added late skips straight to its current bracket instead of catching up.
const ID_OFFSETS = [2, 7, 14, 30];       // days before ID Period Expiration
const EXCH_OFFSETS = [7, 14, 30, 60];    // days before 1031 Expiration
const SEND_180_REMINDERS = false;        // per Jerry (Sept 3): 45-day only
const CHECKIN_MIN_DAYS_OUT = 45;         // sale date must be at least this far out

const json = (s, b) => ({ statusCode: s, headers: { 'content-type': 'application/json' }, body: JSON.stringify(b) });

async function at(pathname, init = {}) {
  const res = await fetch(`https://api.airtable.com/v0/${AT_BASE}/${AT_TABLE}${pathname}`, {
    ...init,
    headers: { Authorization: `Bearer ${process.env.AIRTABLE_TOKEN}`, 'content-type': 'application/json', ...(init.headers || {}) },
  });
  if (!res.ok) throw new Error(`Airtable ${res.status}: ${(await res.text()).slice(0, 150)}`);
  return res.json();
}

async function allRows() {
  const rows = [];
  let offset;
  do {
    const data = await at(`?pageSize=100${offset ? `&offset=${offset}` : ''}`);
    rows.push(...(data.records || []));
    offset = data.offset;
  } while (offset);
  return rows;
}

const dayMs = 86400000;
const toUTC = (iso) => Date.parse(String(iso).slice(0, 10) + 'T00:00:00Z');
const daysUntil = (iso, today) => Math.round((toUTC(iso) - today) / dayMs);

// Personal signed update link (same scheme as lead.mjs / my-info.mjs).
async function updateLinkFor(email, gh, base) {
  try {
    const r = await fetch(`${GHL}/contacts/search/duplicate?locationId=${process.env.GHL_LOCATION_ID}&email=${encodeURIComponent(email)}`, { headers: gh });
    const cid = r.ok ? ((await r.json()).contact || {}).id : null;
    if (!cid) return null;
    const sig = crypto.createHmac('sha256', process.env.SESSION_SECRET || '').update('myinfo:' + cid).digest('hex').slice(0, 32);
    return `${base}/update-my-info/?cid=${cid}&sig=${sig}`;
  } catch { return null; }
}

export const handler = async (event) => {
  const q = (event && event.queryStringParameters) || {};
  let body = {};
  try { body = JSON.parse((event && event.body) || '{}'); } catch {}
  const isScheduled = !!body.next_run;
  const keyed = process.env.PORTAL_SYNC_KEY && q.key === process.env.PORTAL_SYNC_KEY;
  if (!isScheduled && !keyed) return json(403, { error: 'forbidden' });
  const dry = keyed && q.dry === '1';
  const only = keyed && q.only ? String(q.only).toLowerCase() : null;

  if (!process.env.AIRTABLE_TOKEN) return json(500, { error: 'AIRTABLE_TOKEN not configured' });
  const base = process.env.URL || 'https://baker1031.com';
  const gh = { Authorization: `Bearer ${process.env.GHL_Key || process.env.GHL_API_KEY}`, Version: '2021-07-28', 'content-type': 'application/json' };

  const now = new Date();
  const today = toUTC(now.toISOString());
  const todayStr = now.toISOString().slice(0, 10);
  const month = todayStr.slice(0, 7);

  const rows = await allRows();
  const report = [];
  let sent = 0;

  for (const row of rows) {
    const f = row.fields || {};
    const email = String(f['Email Address'] || '').trim();
    const level = typeof f['Access Level'] === 'object' ? f['Access Level']?.name : f['Access Level'];
    if (!email || level === 'Revoked' || f['Reminders Off']) continue;
    if (only && email.toLowerCase() !== only) continue;

    const log = String(f['Reminder Log'] || '');
    const first = f['First Name'] || 'there';
    const hasAccess = level === 'Approved';

    // Most urgent due reminder wins; one email per row per run.
    let due = null; // {key, type, kind?, dateISO?, daysLeft?}
    const idExp = f['ID Period Expiration'];
    const exch = f['1031 Expiration'];
    const start = f['Start Date'];

    if (idExp) {
      const d = daysUntil(idExp, today);
      if (d >= 0) {
        const off = ID_OFFSETS.find((o) => d <= o); // tightest bracket only
        if (off !== undefined && !log.includes(`id-${off} `)) due = { key: `id-${off}`, type: 'deadline', kind: 'id', dateISO: idExp, daysLeft: d };
      }
    }
    if (!due && exch && SEND_180_REMINDERS) {
      const d = daysUntil(exch, today);
      if (d >= 0) {
        const off = EXCH_OFFSETS.find((o) => d <= o); // tightest bracket only
        if (off !== undefined && !log.includes(`x-${off} `)) due = { key: `x-${off}`, type: 'deadline', kind: 'exchange', dateISO: exch, daysLeft: d };
      }
    }
    if (!due && start) {
      const d = daysUntil(start, today);
      if (d > CHECKIN_MIN_DAYS_OUT && !log.includes(`chk-${month} `)) {
        due = { key: `chk-${month}`, type: 'checkin', dateISO: start, daysLeft: d };
      }
    }
    if (!due) continue;

    if (dry) { report.push({ email, level, due: due.key, date: due.dateISO, daysLeft: due.daysLeft }); continue; }

    // Build links.
    const scheduleLink = `${base}/schedule-call/`;
    let loginLink = null;
    if (hasAccess && process.env.SESSION_SECRET) {
      const t = Date.now();
      loginLink = `${base}/api/login-link?rid=${row.id}&t=${t}&sig=${linkSig(row.id, t)}`;
    }
    const updateLink = await updateLinkFor(email, gh, base);
    const optOutLink = `${base}/api/reminders-off?rid=${row.id}&sig=${offSig(row.id)}`;

    const msg = due.type === 'deadline'
      ? buildDeadlineReminder({ first, kind: due.kind, dateISO: due.dateISO, daysLeft: due.daysLeft, hasAccess, loginLink, scheduleLink, updateLink, optOutLink })
      : buildSaleCheckin({ first, saleISO: due.dateISO, hasAccess, loginLink, scheduleLink, updateLink, optOutLink });

    const ok = await sendViaResend(email, msg.subject, msg.html);
    if (ok) {
      sent++;
      const line = `${due.key} sent ${todayStr}`;
      await at(`/${row.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ fields: { 'Reminder Log': log ? `${log}\n${line}` : line } }),
      }).catch((e) => console.error('[reminders] log write:', e.message));
      report.push({ email, level, sent: due.key });
    } else {
      report.push({ email, level, failed: due.key });
    }
  }

  console.log(`[reminders] ${dry ? 'DRY ' : ''}rows=${rows.length} sent=${sent}`);
  return json(200, { ok: true, dry, rows: rows.length, sent, report });
};

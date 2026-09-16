/*
  Shared invitation logic for lead.mjs (initial submission) and my-info.mjs
  (self-service corrections).

  Flow:
    - Qualified (accredited-indicated + U.S.) → scheduling email:
        exchange path → /schedule-call/     cash path → /schedule-consultation/
    - Not U.S.       → residency notice with the personal update link
    - Not accredited → accreditation notice with the personal update link
      (residency takes precedence when both fail)

  Duplicate protection ("Intro Invite Status" person attribute in Attio, when it exists):
    - "invited …"  → never auto-send another scheduling email, even after updates
    - "notice …"   → the same notice is not re-sent on later updates
*/

export const STATUS_FIELD = 'Intro Invite Status';

// The 2026 registration form sends the net-worth / income *ranges* it showed (plus its own
// `accreditedLikely` verdict); the previous request-access form sent numeric income and shorter
// range labels. Both shapes are handled so corrections through update-my-info keep working.
export function accreditedSignal(lead) {
  if (typeof lead.accreditedLikely === 'boolean') return lead.accreditedLikely ? 'Indicated' : 'Unclear';
  const nw = String(lead.netWorth || '');
  const worthOk = nw !== '' && !/^under/i.test(nw);
  const joint = lead.marital === 'Married' || lead.marital === 'Domestic partnership';
  const inc = lead.income;
  let incomeOk = false;
  if (typeof inc === 'number') incomeOk = inc >= (joint ? 300000 : 200000);
  else if (typeof inc === 'string' && inc) incomeOk = joint ? !/^(under|\$200,000)/i.test(inc) : !/^under/i.test(inc);
  return worthOk || incomeOk ? 'Indicated' : 'Unclear';
}

// U.S. by phone region (2026 form) or by state (previous form); unknown counts as U.S.
export function isUS(lead) {
  if (lead.phoneRegion) return lead.phoneRegion === 'US';
  if (lead.state) return lead.state !== 'Outside United States';
  return true;
}

// 'exchange' | 'cash' when qualified; null otherwise
export function inviteVariant(lead) {
  if (accreditedSignal(lead) !== 'Indicated' || !isUS(lead)) return null;
  return lead.path === 'exchange' ? 'exchange' : 'cash';
}

// 'residency' | 'accreditation' when not qualified; null when qualified
export function noticeKind(lead) {
  if (!isUS(lead)) return 'residency';
  if (accreditedSignal(lead) !== 'Indicated') return 'accreditation';
  return null;
}

const P = 'style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:21px;color:#243856;margin:0 0 16px;"';
const BTN = 'style="display:inline-block;background:#243856;color:#ffffff;font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:bold;text-decoration:none;padding:13px 28px;border-radius:2px;"';

const SITE_BASE = (process.env.URL || 'https://baker1031.com').replace(/\/$/, '');
const SIG = `<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:21px;color:#243856;">-Jerry</div>
<br>
<table cellpadding="0" cellspacing="0" border="0" width="640" style="border-collapse:collapse;table-layout:fixed;width:640px;max-width:100%;font-family:Arial,Helvetica,sans-serif"><tbody>
<tr><td style="padding:0;font-family:Arial,Helvetica,sans-serif"><div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:21px;font-weight:bold;color:#243856">Gerald F. Baker, III</div><div style="font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#243856">Founder &amp; Managing Principal | Baker 1031 Investments</div></td></tr>
<tr><td style="padding:0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#666666"><b style="font-weight:bold;color:#666666">Office +1 415 991 4895</b><span> | </span><span>Mobile +1 310 905 7706</span></td></tr>
<tr><td style="padding:0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px"><a href="mailto:jerry@baker1031.com" rel="noopener noreferrer" style="font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#666666;text-decoration:underline" target="_blank">jerry@baker1031.com</a></td></tr>
<tr><td style="padding:22px 0 18px 0"><a href="https://baker1031.com" rel="noopener noreferrer" style="text-decoration:none;border:0" target="_blank"><img src="${SITE_BASE}/assets/media/logo.png" alt="Baker 1031 Investments" width="200" height="37" style="display:block;width:200px;height:37px;border:0;outline:none;text-decoration:none"></a></td></tr>
<tr><td style="padding:0 0 10px 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px"><br></td></tr>
<tr><td style="padding:0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#000000">1700 Montgomery St, Ste 108 | San Francisco, CA 94111</td></tr>
<tr><td style="padding:0 0 15px 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px"><a href="https://baker1031.com" rel="noopener noreferrer" style="font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:18px;color:#243856;text-decoration:none" target="_blank">baker1031.com</a></td></tr>
<tr><td width="640" style="width:640px;padding:0;font-family:Arial,Helvetica,sans-serif;font-size:8px;line-height:12px;color:#808080"><div style="padding-bottom:8px;font-family:Arial,Helvetica,sans-serif;font-size:8px;line-height:12px;color:#808080">Securities offered through Aurora Securities, Inc. (ASI), Member: FINRA/SIPC. Baker 1031 Investments is independent of ASI.</div><div style="font-family:Arial,Helvetica,sans-serif;font-size:8px;line-height:12px;color:#808080">Please note that this email is subject to the regulatory review and retention policies of Baker 1031 Investments, LLC and Aurora Securities, Inc. Neither this email nor any attachments constitute an offer to sell or a solicitation of an offer to purchase securities. Any such offer shall be made solely pursuant to the applicable PPM or Prospectus. Any information contained in this email or its attachments may contain errors; please review the PPM for correct information prior to investing. Delaware Statutory Trust (DST) investments are illiquid and involve a high degree of risk. Investment offerings may sell out quickly; even if an investment is shown as available, the only way to ensure participation is through a closed transaction. The investment sponsor is responsible for the closing process and final availability, not Jerry Baker or Baker 1031 Investments. Information provided is for educational purposes and should not be relied upon for investment, tax, or legal decisions. Past performance and forward-looking statements are never an assurance of future results.</div></td></tr>
</tbody></table>`;

const wrap = (inner) => `<!doctype html><html><body style="margin:0;padding:0;background:#ffffff;">
<div style="max-width:640px;margin:0;padding:24px 20px;">
${inner}
  <p ${P}>Thank you,</p>
  ${SIG}
</div>
</body></html>`;

export function buildInvite(variant, first, base) {
  const link = variant === 'exchange' ? `${base}/schedule-call/` : `${base}/schedule-consultation/`;
  const middle = variant === 'exchange'
    ? "The last step is a quick introductory call. Regulators require it before I can open the current investments to you, and honestly it's the fastest way for me to point you at what fits."
    : "The last step is a quick introductory call. Regulators require it before I can open the current investments to you, and it's the best way for me to understand what you're trying to accomplish before I point you at anything.";
  return {
    subject: 'One step left - schedule your introductory call',
    html: wrap(`  <p ${P}>Hi ${first} -</p>
  <p ${P}>Thanks for registering - I appreciate it, and I've read through what you shared.</p>
  <p ${P}>${middle}</p>
  <p style="margin:24px 0;"><a href="${link}" ${BTN}>Schedule your introductory call</a></p>
  <p ${P}>It's about 30 minutes. If none of the times work, just reply to this email and we'll find one that does.</p>`),
  };
}

export function buildNotice(kind, first, updateLink) {
  if (kind === 'residency') {
    return {
      subject: 'Quick question about your registration',
      html: wrap(`  <p ${P}>Hi ${first} -</p>
  <p ${P}>Thanks for registering.</p>
  <p ${P}>The investments I offer are limited to U.S. citizens and permanent residents (for an entity, all of its owners need to meet that requirement). Your submission listed you outside the United States, so I wanted to check before we go further.</p>
  <p ${P}>If you're a U.S. citizen or green-card holder living abroad, or the location was just a mistake, update your submission and everything picks back up automatically:</p>
  <p style="margin:24px 0;"><a href="${updateLink}" ${BTN}>Update my information</a></p>
  <p ${P}>Either way, feel free to reply - I'm happy to answer questions.</p>`),
    };
  }
  return {
    subject: 'Quick question about your registration',
    html: wrap(`  <p ${P}>Hi ${first} -</p>
  <p ${P}>Thanks for registering, and for being straightforward with your answers.</p>
  <p ${P}>Based on what you shared, it looks like the accredited-investor requirements may not be met. That matters because the investments I offer are private placements, and regulators limit them to accredited investors - generally net worth over $1M excluding your home, or income over $200K ($300K jointly).</p>
  <p ${P}>If any of those numbers were entered wrong, or your situation has changed, update your submission and everything picks back up automatically:</p>
  <p style="margin:24px 0;"><a href="${updateLink}" ${BTN}>Update my information</a></p>
  <p ${P}>Either way, feel free to reply - I'm happy to answer questions.</p>`),
    };
}

// Portal-approval welcome. loginLink signs the person in automatically the
// first time (magic link, valid 30 days, dies instantly if access is revoked).
export function buildWelcome(first, loginLink, base) {
  return {
    subject: 'Your investor portal access is ready',
    html: wrap(`  <p ${P}>Hi ${first} -</p>
  <p ${P}>Good news - your access to the Baker 1031 investor portal is set up. You can now review the current investments, offering details, and documents.</p>
  <p style="margin:24px 0;"><a href="${loginLink}" ${BTN}>View current investments</a></p>
  <p ${P}>That button signs you in automatically - no password needed. After the first visit, you can log in anytime at <a href="${base}/login/" style="color:#243856;">${base.replace(/^https?:\/\//, '')}/login/</a> using this email address.</p>
  <p ${P}>If you have questions about anything you see, just reply - I'm happy to walk through it with you.</p>`),
  };
}

// ---- level 2 (restricted pages) ------------------------------------------

// To Jerry, when an investor asks to be let into a restricted page.
export function buildLevel2Request(name, email, path) {
  const where = path ? `${SITE_BASE}${path}` : 'the investor portal';
  return {
    subject: `Access request: ${name || email}`,
    html: wrap(`  <p ${P}>${name || email} asked for access to a restricted page.</p>
  <p ${P}><strong>Page:</strong> <a href="${where}" style="color:#243856;">${where}</a><br>
  <strong>Email:</strong> ${email}</p>
  <p ${P}>They are already an approved investor, so this is the second tier only. To grant it, open their
  record in Attio and set <strong>Portal Access - Level 2</strong> to <strong>Yes</strong> — the site picks
  it up and emails them.</p>`),
  };
}

// To the investor, once, when level 2 is granted.
export function buildLevel2Granted(first, base) {
  return {
    subject: 'Your access has been extended',
    html: wrap(`  <p ${P}>Hi ${first} -</p>
  <p ${P}>I have opened up the additional material you asked about. Next time you are logged in it will be
  there — nothing else to do on your end.</p>
  <p style="margin:24px 0;"><a href="${base}/login/" ${BTN}>Log in</a></p>
  <p ${P}>As always, if anything raises a question, just reply and I will walk you through it.</p>`),
  };
}

// ---- 1031 deadline reminders (sent by deadline-reminders.mjs) -------------

const fmtDate = (iso) => {
  const d = new Date(String(iso).slice(0, 10) + 'T12:00:00Z');
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
};

const LINKBTN = 'style="color:#243856;text-decoration:underline;font-family:Arial,Helvetica,sans-serif;font-size:14px;"';

const optOutLine = (optOutLink) => optOutLink
  ? `<p style="font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:17px;color:#8A93A0;margin:26px 0 0;">You're receiving these reminders because you have a 1031 exchange on file with me. <a href="${optOutLink}" style="color:#8A93A0;text-decoration:underline;">Stop these reminders</a> - your portal access and everything else is unaffected.</p>`
  : '';

// kind: 'id' (45-day identification) | 'exchange' (180-day completion)
// hasAccess=true → loginLink button; false → scheduleLink button. updateLink optional.
export function buildDeadlineReminder({ first, kind, dateISO, daysLeft, hasAccess, loginLink, scheduleLink, updateLink, optOutLink }) {
  const dateStr = fmtDate(dateISO);
  const what = kind === 'id'
    ? 'your 45-day identification window closes'
    : 'your 180-day exchange completion deadline is';
  const days = daysLeft === 1 ? 'tomorrow' : `in ${daysLeft} days`;
  const subject = kind === 'id'
    ? `Your 45-day identification deadline — ${dateStr}`
    : `Your 180-day exchange deadline — ${dateStr}`;
  const urgency = kind === 'id'
    ? 'Identification is the step with the least room for error — replacement property must be formally identified in writing by that date, and the IRS does not grant extensions.'
    : 'Your exchange must be fully completed — replacement property closed — by that date. The IRS does not grant extensions.';
  const cta = hasAccess
    ? `<p ${P}>You have portal access, so the current investments are ready for you to review any time:</p>
  <p style="margin:24px 0;"><a href="${loginLink}" ${BTN}>Review current investments</a></p>`
    : `<p ${P}>The fastest way to keep your options open is a quick introductory call — regulators require it before I can open the current investments to you:</p>
  <p style="margin:24px 0;"><a href="${scheduleLink}" ${BTN}>Schedule your introductory call</a></p>`;
  const upd = updateLink
    ? `<p ${P}>If your closing moved or these dates aren't right, take 30 seconds to fix them so my reminders stay accurate: <a href="${updateLink}" ${LINKBTN}>update my dates</a>.</p>`
    : `<p ${P}>If your closing moved or these dates aren't right, just reply to this email and I'll fix them.</p>`;
  return {
    subject,
    html: wrap(`  <p ${P}>Hi ${first} -</p>
  <p ${P}>A quick reminder from my calendar: ${what} on <b>${dateStr}</b> — ${days}.</p>
  <p ${P}>${urgency}</p>
${cta}
${upd}
${optOutLine(optOutLink)}`),
  };
}

// Periodic check-in for people whose sale/closing date is still a ways out.
export function buildSaleCheckin({ first, saleISO, hasAccess, loginLink, scheduleLink, updateLink, optOutLink }) {
  const dateStr = fmtDate(saleISO);
  const cta = hasAccess
    ? `<p ${P}>In the meantime, you're welcome to browse the current investments whenever you like - it's a good way to get a feel for what's available before your clock starts:</p>
  <p style="margin:24px 0;"><a href="${loginLink}" ${BTN}>Review current investments</a></p>`
    : `<p ${P}>If you'd like to get ahead of it, a quick introductory call now means everything is open to you before your clock starts:</p>
  <p style="margin:24px 0;"><a href="${scheduleLink}" ${BTN}>Schedule your introductory call</a></p>`;
  const upd = updateLink
    ? `<p ${P}>Has anything changed - closing moved, deal restructured, timing shifted? <a href="${updateLink}" ${LINKBTN}>Update your dates here</a> and my reminders will track the new schedule automatically.</p>`
    : `<p ${P}>Has anything changed - closing moved, deal restructured, timing shifted? Just reply and I'll update your file.</p>`;
  return {
    subject: `Checking in ahead of your ${dateStr} sale`,
    html: wrap(`  <p ${P}>Hi ${first} -</p>
  <p ${P}>I have your property sale on file for <b>${dateStr}</b>. Once that closes, your 45-day identification window starts running, so I like to check in ahead of time.</p>
${upd}
${cta}
  <p ${P}>And if anything about the exchange is on your mind before then, reply anytime.</p>
${optOutLine(optOutLink)}`),
  };
}

export async function sendViaResend(to, subject, html, from = 'Jerry Baker <jerry@baker1031.com>') {
  const rk = process.env.RESEND_API_KEY;
  if (!rk) return false;
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${rk}`, 'content-type': 'application/json' },
    body: JSON.stringify({ from, to: [to], reply_to: 'jerry@baker1031.com', subject, html }),
  });
  if (!r.ok) { console.error('[invites] send failed', r.status, (await r.text()).slice(0, 200)); return false; }
  return true;
}

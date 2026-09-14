/*
  Baker 1031 — shape of a website lead: naming, commission estimate, and the attribute pairs written to Attio.
  Shared by lead.mjs (registration) and my-info.mjs (self-service corrections).
*/
import { accreditedSignal } from './invites.mjs';

// ---- commission + naming -------------------------------------------------
export function commissionValue(lead) {
  const base = lead.path === 'exchange' ? lead.equity : lead.amount;
  return base ? Math.round(base * 0.9 * 0.05) : 0;
}
export function dealType(lead) {
  if (lead.path !== 'exchange') return 'Cash';
  const objs = lead.objectives || [];
  return objs.includes('Planning a 1033 exchange') && !objs.includes('Planning a 1031 exchange') ? '1033' : '1031';
}
// "Last Name, First Name - 1031/1033/Cash - Role"
export function dealName(lead) {
  const who = [lead.lastName, lead.firstName].filter(Boolean).join(', ') || lead.email;
  return [who, dealType(lead), lead.role || ''].filter(Boolean).join(' - ');
}
export function addDays(iso, days) {
  const d = new Date(iso + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// person-level attribute pairs (filled only where an attribute with that title exists in Attio)
export function personPairs(lead, extra = {}) {
  return [
    ['Role (This Transaction)', lead.role],
    ['Marital Status', lead.marital],
    ['Net Worth Range', lead.netWorth],
    ['Household Income', lead.income],
    ['Accredited Signal', accreditedSignal(lead)],
    ['Exchange Fit', lead.fit],
    ['Lead Source', lead.source || 'baker1031.com registration'],
    ['Acknowledgments Timestamp', lead.submittedAt],
    ...Object.entries(extra),
  ];
}
export function dealPairs(lead) {
  return [
    ['Sale Date', lead.saleDate],
    ['45-Day Deadline', lead.saleDate ? addDays(lead.saleDate, 45) : null],
    ['180-Day Deadline', lead.saleDate ? addDays(lead.saleDate, 180) : null],
    ['Exchange Equity', lead.equity],
    ['Replacement Debt', lead.debt],
    ['Exchange Fit', lead.fit],
    ['Objectives', lead.objectives],
    ['Cash Amount', lead.amount],
    ['Deal Type', dealType(lead)],
  ];
}


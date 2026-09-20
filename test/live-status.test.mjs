/*
  Live offering status between builds: the build marks each offering (data-opp-slug / data-opp-status), and
  /assets/js/live-status.js corrects the status from the Opportunities feed. No network and no browser: the page
  builders run against a scratch site root, the listing's own script runs in a vm with a stub DOM, and the feed is a stub.
  Run:  npm test   (needs python3 for the builder half; it is skipped without it)
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const live = createRequire(import.meta.url)(path.join(ROOT, 'assets/js/live-status.js'));
const OFFERINGS = JSON.parse(fs.readFileSync(path.join(ROOT, 'build/offerings.json'), 'utf8'));

// ---- a tiny DOM: elements with attributes, className, textContent and attribute-selector queries ----
class El {
  constructor(attrs = {}, children = [], text = '') { this.attrs = { ...attrs }; this.children = children; this.textContent = text; this.className = attrs.class || ''; delete this.attrs.class; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  hasAttribute(k) { return k in this.attrs; }
  querySelectorAll(sel) {
    const name = /^\[([a-z-]+)\]$/.exec(sel)[1], out = [];
    const walk = (n) => n.children.forEach((c) => { if (c.hasAttribute(name)) out.push(c); walk(c); });
    walk(this); return out;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
const docOf = (...children) => { const d = new El({}, children); d.events = []; d.dispatchEvent = (e) => { d.events.push(e); return true; }; return d; };
const has = (el, c) => el.className.split(/\s+/).includes(c);

function feed(list) { return { updatedAt: '2026-09-19T00:00:00Z', count: list.length, opportunities: list }; }
function memStorage() { const m = new Map(); return { m, getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)) }; }
function fetchStub(body, { ok = true, fail = false } = {}) {
  const calls = [];
  const f = async (url, init) => { calls.push({ url, init }); if (fail) throw new TypeError('Failed to fetch'); return { ok, json: async () => body }; };
  f.calls = calls; return f;
}

// ---- the builders ----
function buildPages() {
  const py = spawnSync('python3', ['--version']);
  if (py.status !== 0) return null;
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'b1031-live-'));
  fs.copyFileSync(path.join(ROOT, 'index.html'), path.join(tmp, 'index.html'));
  fs.mkdirSync(path.join(tmp, 'assets/media'), { recursive: true });
  fs.symlinkSync(path.join(ROOT, 'assets/media/offerings'), path.join(tmp, 'assets/media/offerings')); // same image paths, so build/inventory_template.html is rewritten unchanged
  for (const s of ['build_inventory.py', 'build_offering.py']) {
    const r = spawnSync('python3', [path.join(ROOT, 'build', s)], { cwd: path.join(ROOT, 'build'), env: { ...process.env, SITE_ROOT: tmp }, encoding: 'utf8' });
    assert.equal(r.status, 0, s + ' failed: ' + r.stderr);
  }
  return tmp;
}
const built = buildPages();

test('offering pages carry the slug, the built status and the script', { skip: !built && 'python3 not available' }, () => {
  for (const o of OFFERINGS) {
    const html = fs.readFileSync(path.join(built, 'offerings', o.slug, 'index.html'), 'utf8');
    const row = new RegExp(`<div data-opp-slug="${o.slug}" data-opp-status="${o.status || 'Available'}"><dt>Availability Status</dt><dd><span class="status[^"]*" data-opp-label="full">([^<]*)</span>`).exec(html);
    assert.ok(row, o.slug + ': status row not marked');
    assert.equal(row[1], o.status === 'Closed' ? 'Closed — no longer available' : (o.status || 'Available'));
    assert.match(html, new RegExp(`<a href="/invest/" data-opp-crumb="${o.slug}">`));
    assert.match(html, /<script defer src="\/assets\/js\/live-status\.js"><\/script>\s*<\/body>/);
  }
  assert.ok(OFFERINGS.some((o) => o.status === 'Closed'), 'the snapshot has a closed deal, so the wording above was exercised');
});

// Run the listing's own script against a stub DOM, logged in, and return what it rendered plus its event listeners.
function runListing(html) {
  const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]).find((s) => s.includes('var OFFERINGS ='));
  assert.ok(script, 'listing script found');
  const els = {}, listeners = {};
  const stub = () => ({ innerHTML: '', hidden: false, value: 'rec', dataset: {}, style: {}, children: [], className: '', textContent: '', clientWidth: 2000, offsetWidth: 10,
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false }, appendChild() {}, addEventListener() {}, setAttribute() {}, removeAttribute() {},
    querySelector: () => stub(), querySelectorAll: () => [], getBoundingClientRect: () => ({ top: 0, right: 0 }), focus() {} });
  const document = {
    documentElement: { classList: { contains: (c) => c === 'is-logged-in' } },
    body: stub(),
    getElementById: (id) => (els[id] ||= stub()),
    createElement: () => stub(),
    querySelector: () => stub(),
    querySelectorAll: () => [],
    addEventListener: (type, fn) => { (listeners[type] ||= []).push(fn); },
  };
  const window = { matchMedia: () => ({ matches: true }), innerWidth: 1400, innerHeight: 900, addEventListener() {} };
  vm.runInNewContext(script, { document, window, localStorage: { getItem: () => null, setItem() {} }, console });
  const cards = () => [...els.grid.innerHTML.matchAll(/<div class="(card[^"]*)" data-opp-slug="([^"]+)" data-opp-status="([^"]+)" data-opp-muted-class="card--sold">[\s\S]*?<span class="status([^"]*)" data-opp-label="short" title="([^"]*)">([^<]*)<\/span>/g)]
    .map((m) => ({ cls: m[1], slug: m[2], status: m[3], pillCls: m[4].trim(), title: m[5], label: m[6] }));
  return { els, listeners, cards };
}

test('listing cards and rows carry the attributes; the live event re-renders with the build rules', { skip: !built && 'python3 not available' }, () => {
  const html = fs.readFileSync(path.join(built, 'invest', 'index.html'), 'utf8');
  assert.match(html, /<script defer src="\/assets\/js\/live-status\.js"><\/script>\s*<\/body>/);
  const { els, listeners, cards } = runListing(html);
  let c = cards();
  assert.equal(c.length, OFFERINGS.length, 'every card is marked');
  assert.match(els.tbody.innerHTML, /<tr data-id="[^"]+"( class="is-sold")? data-opp-slug="[^"]+" data-opp-status="[^"]+" data-opp-muted-class="is-sold">/);
  const open = OFFERINGS.filter((o) => ['Available', 'Limited Availability'].includes(o.status)).map((o) => o.slug);
  assert.ok(open.length >= 3);

  // live: the first open deal closed, the second is limited, the third has left the feed
  const [closing, limited, gone] = open;
  const bySlug = {};
  for (const o of OFFERINGS) if (o.slug !== gone) bySlug[o.slug] = { status: o.slug === closing ? 'Closed' : o.slug === limited ? 'Limited Availability' : o.status };
  listeners['b1031:live-status'].forEach((fn) => fn({ detail: { bySlug } }));
  c = cards();
  const at = (slug) => c.findIndex((x) => x.slug === slug);
  const isOpen = (x) => ['Available', 'Limited Availability'].includes(x.status);
  const firstMuted = c.findIndex((x) => !isOpen(x));
  assert.ok(firstMuted > 0 && c.slice(firstMuted).every((x) => !isOpen(x)), 'featured order: open deals first, the rest after');
  assert.ok(c.every((x) => /card--sold/.test(x.cls) === ['Closed', 'Rejected', 'No longer available'].includes(x.status)), 'closed, rejected and gone are dimmed, nothing else');
  assert.deepEqual(c[at(closing)], { ...c[at(closing)], cls: 'card card--sold', status: 'Closed', pillCls: 'status--sold', title: 'Closed — no longer available', label: 'Closed' });
  assert.deepEqual(c[at(gone)], { ...c[at(gone)], cls: 'card card--sold', status: 'No longer available', pillCls: 'status--sold', label: 'Unavailable' });
  assert.deepEqual(c[at(limited)], { ...c[at(limited)], cls: 'card', status: 'Limited Availability', pillCls: 'status--limited', label: 'Limited' });
  assert.ok(at(closing) >= firstMuted && at(gone) >= firstMuted && at(limited) < firstMuted);
});

test('the script corrects status, pill, dimming and breadcrumb in place', () => {
  const pill = (slug, status, kind) => new El({ class: 'status', 'data-opp-label': kind }, [], status);
  const offer = new El({ 'data-opp-slug': 'harbor-dst', 'data-opp-status': 'Available' }, [new El({}, [pill('harbor-dst', 'Available', 'full')])]);
  const crumb = new El({ 'data-opp-crumb': 'harbor-dst' }, [], 'Available Investments');
  const cardA = new El({ class: 'card', 'data-opp-slug': 'a-dst', 'data-opp-status': 'Available', 'data-opp-muted-class': 'card--sold' }, [pill('a-dst', 'Available', 'short')]);
  const cardB = new El({ class: 'card', 'data-opp-slug': 'b-dst', 'data-opp-status': 'Available', 'data-opp-muted-class': 'card--sold' }, [pill('b-dst', 'Available', 'short')]);
  const cardC = new El({ class: 'card card--sold', 'data-opp-slug': 'c-dst', 'data-opp-status': 'Closed', 'data-opp-muted-class': 'card--sold' }, [pill('c-dst', 'Closed', 'short')]);
  const doc = docOf(crumb, offer, cardA, cardB, cardC);

  const bySlug = live.reduce(feed([
    { slug: 'harbor-dst', status: 'Closed', remainingPct: 0, availableForInvestment: false },
    { slug: 'a-dst', status: 'Limited Availability', remainingPct: 12, availableForInvestment: true },
    { slug: 'c-dst', status: 'Available', remainingPct: 80, availableForInvestment: true },
  ]));
  assert.equal(live.apply(bySlug, doc), 4);

  const p = offer.children[0].children[0];
  assert.deepEqual([offer.getAttribute('data-opp-status'), p.textContent, p.className, crumb.textContent], ['Closed', 'Closed — no longer available', 'status status--sold', 'Investments']);
  assert.equal(offer.getAttribute('data-opp-remaining'), '0');
  assert.deepEqual([cardA.getAttribute('data-opp-status'), cardA.children[0].textContent, cardA.children[0].className, has(cardA, 'card--sold'), has(cardA, 'is-opp-limited')],
    ['Limited Availability', 'Limited', 'status status--limited', false, true]);
  assert.deepEqual([cardB.getAttribute('data-opp-status'), cardB.children[0].textContent, cardB.children[0].getAttribute('title'), has(cardB, 'card--sold')],
    ['No longer available', 'Unavailable', 'No longer available', true], 'missing from the feed: the unavailable treatment');
  assert.deepEqual([cardC.getAttribute('data-opp-status'), cardC.children[0].textContent, cardC.children[0].className, has(cardC, 'card--sold')],
    ['Available', 'Available', 'status', false], 'a reopened deal is un-dimmed');
  assert.equal(live.apply(bySlug, doc), 0, 'idempotent');
});

test('one request, cached 60 s in sessionStorage; failures and empty feeds leave the page as built', async () => {
  const storage = memStorage(), f = fetchStub(feed([{ slug: 'a-dst', status: 'Closed' }]));
  let t = 1_000_000;
  const env = { storage, fetch: f, now: () => t };
  assert.deepEqual(await live.load(env), { 'a-dst': { status: 'Closed', remainingPct: null, available: true } });
  assert.equal(f.calls.length, 1); assert.equal(f.calls[0].url, 'https://opportunities.baker1031.com/api/public/opportunities'); assert.equal(f.calls[0].init.credentials, 'omit');
  t += 59_000; await live.load(env); assert.equal(f.calls.length, 1, 'served from the cache');
  t += 2_000; await live.load(env); assert.equal(f.calls.length, 2, 'refetched after 60 s');

  assert.equal(await live.load({ storage: memStorage(), fetch: fetchStub(null, { fail: true }) }), null);
  assert.equal(await live.load({ storage: memStorage(), fetch: fetchStub({}, { ok: false }) }), null);
  assert.equal(await live.load({ storage: memStorage(), fetch: fetchStub(feed([])) }), null, 'an empty feed is treated as an outage, not as everything gone');
  const broken = { getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('SecurityError'); } };
  assert.ok(await live.load({ storage: broken, fetch: fetchStub(feed([{ slug: 'a-dst', status: 'Available' }])) }), 'storage that throws is ignored');

  const card = new El({ class: 'card', 'data-opp-slug': 'a-dst', 'data-opp-status': 'Available', 'data-opp-muted-class': 'card--sold' }, [new El({ class: 'status', 'data-opp-label': 'short' }, [], 'Available')]);
  const doc = docOf(card);
  assert.equal(await live.run({ document: doc, storage: memStorage(), fetch: fetchStub(null, { fail: true }) }), null);
  assert.deepEqual([card.getAttribute('data-opp-status'), card.children[0].textContent, card.className], ['Available', 'Available', 'card'], 'feed down: untouched');

  function CustomEvent(type, init) { this.type = type; this.detail = init.detail; }
  assert.equal(await live.run({ document: doc, storage: memStorage(), fetch: fetchStub(feed([{ slug: 'a-dst', status: 'Closed' }])), CustomEvent }), 1);
  assert.equal(doc.events[0].type, 'b1031:live-status'); assert.equal(doc.events[0].detail.bySlug['a-dst'].status, 'Closed');
  assert.ok(has(card, 'card--sold'));

  const f2 = fetchStub(feed([{ slug: 'x', status: 'Closed' }]));
  assert.equal(await live.run({ document: docOf(), storage: memStorage(), fetch: f2 }), null); assert.equal(f2.calls.length, 0, 'no marked offering, no request');
});

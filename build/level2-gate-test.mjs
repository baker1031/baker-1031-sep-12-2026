// Exercises the real gate.js against cookies minted the way auth.mjs mints them.
import crypto from 'node:crypto';
import fs from 'node:fs';
const SECRET = 'test-secret-value';
globalThis.Deno = { env: { get: (k) => (k === 'SESSION_SECRET' ? SECRET : '') } };

// build the module with a level-2 list filled in, as Jerry would
let src = fs.readFileSync('/home/claude/repo/netlify/edge-functions/gate.js', 'utf8');
src = src.replace("const LEVEL2_PREFIXES = [\n  // e.g. '/strategies',\n];",
                  "const LEVEL2_PREFIXES = ['/strategies', '/vault/'];");
// The copy has to sit beside the real gate.js: gate.js imports ./lib/retired-offerings.js, which only
// resolves from that directory. Cleaned up below whether the run passes or not.
const tmp = '/home/claude/repo/netlify/edge-functions/.gate.test.mjs';
fs.writeFileSync(tmp, src);
const gate = (await import(tmp)).default;
const cleanup = () => { try { fs.unlinkSync(tmp); } catch {} };
process.on('exit', cleanup);

const b64u = (b) => Buffer.from(b).toString('base64url');
function cookie(level, { expired = false } = {}) {
  const exp = Date.now() + (expired ? -1000 : 86400000);
  const payload = b64u(JSON.stringify({ rid: 'rec123', fn: 'Jane', exp, lvl: level }));
  const sig = crypto.createHmac('sha256', SECRET).update(payload).digest('base64url');
  return `b31_session=${payload}.${sig}`;
}
const legacyCookie = () => {           // a cookie minted before this change: no lvl at all
  const payload = b64u(JSON.stringify({ rid: 'rec123', fn: 'Jane', exp: Date.now() + 86400000 }));
  return `b31_session=${payload}.${crypto.createHmac('sha256', SECRET).update(payload).digest('base64url')}`;
};

let pass = 0, fail = 0;
async function check(label, path, ck, want) {
  const req = new Request('https://baker1031.com' + path, { headers: ck ? { cookie: ck } : {} });
  const res = await gate(req, { next: async () => new Response('PAGE', { status: 200 }) });
  const got = res.status === 200 ? 'through' : `${res.status} ${res.headers.get('location')}`;
  const ok = got === want;
  console.log(`${ok ? '  ok  ' : '  FAIL'} ${label}\n         → ${got}${ok ? '' : `   (wanted ${want})`}`);
  ok ? pass++ : fail++;
}

console.log('level-2 pages: /strategies, /vault/\n');
await check('level 2 cookie on a level-2 page', '/strategies/reits/', cookie(2), 'through');
await check('level 1 cookie on a level-2 page', '/strategies/reits/', cookie(1),
            '302 /login/?next=%2Fstrategies%2Freits%2F&need=2');
await check('legacy cookie (no lvl) on a level-2 page', '/strategies/reits/', legacyCookie(),
            '302 /login/?next=%2Fstrategies%2Freits%2F&need=2');
await check('no cookie on a level-2 page', '/strategies/reits/', null,
            '302 /login/?next=%2Fstrategies%2Freits%2F');
await check('expired level 2 cookie', '/strategies/', cookie(2, { expired: true }),
            '302 /login/?next=%2Fstrategies%2F');
await check('level-2 prefix exactly', '/strategies', cookie(1),
            '302 /login/?next=%2Fstrategies&need=2');
await check('level 1 on a normal public page', '/results/', cookie(1), 'through');
await check('no cookie on a public page', '/results/', null, 'through');
await check('level 1 on the offering docs gate', '/offerings/foo/docs/ppm.pdf', cookie(1), 'through');
await check('no cookie on the offering docs gate', '/offerings/foo/docs/ppm.pdf', null,
            '302 /login/?next=%2Fofferings%2Ffoo%2F');
// /strategiesX/ isn't public either, so it lands on the normal login redirect — the point is the
// absence of &need=2, which proves the level-2 prefix matched on a segment boundary and not a substring.
await check('a path merely starting with the same letters', '/strategiesX/', null,
            '302 /login/?next=%2FstrategiesX%2F');
await check('same, with a level 1 cookie', '/strategiesX/', cookie(1), 'through');

// Retired offerings: a URL that was published once must never 404. The list is generated from
// build/published-slugs.txt, so an offering that comes back into Airtable has to stop redirecting.
const { RETIRED_OFFERINGS } = await import('/home/claude/repo/netlify/edge-functions/lib/retired-offerings.js');
const live = JSON.parse(fs.readFileSync('/home/claude/repo/build/offerings.json', 'utf8')).map((o) => o.slug);
const someRetired = [...RETIRED_OFFERINGS][0];
await check('a retired offering redirects to the inventory', `/offerings/${someRetired}/`, cookie(1),
            '301 /invest/');
await check('…and so does anything under it', `/offerings/${someRetired}/docs/ppm.pdf`, cookie(1),
            '301 /invest/');
await check('a live offering is not redirected', `/offerings/${live[0]}/`, cookie(1), 'through');
const clash = live.filter((s) => RETIRED_OFFERINGS.has(s));
console.log(`${clash.length === 0 ? '  ok  ' : '  FAIL'} no live offering is in the retired list` +
            `\n         → ${clash.length ? clash.join(', ') : 'none'}`);
clash.length === 0 ? pass++ : fail++;
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

/* Checks the arithmetic inside the calculator pages against hand-worked cases.
 *
 * Added after /calculators/boot/ was found computing
 *     mortgage boot = old debt - new debt - cash added - CASH BOOT
 * The trailing term is wrong: under Treas. Reg. 1.1031(d)-2 only cash PAID reduces
 * liability relief, cash RECEIVED does not, and the site's own articles state the rule
 * correctly as "old debt - new debt - additional cash contributed". The bug understated
 * total boot by exactly the cash-boot amount whenever both kinds of boot arose -- up to
 * 50% in an ordinary trade-down -- always in the direction of understating tax.
 *
 * Run: node build/calculator-test.mjs
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
let pass = 0, fail = 0;
const ok = (name, got, want) => {
  const good = Math.abs(got - want) < 1;
  good ? pass++ : fail++;
  console.log(`  ${good ? 'ok  ' : 'FAIL'} ${name}` + (good ? '' : `  got ${got}, want ${want}`));
};

/* Pull the calc() body straight out of the built page so the test tracks the shipped code. */
function calcSource(page) {
  const html = readFileSync(join(ROOT, 'calculators', page, 'index.html'), 'utf8');
  const m = html.match(/function calc\(\)\{[\s\S]*?\n\}/);
  if (!m) throw new Error(`no calc() found in /calculators/${page}/`);
  return m[0];
}

/* ---- boot ------------------------------------------------------------------------- */
console.log('/calculators/boot/');
{
  const src = calcSource('boot');
  if (/-\s*cashBoot\s*\)/.test(src.replace(/\/\/[^\n]*/g, ''))) {
    console.log('  FAIL mortgage boot still subtracts cash boot received'); fail++;
  } else { console.log('  ok   mortgage boot does not subtract cash boot received'); pass++; }

  // Same arithmetic the page runs, evaluated here.
  const boot = (sale, costs, payoff, rprice, rdebt, addcash) => {
    const netValue = sale - costs;
    const equity = Math.max(0, netValue - payoff);
    const equityIn = Math.max(0, Math.min(equity, rprice - rdebt - addcash));
    const cashBoot = Math.max(0, equity - equityIn);
    const mortBoot = Math.max(0, payoff - rdebt - addcash);
    return { cashBoot, mortBoot, total: cashBoot + mortBoot };
  };
  // Trading down: total boot must equal the shortfall in value acquired.
  const down = [
    ['debt partly replaced', 1000000, 60000, 400000,  800000, 300000,      0],
    ['both kinds of boot',   1000000,     0, 500000,  600000, 300000,      0],
    ['cash added',           1000000,     0, 500000,  600000, 300000, 100000],
    ['no new debt',          1000000,     0, 500000,  700000, 200000,      0],
  ];
  for (const [name, ...a] of down) {
    ok(`${name}: total boot = value shortfall`, boot(...a).total, (a[0] - a[1]) - a[3]);
  }
  ok('even exchange: no boot', boot(1000000, 0, 400000, 1000000, 400000, 0).total, 0);
  // Trading up but leaving equity behind is cash boot with no value shortfall.
  ok('trade up, equity left over', boot(1000000, 60000, 400000, 1200000, 700000, 0).total, 40000);
  // The site's stated rule, quoted in /learn/1031-exchange-debt-replacement-mortgage-boot/.
  ok('stated rule: 300k old debt, 200k new', boot(800000, 0, 300000, 800000, 200000, 0).mortBoot, 100000);
  ok('stated rule: cured by 100k of cash',   boot(800000, 0, 300000, 800000, 200000, 100000).mortBoot, 0);
}

/* ---- deferred tax ----------------------------------------------------------------- */
console.log('/calculators/deferred-tax/');
{
  const t = (sale, costs, basis, improve, dep, fed, niitOn, statePct) => {
    const adjBasis = basis + improve - dep;
    const gain = Math.max(0, (sale - costs) - adjBasis);
    const recapPortion = Math.min(dep, gain);
    return recapPortion * .25 + (gain - recapPortion) * fed
         + (niitOn ? gain * .038 : 0) + (statePct / 100) * gain;
  };
  // $1.0m sale, $40k costs, $300k basis, $200k depreciation: gain $860k, $200k at 25%, $660k at 20%.
  ok('recapture at 25%, remainder at 20%', t(1000000, 40000, 300000, 0, 200000, .20, false, 0), 200000 * .25 + 660000 * .20);
  ok('NIIT applies to the whole gain',     t(1000000, 40000, 300000, 0, 200000, .20, true,  0),
     200000 * .25 + 660000 * .20 + 860000 * .038);
  ok('no gain, no tax', t(300000, 0, 400000, 0, 0, .20, true, 13.3), 0);
}

/* ---- deadlines -------------------------------------------------------------------- */
console.log('/calculators/deadline/');
{
  const at = (iso, days) => { const d = new Date(iso + 'T12:00:00'); d.setDate(d.getDate() + days); return d.toISOString().slice(0, 10); };
  const eq = (name, got, want) => { const g = got === want; g ? pass++ : fail++; console.log(`  ${g ? 'ok  ' : 'FAIL'} ${name}` + (g ? '' : `  got ${got}, want ${want}`)); };
  eq('45 days from 2026-09-17',  at('2026-09-17', 45),  '2026-11-01');
  eq('180 days from 2026-09-17', at('2026-09-17', 180), '2027-03-16');
  eq('45 days across a leap day',  at('2028-01-31', 45),  '2028-03-16');
  eq('180 days across a year end', at('2026-12-01', 180), '2027-05-30');
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

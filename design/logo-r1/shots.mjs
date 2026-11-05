// Contact sheet and close-ups of logos.html, plus console and request errors.
//   node design/logo-r1/shots.mjs [outdir]     (needs the server on 8083)
import { createRequire } from 'node:module';
const require = createRequire(new URL('../../tools/package.json', import.meta.url));
const { chromium } = require('playwright-core');

const out = process.argv[2] || '/opt/data/cache/scratch/elliott_logo_r1/shots';
const CHROME = process.env.CHROME || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome';
const browser = await chromium.launch({ executablePath: CHROME });
const open = async (w, dpr) => {
  const page = await (await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: dpr })).newPage();
  const bad = [];
  page.on('console', (m) => { if (m.type() === 'error') bad.push(m.text()); });
  page.on('pageerror', (e) => bad.push(String(e)));
  page.on('response', (r) => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
  await page.goto('http://127.0.0.1:8083/logos.html', { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  return { page, bad };
};
const a = await open(1440, 1);
await a.page.screenshot({ path: `${out}/sheet.png`, fullPage: true });
const b = await open(1440, 2);
await b.page.locator('#top3').screenshot({ path: `${out}/header_top3.png` });
for (const id of ['five-strokes', 'bracket-impulse', 'one-line', 'broom-candle', 'fib-lattice', 'side-eye', 'broom-five', 'loaded-die', 'baseline']) {
  await a.page.locator(`[id="${id}"]`).screenshot({ path: `${out}/concept_${id}.png` });
}
const c = await open(390, 2);
const overflow = await c.page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
console.log(JSON.stringify({ errors: [...a.bad, ...b.bad, ...c.bad], phoneOverflow: overflow }));
await browser.close();

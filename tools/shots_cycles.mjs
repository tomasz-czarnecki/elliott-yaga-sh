// Headless check of the cycles overlay: screenshots of each view, console errors, failed requests, and the public-site
// behaviour (no toggle, no request for the private file). Needs the preview server running.
//   node tools/shots_cycles.mjs [--base http://127.0.0.1:8082] [--out DIR] [--baseline http://127.0.0.1:8083]
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf('--' + name); return i < 0 ? def : args[i + 1]; };
const base = opt('base', 'http://127.0.0.1:8082');
const baseline = opt('baseline', '');
const out = path.resolve(opt('out', '/opt/data/cache/scratch/elliott_cycles_r1/shots'));
const CHROME = process.env.CHROME || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome';
fs.mkdirSync(out, { recursive: true });

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const launch = (extra = []) => chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', ...extra] });
const report = [];
let ok = true;

async function visit(browser, name, url, viewport, fn, { root = base, allow = [] } = {}) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: viewport === PHONE ? 2 : 1 });
  const page = await ctx.newPage();
  const errors = [], bad = [], requested = [];
  page.on('console', (m) => { if ((m.type() === 'error' || m.type() === 'warning') && !allow.some((a) => m.text().includes(a))) errors.push(`${m.type()}: ${m.text()}`); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e));
  page.on('request', (r) => requested.push(r.url()));
  page.on('response', (r) => { if (r.status() >= 400 && !allow.some((a) => r.url().includes(a))) bad.push(`${r.status()} ${r.url()}`); });
  page.on('requestfailed', (r) => bad.push(`failed ${r.url()} ${r.failure()?.errorText}`));
  await page.goto(root + url, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready', null, { timeout: 60000 });
  await page.waitForTimeout(700);
  await fn(page, requested);
  const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  if (o.sw > o.cw) errors.push(`overflows: ${o.sw} > ${o.cw}`);
  report.push({ name, errors, bad });
  if (errors.length || bad.length) ok = false;
  await ctx.close();
}

const shot = (page, name) => page.screenshot({ path: path.join(out, `${name}.png`) });
const zoom = (page, from, to) => page.evaluate(([a, b]) => {
  chart.timeScale().setVisibleLogicalRange({ from: a === null ? 0 : bars.time.findIndex((t) => t >= Date.parse(a) / 1000), to: bars.n - 1 + (Date.parse(b) / 1000 - bars.time[bars.n - 1]) / 86400 });
}, [from, to]);
const settle = (page) => page.waitForTimeout(500);

const browser = await launch();
const ON = 'cycles=1';

await visit(browser, 'bitstamp 1d log, full history', `/chart.html?venue=bitstamp&tf=1d&scale=log&${ON}`, DESKTOP, async (page) => {
  await shot(page, 'cycles_bitstamp_1d_log_full');
});
await visit(browser, 'bitstamp 1d log, last 3 years', `/chart.html?venue=bitstamp&tf=1d&scale=log&${ON}`, DESKTOP, async (page) => {
  await zoom(page, '2023-10-30', '2027-05-10');
  await settle(page);
  await shot(page, 'cycles_bitstamp_1d_log_3y');
  await zoom(page, '2025-10-01', '2027-01-10');
  await settle(page);
  await shot(page, 'cycles_bitstamp_1d_log_1y');
  // The crosshair on a hindsight low explains it
  const x = await page.evaluate(() => chart.timeScale().timeToCoordinate(Date.parse('2026-02-06') / 1000));
  const box = await page.locator('#chart').boundingBox();
  await page.mouse.move(box.x + x, box.y + 200);
  await page.waitForTimeout(300);
  const info = await page.textContent('#cycles-info');
  report.push({ name: 'hover', info, errors: [], bad: [] });
  if (!/Weekly low.*2026-02-06/.test(info)) ok = false;
  await shot(page, 'cycles_hover');
});
await visit(browser, 'weekly level', `/chart.html?venue=bitstamp&tf=1d&scale=log&${ON}&clv=w&cly=h,z`, DESKTOP, async (page) => {
  await shot(page, 'cycles_weekly_level');
});
await visit(browser, 'hindsight vs live, weekly and 4y', `/chart.html?venue=bitstamp&tf=1d&scale=log&${ON}&clv=4y,w&cly=h,l`, DESKTOP, async (page) => {
  await zoom(page, '2018-01-01', '2027-05-10');
  await settle(page);
  await shot(page, 'cycles_weekly_live_2018');
});
await visit(browser, 'bybit 1d', `/chart.html?venue=bybit&tf=1d&scale=log&${ON}`, DESKTOP, async (page) => {
  await shot(page, 'cycles_bybit_1d');
  await zoom(page, '2024-10-01', '2027-05-10');
  await settle(page);
  await shot(page, 'cycles_bybit_1d_zoom');
});
await visit(browser, 'bybit 4h', `/chart.html?venue=bybit&tf=4h&${ON}`, DESKTOP, async (page) => { await shot(page, 'cycles_bybit_4h'); });
await visit(browser, 'bybit 15m', `/chart.html?venue=bybit&tf=15m&${ON}`, DESKTOP, async (page) => { await shot(page, 'cycles_bybit_15m'); });
await visit(browser, 'phone', `/chart.html?venue=bitstamp&tf=1d&scale=log&${ON}`, PHONE, async (page) => {
  await shot(page, 'cycles_phone_full');
  await zoom(page, '2026-01-01', '2027-01-10');
  await settle(page);
  await shot(page, 'cycles_phone_zoom');
});
await visit(browser, 'off, toggle present', '/chart.html?venue=bitstamp&tf=1d&scale=log', DESKTOP, async (page) => {
  await shot(page, 'cycles_off');
  const shown = await page.$eval('#seg-cycles', (e) => !e.hidden);
  const barHidden = await page.$eval('#cycles-bar', (e) => e.hidden);
  report.push({ name: 'toggle shown, bar hidden', shown, barHidden, errors: [], bad: [] });
  if (!shown || !barHidden) ok = false;
  await page.click('#seg-cycles button');
  await settle(page);
  const url = new URL(page.url());
  report.push({ name: 'toggle on', url: url.search, errors: [], bad: [] });
  if (url.searchParams.get('cycles') !== '1') ok = false;
  await shot(page, 'cycles_toggled_on');
  await page.click('#seg-tf button[data-value="1h"]');
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready');
  await settle(page);
  if (new URL(page.url()).searchParams.get('cycles') !== '1') ok = false;
  await page.click('#seg-cycles button');
  await settle(page);
  if (new URL(page.url()).searchParams.has('cycles')) ok = false;
});
await browser.close();

// The public host: same files, served as elliott.yaga.sh. No toggle, and the private file is never asked for.
const port = new URL(base).port;
const pub = await launch([`--host-resolver-rules=MAP elliott.yaga.sh 127.0.0.1:${port}`]);
const shotsToCompare = {};
for (const [tag, vp] of [['desktop', DESKTOP], ['phone', PHONE]]) {
  await visit(pub, `public host ${tag}`, '/chart.html?venue=bitstamp&tf=1d&scale=log', vp, async (page, requested) => {
    await page.screenshot({ path: path.join(out, `public_${tag}.png`) });
    shotsToCompare[tag] = fs.readFileSync(path.join(out, `public_${tag}.png`));
    const asked = requested.filter((u) => u.includes('/data/local'));
    const toggle = await page.$eval('#seg-cycles', (e) => !e.hidden);
    report.push({ name: `public ${tag}`, asked, toggle, errors: [], bad: [] });
    if (asked.length || toggle) ok = false;
  }, { root: 'http://elliott.yaga.sh' });
}
await pub.close();

// A preview server without the private file: no toggle. The browser's own 404 line is the one thing a page cannot prevent.
const noData = await launch();
{
  const ctx = await noData.newContext({ viewport: DESKTOP });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + e));
  page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('404')) errors.push(m.text()); });
  await page.route(/\/data\/local\//, (r) => r.fulfill({ status: 404, body: '' }));
  await page.goto(base + '/chart.html?venue=bitstamp&tf=1d&scale=log&cycles=1', { waitUntil: 'load' });
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready', null, { timeout: 60000 });
  await page.waitForTimeout(500);
  const toggle = await page.$eval('#seg-cycles', (e) => !e.hidden);
  report.push({ name: 'no private file', toggle, errors, url: new URL(page.url()).search, bad: [] });
  if (toggle || errors.length) ok = false;
  await ctx.close();
}
await noData.close();

// The public page against the page as it is in git: pixel for pixel.
if (baseline) {
  const b = await launch();
  for (const [tag, vp] of [['desktop', DESKTOP], ['phone', PHONE]]) {
    await visit(b, `baseline ${tag}`, '/chart.html?venue=bitstamp&tf=1d&scale=log', vp, async (page) => {
      const file = path.join(out, `baseline_${tag}.png`);
      await page.screenshot({ path: file });
      const hash = (x) => crypto.createHash('sha256').update(x).digest('hex').slice(0, 16);
      const same = hash(fs.readFileSync(file)) === hash(shotsToCompare[tag]);
      report.push({ name: `public ${tag} equals git HEAD`, same, errors: [], bad: [] });
      if (!same) ok = false;
    }, { root: baseline });
  }
  await b.close();
}

console.log(JSON.stringify(report.filter((r) => Object.keys(r).length > 3 || r.errors.length || r.bad.length), null, 1));
console.log(`${report.length} checks`);
console.log(ok ? 'ALL OK' : 'PROBLEMS FOUND');
process.exit(ok ? 0 : 1);

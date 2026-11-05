// Headless check of round 6: projected paths and boxes, next leg, magnets, clarity with its hover, and that choosing a count moves
// nothing. Screenshots, console errors, failed requests. Needs the preview server running.
//   node tools/shots_counts_r6.mjs [--base http://127.0.0.1:8082] [--out DIR]
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf('--' + name); return i < 0 ? def : args[i + 1]; };
const base = opt('base', 'http://127.0.0.1:8082');
const out = path.resolve(opt('out', '/opt/data/cache/scratch/elliott_counts_r6/shots'));
const CHROME = process.env.CHROME || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome';
fs.mkdirSync(out, { recursive: true });
const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const problems = [];
const fail = (name, why) => problems.push({ name, why });

async function open(url, viewport = DESKTOP) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: viewport === PHONE ? 2 : 1, hasTouch: viewport === PHONE });
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') fail(url, `${m.type()}: ${m.text()}`); });
  page.on('pageerror', (e) => fail(url, `pageerror: ${e}`));
  page.on('response', (r) => { if (r.status() >= 400) fail(url, `${r.status()} ${r.url()}`); });
  await page.goto(base + url, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready', null, { timeout: 60000 });
  await page.waitForTimeout(1000);
  return page;
}
const shot = (page, name) => page.screenshot({ path: path.join(out, `${name}.png`) });
const fit = async (page, v) => { await page.click(`#seg-count-view button[data-value="${v}"]`); await page.waitForTimeout(600); };
const range = (page) => page.evaluate(() => { const r = chart.timeScale().getVisibleLogicalRange(); return `${r.from.toFixed(2)}..${r.to.toFixed(2)}`; });
const prices = (page) => page.evaluate(() => { const r = candles.priceScale().getVisibleRange(); return r ? `${r.from.toFixed(0)}..${r.to.toFixed(0)}` : 'n/a'; });

const data = JSON.parse(fs.readFileSync(new URL('../site/data/local/counts.json', import.meta.url)));
const levels = data.trees['1d'].levels;
const root = levels[0].nodes[0];
const first = (tf) => levels.find((l) => l.tf === tf).nodes[0].id;
for (const lv of levels) for (const n of lv.nodes) {
  const after = n.projection.legs.filter((l) => l.role === 'after');
  if (after.length > 1) fail('one step after', n.id);
  if (n.odds.findIndex((o) => o.name === 'leg') > 0) fail('the move after leads', n.id);
}

// 1D and 4H with 1d.1's Y path and boxes
let page = await open(`/chart.html?venue=bybit&tf=1d&counts=1&cn=${root.id}`);
await shot(page, 'r6_1d_default');
await fit(page, 'path');
await shot(page, 'r6_1d_path');
const main = root.projection.legs[0];
const yOf = await page.evaluate((p) => candles.priceToCoordinate(p), main.p);
if (yOf == null || yOf < 0) fail('1D fit path', 'the running wave point is not on the chart');
page = await open(`/chart.html?venue=bybit&tf=4h&counts=1`);
await page.click(`.cp-row[data-id="${root.id}"] .cp-name`);
await page.waitForTimeout(300);
await fit(page, 'path');
await shot(page, 'r6_4h_root_path');
page = await open(`/chart.html?venue=bybit&tf=4h&counts=1&cn=${first('4h')}`);
await fit(page, 'path');
await shot(page, 'r6_4h_child_path');

// a 1H and a 15m next leg with magnet tags
page = await open(`/chart.html?venue=bybit&tf=1h&counts=1&cn=${first('1h')}`);
await fit(page, 'path');
await shot(page, 'r6_1h_next_leg');
page = await open(`/chart.html?venue=bybit&tf=15m&counts=1&cn=${first('15m')}`);
await fit(page, 'path');
await shot(page, 'r6_15m_next_leg');

// the panel: magnets and next leg
await page.click('.cp-i[data-pop="magnets"]');
await page.waitForTimeout(300);
await shot(page, 'r6_magnets_popover');
const mag = await page.$eval('.cp-pop', (e) => e.textContent);
if (!/weight/.test(mag)) fail('magnets popover', mag.slice(0, 80));
await page.keyboard.press('Escape');
await page.click('.cp-i[data-pop="next"]');
await page.waitForTimeout(300);
const nxt = await page.$eval('.cp-pop', (e) => e.textContent);
if (!/before/.test(nxt)) fail('next leg popover', nxt.slice(0, 80));
await page.keyboard.press('Escape');

// the hover inside of X
page = await open(`/chart.html?venue=bybit&tf=4h&counts=1`);
await page.click(`.cp-row[data-id="${root.id}"] .cp-name`);
// the popover sits over the right of the chart: X, February to September, goes in the free left part
await page.evaluate((n) => {
  const bar = (t) => { let a = 0; let b = bars.n - 1; while (a < b) { const m = (a + b + 1) >> 1; if (bars.time[m] <= t) a = m; else b = m - 1; } return a; };
  const a = bar(n.labels[1].t);
  const span = bar(n.labels[2].t) - a;
  chart.timeScale().setVisibleLogicalRange({ from: a - span * 0.04, to: a + span * 1.75 });
}, root);
await page.waitForTimeout(400);
await page.click(`.cp-i[data-pop="${root.id}"]`);
await page.waitForTimeout(300);
const pop = await page.$eval('.cp-pop', (e) => e.textContent);
for (const want of ['Clarity', 'Path', 'Cycles', 'Next leg']) if (!pop.includes(want)) fail('count popover', want);
if (/\u2014/.test(pop)) fail('count popover', 'em dash');
await shot(page, 'r6_popover_clarity');
const before = await page.screenshot({ clip: { x: 0, y: 170, width: 950, height: 520 } });
await page.hover('.cp-cl[data-wave="X"]');
await page.waitForTimeout(300);
if ((await page.evaluate(() => EWCounts.drawn().hover?.wave)) !== 'X') fail('hover', 'not set');
await shot(page, 'r6_hover_x_inside');
const during = await page.screenshot({ clip: { x: 0, y: 170, width: 950, height: 520 } });
if (Buffer.compare(before, during) === 0) fail('hover', 'the chart did not change');
await page.mouse.move(20, 880);
await page.waitForTimeout(300);
if (await page.evaluate(() => EWCounts.drawn().hover)) fail('hover', 'stayed after leaving');
await page.keyboard.press('Escape');

// choosing a count moves nothing: neither time nor price
page = await open('/chart.html?venue=bybit&tf=4h&counts=1');
await page.mouse.move(500, 400);
await page.mouse.wheel(0, -200);
await page.waitForTimeout(400);
const ids = await page.$$eval('.cp-row', (rs) => rs.map((r) => r.dataset.id));
const t0 = await range(page);
const p0 = await prices(page);
for (const id of ids) {
  await page.click(`.cp-row[data-id="${id}"] .cp-name`);
  await page.waitForTimeout(250);
  if (await range(page) !== t0) fail('choosing moved time', id);
  if (await prices(page) !== p0) fail('choosing moved price', `${id}: ${await prices(page)} against ${p0}`);
}
await fit(page, 'path');
if (await range(page) === t0) fail('fit path', 'did nothing');
await page.click('#seg-count-view button[data-value="focus"]');
await page.waitForTimeout(400);
if ((await page.evaluate(() => EWCounts.drawn().fitPrice))) fail('fit count', 'kept the price range');

// phone
page = await open(`/chart.html?venue=bybit&tf=1d&counts=1&cn=${root.id}`, PHONE);
await fit(page, 'path');
await shot(page, 'r6_phone_1d');
page = await open(`/chart.html?venue=bybit&tf=4h&counts=1&cn=${first('4h')}`, PHONE);
await shot(page, 'r6_phone_4h');
await page.tap(`.cp-i[data-pop="${first('4h')}"]`);
await page.waitForTimeout(300);
await shot(page, 'r6_phone_popover');
const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
if (o.sw > o.cw) fail('phone', `overflows: ${o.sw} > ${o.cw}`);

await browser.close();
console.log(problems.length ? JSON.stringify(problems, null, 1) : 'all checks pass');
process.exit(problems.length ? 1 : 0);

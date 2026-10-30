// Headless check of site/: screenshots, console errors, failed requests, and the chart's bars against the export.
//   python3 -m http.server 8082 --bind 127.0.0.1 --directory site &      (then, with the server running)
//   node tools/shots_site.mjs [--base http://127.0.0.1:8082] [--out /opt/data/cache/scratch/elliott_site_r1/shots]
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf('--' + name); return i < 0 ? def : args[i + 1]; };
const base = opt('base', 'http://127.0.0.1:8082');
const out = path.resolve(opt('out', '/opt/data/cache/scratch/elliott_site_r1/shots'));
const CHROME = process.env.CHROME || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome';
fs.mkdirSync(out, { recursive: true });

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const scaleFor = (vp) => (vp === PHONE ? 2 : 1); // phones have dense screens
const browser = await chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const report = [];
let ok = true;

async function visit(name, url, viewport, fn) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: scaleFor(viewport) });
  const page = await ctx.newPage();
  const errors = [], bad = [];
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(`${m.type()}: ${m.text()}`); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e));
  page.on('response', (r) => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
  page.on('requestfailed', (r) => bad.push(`failed ${r.url()} ${r.failure()?.errorText}`));
  const resp = await page.goto(base + url, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await fn(page);
  report.push({ name, url, status: resp.status(), errors, bad });
  if (resp.status() !== 200 || errors.length || bad.length) ok = false;
  await ctx.close();
}

const chartReady = async (page) => {
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready', null, { timeout: 60000 });
  await page.waitForTimeout(500);
};
const noOverflow = async (page, name) => {
  const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  if (o.sw > o.cw) { ok = false; report.push({ name: `${name} overflows`, ...o }); }
};

// Landing
for (const [tag, vp] of [['desktop', DESKTOP], ['phone', PHONE]]) {
  await visit(`landing-${tag}`, '/index.html', vp, async (page) => {
    await page.waitForSelector('.history-plot svg');
    await page.screenshot({ path: path.join(out, `landing_${tag}_fold.png`) });
    // In chunks: one very tall capture repeats content in headless Chromium.
    const h = await page.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0, n = 1; y < h; y += 2400, n++) {
      await page.screenshot({ path: path.join(out, `landing_${tag}_full_${n}.png`), fullPage: true, clip: { x: 0, y, width: vp.width, height: Math.min(2400, h - y) } });
    }
    await noOverflow(page, `landing-${tag}`);
    const left = await page.evaluate(() => document.body.innerText.includes('...') );
    if (left) { ok = false; report.push({ name: `landing-${tag}: placeholder left in the page` }); }
    report.push({ name: `landing-${tag} numbers`, tiles: await page.$$eval('.tile-value', (e) => e.map((x) => x.textContent)), cards: await page.$$eval('[data-venue] dd', (e) => e.map((x) => x.textContent)) });
  });
}

// Chart: each timeframe on log and linear, on both widths
for (const [tag, vp] of [['desktop', DESKTOP], ['phone', PHONE]]) {
  for (const tf of ['1d', '4h', '1h', '15m']) {
    for (const scale of ['log', 'linear']) {
      await visit(`chart-${tag}-${tf}-${scale}`, `/chart.html?tf=${tf}&scale=${scale}`, vp, async (page) => {
        await chartReady(page);
        await page.screenshot({ path: path.join(out, `chart_${tag}_${tf}_${scale}.png`) });
        await noOverflow(page, `chart-${tag}-${tf}-${scale}`);
      });
    }
  }
}

// Chart: the other venues, defaults, and the controls
await visit('chart-default', '/chart.html', DESKTOP, async (page) => {
  await chartReady(page);
  const pressed = await page.$$eval('button[aria-pressed="true"]', (b) => b.map((x) => x.textContent));
  report.push({ name: 'chart default controls', pressed });
  if (pressed.join() !== 'Bybit perp,1D,Log') ok = false;
  await page.click('#seg-tf button[data-value="4h"]');
  await chartReady(page);
  const after4h = await page.$$eval('#seg-scale button[aria-pressed="true"]', (b) => b.map((x) => x.textContent));
  report.push({ name: 'chart 4H default scale', after4h, url: page.url() });
  if (after4h.join() !== 'Linear') ok = false;
  await page.click('#seg-venue button[data-value="binance_btcusdt"]');
  await chartReady(page);
  await page.mouse.move(700, 500);
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(out, 'chart_desktop_binance_4h_crosshair.png') });
  report.push({ name: 'chart crosshair readout', readout: await page.textContent('#readout') });
  await page.click('#seg-venue button[data-value="bitstamp_btcusd"]');
  await page.click('#seg-tf button[data-value="1d"]');
  await chartReady(page);
  await page.screenshot({ path: path.join(out, 'chart_desktop_bitstamp_1d.png') });
  report.push({ name: 'attribution logo', present: await page.$eval('#tv-attr-logo', (e) => !!e).catch(() => false) });
});

// A Binance bar that spans an outage is marked in the readout
await visit('chart-short-bar', '/chart.html?venue=binance&tf=1d', DESKTOP, async (page) => {
  await chartReady(page);
  const text = await page.evaluate(() => { renderReadout(bars.short.keys().next().value); return document.querySelector('#readout .warn')?.textContent; });
  report.push({ name: 'short bar readout', text });
  if (!/^Only \d+ of 1440 minutes$/.test(text ?? '')) ok = false;
});

// Without generated data both pages say so instead of breaking (the 404s are expected, so outside visit())
for (const [url, sel] of [['/chart.html', '#chart-msg'], ['/index.html', '[data-total="rows"]']]) {
  const ctx = await browser.newContext({ viewport: DESKTOP });
  const page = await ctx.newPage();
  await page.route(/\/data\//, (r) => r.fulfill({ status: 404, body: '' }));
  await page.goto(base + url, { waitUntil: 'networkidle' });
  const text = await page.textContent(sel);
  report.push({ name: `no data: ${url}`, text });
  if (!/not generated|n\/a/.test(text)) ok = false;
  await ctx.close();
}

// Every venue and timeframe: what the page decodes equals the bars the export was made from (see tools/bars_truth.py)
const truthFile = opt('truth', '');
if (truthFile) {
  const truth = JSON.parse(fs.readFileSync(truthFile, 'utf8'));
  await visit('decoded-bars', '/index.html', DESKTOP, async (page) => {
    const rows = await page.evaluate(async (truth) => {
      const stats = await EW.loadStats();
      const res = [];
      for (const t of truth) {
        const b = await EW.loadBars(stats, t.venue, t.tf);
        const at = b.time.indexOf(t.ts / 1000);
        const got = at < 0 ? null : [b.open[at], b.high[at], b.low[at], b.close[at], b.volume[at]];
        res.push({ ...t, got });
      }
      return res;
    }, truth);
    const wrong = rows.filter((r) => !r.got || r.want.some((w, i) => Math.abs(w - r.got[i]) > (i === 4 ? 0.0005001 : 0.0050001)));
    report.push({ name: 'decoded bars vs parquet', compared: rows.length, wrong });
    if (wrong.length) ok = false;
  });
}

// Links
await visit('links', '/index.html', DESKTOP, async (page) => {
  await page.locator('a.btn-dark:has-text("Open the chart")').nth(1).click();
  await page.waitForLoadState('load');
  const landed = new URL(page.url()).pathname;
  await page.locator('a:has-text("About")').click();
  await page.waitForLoadState('load');
  const back = new URL(page.url()).pathname;
  report.push({ name: 'links', landed, back });
  if (landed !== '/chart.html' || back !== '/index.html') ok = false;
});

console.log(JSON.stringify(report.filter((r) => !r.status || r.errors.length || r.bad.length), null, 1));
console.log(`${report.filter((r) => r.status).length} pages opened`);
console.log(ok ? 'ALL OK' : 'PROBLEMS FOUND');
await browser.close();
process.exit(ok ? 0 : 1);

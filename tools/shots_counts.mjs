// Headless check of the counts panel: the list, its popovers and keyboard, the whole chain on every timeframe, phone width,
// the page without the private file, and the public host. Screenshots, console errors, failed requests.
// Needs the preview server running.
//   node tools/shots_counts.mjs [--base http://127.0.0.1:8082] [--out DIR] [--baseline http://127.0.0.1:8093]
// --baseline: a server of the site as committed; the public page must equal it pixel for pixel.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf('--' + name); return i < 0 ? def : args[i + 1]; };
const base = opt('base', 'http://127.0.0.1:8082');
const baseline = opt('baseline', '');
const out = path.resolve(opt('out', '/opt/data/cache/scratch/elliott_counts_r5/shots'));
const CHROME = process.env.CHROME || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome';
fs.mkdirSync(out, { recursive: true });

const DESKTOP = { width: 1440, height: 900 };
const PHONE = { width: 390, height: 844 };
const launch = (extra = []) => chromium.launch({ executablePath: CHROME, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', ...extra] });
const report = [];
let ok = true;
const fail = (name, why) => { ok = false; report.push({ name, why }); };

async function visit(browser, name, url, viewport, fn, { root = base, route = null, allow = [], touch = false } = {}) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: viewport === PHONE ? 2 : 1, hasTouch: touch });
  const page = await ctx.newPage();
  const errors = [], requested = [];
  page.on('console', (m) => { if ((m.type() === 'error' || m.type() === 'warning') && !allow.some((a) => m.text().includes(a))) errors.push(`${m.type()}: ${m.text()}`); });
  page.on('pageerror', (e) => errors.push('pageerror: ' + e));
  page.on('request', (r) => requested.push(r.url()));
  page.on('response', (r) => { if (r.status() >= 400 && !allow.some((a) => r.url().includes(a) || String(r.status()) === a)) errors.push(`${r.status()} ${r.url()}`); });
  if (route) await page.route(route, (r) => r.fulfill({ status: 404, body: '' }));
  await page.goto(root + url, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready', null, { timeout: 60000 });
  await page.waitForTimeout(900);
  await fn(page, requested);
  const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  if (o.sw > o.cw) errors.push(`overflows: ${o.sw} > ${o.cw}`);
  if (errors.length) fail(name, errors);
  report.push({ name, done: true });
  await ctx.close();
}
const shot = (page, name) => page.screenshot({ path: path.join(out, `${name}.png`) });

const data = JSON.parse(fs.readFileSync(new URL('../site/data/local/counts.json', import.meta.url)));
const levels = data.trees['1d'].levels;
const first = (i) => levels[i].nodes[0].id;

/** The first 4H node whose count, or whose inside, holds the 5 that ends at his 5. */
const fives = (rows) => rows.flatMap((r) => (/impulse/.test(r.pattern) && r.labels.length === 6 ? [r] : []).concat(fives(r.inside)));
const shows = (n) => (/impulse/.test(n.pattern) && n.labels.length === 6 ? [n] : []).concat(fives(n.inside)).some((c) => Math.abs(c.labels[c.labels.length - 1].p - 87383.6) < 1);
const his = levels[1].nodes.find(shows);

/** The rectangles that must not touch. */
const rects = (page, sel) => page.$$eval(sel, (es) => es.map((e) => { const r = e.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right }; }));
const touches = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
/** The popover: fully on screen, and off the chosen row. */
async function popOk(page, name) {
  const [p] = await rects(page, '.cp-pop:not([hidden])');
  if (!p) return fail(name, 'no popover');
  const vp = page.viewportSize();
  if (p.left < 0 || p.top < 0 || p.right > vp.width || p.bottom > vp.height) fail(name, { offScreen: p, vp });
  const [sel] = await rects(page, '.cp-row[aria-selected="true"]');
  if (sel && touches(p, sel)) fail(name, { covers: sel, p });
}
const ready = (page, tf) => page.waitForFunction((want) => document.documentElement.dataset.chartState === 'ready' && state.tf === want, tf, { timeout: 60000 });
const clickTf = (page, tf) => page.click(`#seg-tf button[data-value="${tf}"]`);
const leaf = levels[3].nodes[0].id;

const browser = await launch();

await visit(browser, 'the list: all roots open, twelve lines without scrolling, nothing selected but the best', '/chart.html?venue=bybit&tf=1d&counts=1', DESKTOP, async (page) => {
  await shot(page, 'r5_list_all_open');
  const n = await page.$$eval('.cp-row', (e) => e.length);
  if (n !== 12) fail('twelve rows', n);
  const { sh, ch } = await page.$eval('#counts-panel', (e) => ({ sh: e.scrollHeight, ch: e.clientHeight }));
  if (sh > ch) fail('panel scrolls on a desktop', { sh, ch });
  const one = await page.$$eval('.cp-row', (es) => es.map((e) => e.getBoundingClientRect().height));
  if (one.some((h) => h > 30)) fail('row height', one);
  const pin = await page.$eval('.cp-pin', (e) => e.getBoundingClientRect().height);
  if (pin > 34) fail('premise is one line', pin);
  await page.click('.cp-row[data-id="1d.2"] .cp-tri');
  await page.waitForTimeout(200);
  if (await page.$$eval('.cp-row', (e) => e.length) !== 9) fail('collapse', 'not nine rows');
  await shot(page, 'r5_list_root_collapsed');
  await page.reload();
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready');
  await page.waitForTimeout(800);
  if (await page.$$eval('.cp-row', (e) => e.length) !== 9) fail('collapse is remembered', 'lost on reload');
  await page.click('.cp-row[data-id="1d.2"] .cp-tri');
});

await visit(browser, 'popover: hover on the icon, across to it, pinned, escape, outside click', `/chart.html?venue=bybit&tf=4h&counts=1&cn=${levels[1].nodes[0].id}`, DESKTOP, async (page) => {
  const id = levels[1].nodes[0].id;
  await page.hover(`.cp-row[data-id="${id}"] .cp-i`);
  await page.waitForTimeout(300);
  await popOk(page, 'hover popover');
  await shot(page, 'r5_popover_hover');
  const text = await page.$eval('.cp-pop', (e) => e.textContent);
  for (const want of ['Legs', 'Running', 'Target', 'Invalid', 'Odds', 'Why this score', 'All levels']) if (!text.includes(want)) fail('popover content', want);
  const [box] = await rects(page, '.cp-pop');
  await page.mouse.move((box.left + box.right) / 2, (box.top + box.bottom) / 2, { steps: 6 }); // across the row and on to the popover
  await page.waitForTimeout(500);
  if (await page.$eval('.cp-pop', (e) => e.hidden)) fail('popover', 'closed on the way to it');
  await page.mouse.move(200, 700);
  await page.waitForTimeout(500);
  if (!await page.$eval('.cp-pop', (e) => e.hidden)) fail('popover', 'stayed open after leaving');
  await page.click(`.cp-row[data-id="${id}"] .cp-i`);
  await page.waitForTimeout(200);
  await page.mouse.move(200, 700);
  await page.waitForTimeout(500);
  if (await page.$eval('.cp-pop', (e) => e.hidden)) fail('pin', 'a pinned popover closed on leaving');
  await page.click('.cp-pop details[data-open="why"] summary');
  await page.waitForTimeout(150);
  await popOk(page, 'pinned popover');
  await shot(page, 'r5_popover_pinned_why');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(100);
  if (!await page.$eval('.cp-pop', (e) => e.hidden)) fail('escape', 'did not close');
  await page.click(`.cp-row[data-id="${id}"] .cp-i`);
  await page.mouse.click(200, 500);
  await page.waitForTimeout(100);
  if (!await page.$eval('.cp-pop', (e) => e.hidden)) fail('outside click', 'did not close');
  // the last row, near the bottom of the screen
  await page.click(`.cp-row[data-id="${levels[3].nodes[2].id}"] .cp-i`);
  await page.waitForTimeout(200);
  await popOk(page, 'popover on the last row');
  await shot(page, 'r5_popover_last_row');
  await page.keyboard.press('Escape');
  for (const key of ['premise', 'cross', 'about']) {
    await page.click(`.cp-i[data-pop="${key}"]`);
    await page.waitForTimeout(200);
    await popOk(page, `popover ${key}`);
    await shot(page, `r5_popover_${key}`);
    await page.keyboard.press('Escape');
  }
});

await visit(browser, 'a narrow window: the popover flips above or below', `/chart.html?venue=bybit&tf=4h&counts=1&cn=${levels[1].nodes[0].id}`, { width: 700, height: 800 }, async (page) => {
  await page.click(`.cp-row[data-id="${levels[3].nodes[0].id}"] .cp-i`);
  await page.waitForTimeout(200);
  await popOk(page, 'narrow popover');
  await shot(page, 'r5_popover_narrow_window');
});

await visit(browser, 'keyboard', '/chart.html?venue=bybit&tf=1d&counts=1', DESKTOP, async (page) => {
  await page.focus('.cp-row[data-id="1d.1"]');
  const active = () => page.evaluate(() => document.activeElement?.dataset?.id ?? null);
  await page.keyboard.press('ArrowDown');
  if (await active() !== '1d.1.1') fail('down', await active());
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('ArrowUp');
  if (await active() !== '1d.1.1') fail('up', await active());
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(100);
  if (await page.$eval('.cp-row[data-id="1d.1.1"]', (e) => e.getAttribute('aria-expanded')) !== 'false') fail('left', 'did not collapse');
  if (await active() !== '1d.1.1') fail('left keeps focus', await active());
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(100);
  if (await page.$eval('.cp-row[data-id="1d.1.1"]', (e) => e.getAttribute('aria-expanded')) !== 'true') fail('right', 'did not expand');
  await page.keyboard.press('Enter');
  await ready(page, '4h');
  await page.waitForTimeout(600);
  if (new URL(page.url()).searchParams.get('cn') !== '1d.1.1') fail('enter', page.url());
  await shot(page, 'r5_keyboard_selected');
  await page.keyboard.press('i');
  await page.waitForTimeout(150);
  if (await page.$eval('.cp-pop', (e) => e.hidden)) fail('i', 'did not open');
  await page.keyboard.press('Escape');
});

// the core of the request: a 15m count with its parents, then the same branch on each timeframe
await visit(browser, 'a 15m count shows its whole chain, and the timeframe buttons keep the branch', `/chart.html?venue=bybit&tf=1d&counts=1`, DESKTOP, async (page) => {
  await page.click(`.cp-row[data-id="${leaf}"] .cp-name`);
  await ready(page, '15m');
  await page.waitForTimeout(900);
  await shot(page, 'r5_chain_15m');
  const check = async (tf, id) => {
    const got = await page.evaluate(() => globalThis.EWCounts.drawn());
    if (got.node !== id) fail(`selected on ${tf}`, got);
    const want = levels.map((lv) => lv.nodes.find((n) => id === n.id || id.startsWith(`${n.id}.`))?.id).filter(Boolean);
    if (JSON.stringify(got.path) !== JSON.stringify(want)) fail(`levels on ${tf}`, { got: got.path, want });
    const marked = await page.$$eval('.cp-row[data-path="true"], .cp-row[aria-selected="true"]', (es) => es.map((e) => e.dataset.id));
    if (JSON.stringify(marked) !== JSON.stringify(want)) fail(`the list agrees with the chart on ${tf}`, { marked, want });
    if (got.labels.some((l) => !l.onChart && !l.marker)) fail(`a label dropped on ${tf}`, got.labels);
    return got;
  };
  const on15 = await check('15m', leaf);
  if (!on15.labels.some((l) => l.marker && l.text.includes('1D: 0 at 126,150 on 2025-10-06'))) fail('edge marker of the root on 15m', on15.labels);
  await clickTf(page, '1h');
  await ready(page, '1h');
  await page.waitForTimeout(900);
  await shot(page, 'r5_chain_1h_via_button');
  await check('1h', levels[2].nodes[0].id);
  await clickTf(page, '4h');
  await ready(page, '4h');
  await page.waitForTimeout(900);
  await shot(page, 'r5_chain_4h_via_button');
  const on4 = await check('4h', levels[1].nodes[0].id);
  if (!on4.labels.some((l) => l.tf === '1d' && l.onChart)) fail('1D labels on the 4H chart', on4.labels);
  await clickTf(page, '15m');
  await ready(page, '15m');
  await page.waitForTimeout(900);
  await check('15m again', leaf);
  await page.click('#seg-count-view button[data-value="focus"]');
  await page.waitForTimeout(500);
  await shot(page, 'r5_focus_15m');
  const f = await check('15m focus', leaf);
  if (!f.labels.some((l) => l.marker && l.tf === '1h')) fail('focus keeps the parents as markers', f.labels);
  if (new URL(page.url()).searchParams.get('cview') !== 'focus') fail('focus in the url', page.url());
  await page.reload();
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready');
  await page.waitForTimeout(800);
  if (await page.$eval('#seg-count-view button[data-value="focus"]', (e) => e.getAttribute('aria-pressed')) !== 'true') fail('focus remembered', 'no');
  await page.click('#seg-count-view button[data-value="chain"]');
});

for (const n of levels[3].nodes.slice(1)) {
  await visit(browser, `15m chain of ${n.id}`, `/chart.html?venue=bybit&tf=15m&counts=1&cn=${n.id}`, DESKTOP, async (page) => { await shot(page, `r5_chain_15m_${n.id}`); });
}
for (const n of levels[2].nodes.slice(1)) {
  await visit(browser, `1H chain of ${n.id}`, `/chart.html?venue=bybit&tf=1h&counts=1&cn=${n.id}`, DESKTOP, async (page) => { await shot(page, `r5_chain_1h_${n.id}`); });
}
for (const n of levels[1].nodes) {
  await visit(browser, `4H chain of ${n.id}`, `/chart.html?venue=bybit&tf=4h&counts=1&cn=${n.id}`, DESKTOP, async (page) => { await shot(page, `r5_chain_4h_${n.id}`); });
}
for (const n of levels[0].nodes) {
  await visit(browser, `root ${n.id}`, `/chart.html?venue=bybit&tf=1d&counts=1&cn=${n.id}`, DESKTOP, async (page) => { await shot(page, `r5_root_${n.id}`); });
}
if (!his) fail('his impulse', 'no 4H node shows it');
else await visit(browser, 'his impulse on the 4H, each wave with its inside', `/chart.html?venue=bybit&tf=4h&counts=1&cn=${his.id}`, DESKTOP, async (page) => {
  await page.click(`.cp-row[data-id="${his.id}"] .cp-i`);
  await page.waitForTimeout(150);
  const line = await page.$eval('.cp-pop', (e) => e.textContent);
  for (const want of ['W1 5 ok', 'W3 5 ok', 'W5 5 ok']) if (!line.includes(want)) fail('inside line on his five', { want, line: line.slice(0, 300) });
  await shot(page, 'r5_his_impulse_popover');
});
await visit(browser, 'turning counts on draws the best count, and a timeframe switch follows its branch', '/chart.html?venue=bybit&tf=4h', DESKTOP, async (page) => {
  await page.click('#seg-counts button');
  await page.waitForTimeout(600);
  const on = new URL(page.url()).searchParams.get('cn');
  if (on !== first(1)) fail('autoPick', { on, want: first(1) });
  await shot(page, 'r5_auto_4h');
  await clickTf(page, '1h');
  await ready(page, '1h');
  await page.waitForTimeout(700);
  const cn = new URL(page.url()).searchParams.get('cn');
  if (!cn || !cn.startsWith(`${on}.`)) fail('autoNode', { cn, on });
});
await visit(browser, 'click a node moves the chart to its timeframe and venue', '/chart.html?venue=bitstamp&tf=1d&counts=1', DESKTOP, async (page) => {
  await page.click(`.cp-row[data-id="${first(2)}"] .cp-name`);
  await page.waitForFunction(() => document.documentElement.dataset.chartState === 'ready' && state.tf === '1h' && state.venue === 'bybit_btcusdt_perp', null, { timeout: 60000 });
  await page.waitForTimeout(700);
  const u = new URL(page.url());
  if (u.searchParams.get('tf') !== '1h' || u.searchParams.get('cn') !== first(2)) fail('click', u.search);
});
await visit(browser, 'another venue: the note, and nothing drawn', '/chart.html?venue=bitstamp&tf=1d&counts=1', DESKTOP, async (page) => { await shot(page, 'r5_other_venue'); });
await visit(browser, '12h root', `/chart.html?venue=bybit&tf=1d&counts=1&croot=12h&cn=12h.1`, DESKTOP, async (page) => { await shot(page, 'r5_root_12h'); });
await visit(browser, '12h root switch', `/chart.html?venue=bybit&tf=4h&counts=1&cn=1d.1.1`, DESKTOP, async (page) => {
  await page.click('#seg-count-root button[data-value="12h"]');
  await page.waitForTimeout(500);
  if (new URL(page.url()).searchParams.get('croot') !== '12h') fail('root switch', page.url());
  await shot(page, 'r5_root_switch_12h');
});
await visit(browser, 'cycles and counts together', `/chart.html?venue=bybit&tf=1d&scale=log&counts=1&cycles=1&cn=${first(0)}`, DESKTOP, async (page) => { await shot(page, 'r5_with_cycles'); });
await visit(browser, 'log scale on 4H', `/chart.html?venue=bybit&tf=4h&scale=log&counts=1&cn=${first(1)}`, DESKTOP, async (page) => { await shot(page, 'r5_4h_log'); });
await visit(browser, 'phone: the list as a bottom sheet, a tapped sheet, the chain', `/chart.html?venue=bybit&tf=15m&counts=1&cn=${leaf}`, PHONE, async (page) => {
  await shot(page, 'r5_phone_15m_chain');
  await page.click(`.cp-row[data-id="${leaf}"] .cp-i`);
  await page.waitForTimeout(250);
  await popOk(page, 'phone sheet');
  await shot(page, 'r5_phone_sheet');
  await page.click('.cp-pop .cp-pop-x');
  await page.waitForTimeout(100);
  if (!await page.$eval('.cp-pop', (e) => e.hidden)) fail('phone sheet', 'close');
  await page.$eval('#counts-panel', (e) => { e.scrollTop = 1000; });
  await page.waitForTimeout(150);
  await shot(page, 'r5_phone_list_end');
}, { touch: true });
await visit(browser, 'phone, 1D, all roots', `/chart.html?venue=bybit&tf=1d&counts=1`, PHONE, async (page) => { await shot(page, 'r5_phone_1d'); }, { touch: true });
await visit(browser, 'phone, panel closed', '/chart.html?venue=bybit&tf=1d', PHONE, async (page) => { await shot(page, 'r5_phone_off'); });
await visit(browser, 'toggle on and off', '/chart.html?venue=bybit&tf=1d', DESKTOP, async (page) => {
  const shown = await page.$eval('#seg-counts', (e) => !e.hidden);
  const closed = await page.$eval('#counts-panel', (e) => e.hidden);
  if (!shown || !closed) fail('toggle', { shown, closed });
  await shot(page, 'r5_off');
  await page.click('#seg-counts button');
  await page.waitForTimeout(300);
  if (await page.$eval('#counts-panel', (e) => e.hidden)) fail('toggle', 'panel did not open');
  if (new URL(page.url()).searchParams.get('counts') !== '1') fail('toggle', 'no url state');
  await page.click('#seg-counts button');
  await page.waitForTimeout(300);
  if (new URL(page.url()).searchParams.has('counts')) fail('toggle', 'url state stayed');
});
await browser.close();

// Without the private files: no toggle, and the page looks as it does today.
const noData = await launch();
await visit(noData, 'no private file', '/chart.html?venue=bybit&tf=1d&counts=1&cycles=1', DESKTOP, async (page) => {
  const seen = await page.evaluate(() => ['seg-counts', 'seg-cycles', 'counts-panel'].map((id) => !document.getElementById(id).hidden));
  if (seen.some(Boolean)) fail('no private file', seen);
  await shot(page, 'counts_no_private_data');
}, { route: /\/data\/local\//, allow: ['404'] });
await noData.close();

// The public host: same files, served as elliott.yaga.sh. No toggle, and the private file is never asked for.
const port = new URL(base).port;
const pub = await launch([`--host-resolver-rules=MAP elliott.yaga.sh 127.0.0.1:${port}`]);
await visit(pub, 'public host', '/chart.html?venue=bybit&tf=1d&counts=1', DESKTOP, async (page, requested) => {
  const asked = requested.filter((u) => u.includes('/data/local'));
  const seen = await page.$eval('#seg-counts', (e) => !e.hidden);
  if (asked.length || seen) fail('public host', { asked, seen });
  await shot(page, 'counts_public_host');
}, { root: 'http://elliott.yaga.sh' });
await pub.close();

if (baseline) {
  const hash = (name) => crypto.createHash('sha256').update(fs.readFileSync(path.join(out, name))).digest('hex').slice(0, 16);
  const b = await launch();
  await visit(b, 'baseline, as committed', '/chart.html?venue=bybit&tf=1d', DESKTOP, async (page) => { await shot(page, 'baseline_committed'); }, { root: baseline });
  await b.close();
  const same = hash('baseline_committed.png') === hash('counts_public_host.png');
  report.push({ name: 'public page equals the committed page', same });
  if (!same) ok = false;
}

console.log(JSON.stringify(report.filter((r) => !r.done), null, 1));
console.log(`${report.length} checks`);
console.log(ok ? 'ALL OK' : 'PROBLEMS FOUND');
process.exit(ok ? 0 : 1);

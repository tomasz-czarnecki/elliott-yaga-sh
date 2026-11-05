// Size QA: renders every mark at 1x and enlarges the pixels, so a 16 px problem cannot hide behind scaling.
//   node design/logo-r1/qa.mjs [outdir]        (needs the server on 8083)
import fs from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../../tools/package.json', import.meta.url));
const { chromium } = require('playwright-core');

const out = process.argv[2] || '/opt/data/cache/scratch/elliott_logo_r1/shots';
const names = ['five-strokes', 'bracket-impulse', 'one-line', 'broom-candle', 'fib-lattice', 'side-eye', 'broom-five', 'loaded-die'];
const CHROME = process.env.CHROME || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome';
const browser = await chromium.launch({ executablePath: CHROME });
const page = await (await browser.newContext({ viewport: { width: 1500, height: 1200 }, deviceScaleFactor: 1 })).newPage();
await page.goto('http://127.0.0.1:8083/wordmark.json');
await page.setContent(`<body style="margin:0;background:#0C1526;color:#93A1B7;font:12px monospace"><canvas id="c" width="1500" height="1200"></canvas></body>`);
await page.evaluate(async (names) => {
  const c = document.getElementById('c'), x = c.getContext('2d');
  const load = (src) => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = src; });
  // Draw at 1x on a scratch canvas with the given background, then blow it up with no smoothing.
  const pix = (img, s, bg, scale, dx, dy) => {
    const t = document.createElement('canvas'); t.width = t.height = s;
    const g = t.getContext('2d'); g.fillStyle = bg; g.fillRect(0, 0, s, s); g.drawImage(img, 0, 0, s, s);
    x.imageSmoothingEnabled = false; x.drawImage(t, dx, dy, s * scale, s * scale);
  };
  x.fillStyle = '#0C1526'; x.fillRect(0, 0, 1500, 1200);
  x.font = '12px monospace'; x.fillStyle = '#93A1B7';
  let y = 8;
  for (const name of names) {
    const a = await load(`http://127.0.0.1:8083/${name}/mark.svg`), s16 = await load(`http://127.0.0.1:8083/${name}/mark-16.svg`), l16 = await load(`http://127.0.0.1:8083/${name}/mark-16-light.svg`);
    x.fillStyle = '#93A1B7'; x.fillText(name, 8, y + 12);
    x.drawImage(a, 8, y + 20, 110, 110);
    pix(s16, 16, '#0C1526', 8, 140, y + 8);
    pix(l16, 16, '#FFFFFF', 8, 280, y + 8);
    pix(a, 36, '#0C1526', 3.5, 420, y + 8);
    x.drawImage(s16, 560, y + 8, 16, 16);
    x.drawImage(a, 590, y + 8, 36, 36);
    y += 142;
  }
}, names);
await page.screenshot({ path: `${out}/qa_sizes.png`, clip: { x: 0, y: 0, width: 650, height: 1150 } });
// Bounds: draw each master with room around it, so anything the 64 box clips shows up as ink at the edge.
const report = await page.evaluate(async (names) => {
  const res = {};
  for (const name of names) for (const file of ['mark', 'mark-16']) {
    const src = await (await fetch(`/${name}/${file}.svg`)).text();
    const svg = src.replace('viewBox="0 0 64 64"', 'viewBox="-16 -16 96 96" width="384" height="384"');
    const i = new Image(); await new Promise((ok) => { i.onload = ok; i.src = 'data:image/svg+xml,' + encodeURIComponent(svg); });
    const t = document.createElement('canvas'); t.width = t.height = 384; const g = t.getContext('2d'); g.drawImage(i, 0, 0);
    const { data } = g.getImageData(0, 0, 384, 384);
    let x0 = 384, y0 = 384, x1 = 0, y1 = 0;
    for (let y = 0; y < 384; y++) for (let x = 0; x < 384; x++) if (data[(y * 384 + x) * 4 + 3] > 40) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    const f = (v) => +(v / 4 - 16).toFixed(1);
    res[`${name}/${file}`] = [f(x0), f(y0), f(x1 + 1), f(y1 + 1)].join(' ');
  }
  return res;
}, names);
console.log(report);
// All dark lockups, which the page does not otherwise show as files.
await page.setContent('<body style="margin:0;background:#0C1526;padding:12px;display:grid;grid-template-columns:1fr 1fr;gap:12px 24px;width:560px">' + names.map((n) => `<img src="http://127.0.0.1:8083/${n}/lockup.svg" height="36">`).join('') + '</body>');
await page.waitForLoadState('networkidle');
await page.screenshot({ path: `${out}/lockups.png`, clip: { x: 0, y: 0, width: 600, height: 220 } });
await browser.close();

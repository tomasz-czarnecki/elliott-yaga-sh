// Candles (log price) and RSI(11) for one masked window, as a PNG for the chart-image condition.
//   node research/model-options/spikes/bakeoff/render_chart.mjs WINDOW_JSON OUT_PNG
// Uses the repo's playwright-core from tools/ and the server's Chromium. Self-contained SVG, no network, no chart library.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const here = path.dirname(new URL(import.meta.url).pathname);
const require = createRequire(path.resolve(here, '../../../../tools/package.json'));
const { chromium } = require('playwright-core');
const CHROME = process.env.CHROME || '/opt/hermes/tools/chromium-1208/chrome-linux64/chrome';

const [inPath, outPath] = process.argv.slice(2);
const w = JSON.parse(fs.readFileSync(inPath, 'utf8'));
const bars = w.bars;
const W = 1800, H = 1100, L = 20, R = 110, T = 40, PRICE_H = 760, GAP = 30, RSI_H = 200, B = 60;
const xs = (i) => L + (i + 0.5) * ((W - L - R) / bars.length);
const cw = Math.max(1.5, ((W - L - R) / bars.length) * 0.7);
const lo = Math.min(...bars.map((b) => b.low)), hi = Math.max(...bars.map((b) => b.high));
const ly = (p) => T + (Math.log(hi) - Math.log(p)) / (Math.log(hi) - Math.log(lo)) * PRICE_H;
const ry = (v) => T + PRICE_H + GAP + (100 - v) / 100 * RSI_H;
let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" font-family="monospace" font-size="15"><rect width="100%" height="100%" fill="#fff"/>`;
svg += `<text x="${L}" y="24" font-size="18">BTC/USD ${w.tf.toUpperCase()}, log scale. Last close ${w.last_close.toFixed(2)}</text>`;
// price grid: 14 log-spaced levels
for (let k = 0; k <= 14; k++) {
  const p = Math.exp(Math.log(lo) + (Math.log(hi) - Math.log(lo)) * k / 14);
  const y = ly(p);
  svg += `<line x1="${L}" x2="${W - R}" y1="${y}" y2="${y}" stroke="#e3e3e3"/><text x="${W - R + 6}" y="${y + 5}">${p.toFixed(p > 100 ? 0 : 2)}</text>`;
}
// time grid: 12 labels
for (let k = 0; k <= 12; k++) {
  const i = Math.min(bars.length - 1, Math.round(k / 12 * (bars.length - 1)));
  const x = xs(i);
  svg += `<line x1="${x}" x2="${x}" y1="${T}" y2="${T + PRICE_H + GAP + RSI_H}" stroke="#eee"/>`;
  svg += `<text x="${x}" y="${H - B + 24}" text-anchor="middle" font-size="13" transform="rotate(0 ${x} ${H - B + 24})">${bars[i].time.replace(' ', 'T').slice(2, w.tf === '1d' ? 10 : 13)}</text>`;
}
for (let i = 0; i < bars.length; i++) {
  const b = bars[i], x = xs(i), up = b.close >= b.open, c = up ? '#18794e' : '#c62828';
  svg += `<line x1="${x}" x2="${x}" y1="${ly(b.high)}" y2="${ly(b.low)}" stroke="${c}"/>`;
  const a = ly(Math.max(b.open, b.close)), d = ly(Math.min(b.open, b.close));
  svg += `<rect x="${x - cw / 2}" y="${a}" width="${cw}" height="${Math.max(1, d - a)}" fill="${c}"/>`;
}
// RSI pane
for (const v of [30, 40, 50, 60, 70]) {
  svg += `<line x1="${L}" x2="${W - R}" y1="${ry(v)}" y2="${ry(v)}" stroke="#ccc" stroke-dasharray="4 4"/><text x="${W - R + 6}" y="${ry(v) + 5}">${v}</text>`;
}
const pts = bars.filter((b) => b.rsi11 === b.rsi11).map((b, k) => `${xs(bars.indexOf(b))},${ry(b.rsi11)}`).join(' ');
svg += `<polyline points="${pts}" fill="none" stroke="#3949ab" stroke-width="1.5"/><text x="${L + 4}" y="${ry(100) + 16}">RSI(11)</text></svg>`;
const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.setContent(`<!doctype html><html><body style="margin:0">${svg}</body></html>`);
await page.screenshot({ path: outPath });
await browser.close();
console.log('wrote', outPath, fs.statSync(outPath).size);

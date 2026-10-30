/** Landing page: every number comes from data/stats.json, and the hero plot from the daily Bitstamp bars. */

const HISTORY_VENUE = 'bitstamp_btcusd';
const YEAR_MS = 365.25 * 864e5;
const SVG_NS = 'http://www.w3.org/2000/svg';

const setText = (root, sel, text) => root.querySelectorAll(sel).forEach((el) => { el.textContent = text; });

function fillStats(stats) {
  const venues = Object.values(stats.venues);
  const rows = venues.reduce((sum, v) => sum + v.rows_1m, 0);
  const first = Math.min(...venues.map((v) => v.first_minute_ms));
  const last = Math.max(...venues.map((v) => v.last_minute_ms));

  setText(document, '[data-total="rows"]', `${(rows / 1e6).toFixed(1)} M`);
  setText(document, '[data-total="years"]', ((last - first) / YEAR_MS).toFixed(1));
  setText(document, '[data-total="venues"]', String(venues.length));
  setText(document, '[data-total="until"]', EW.fmtMinute(last));
  setText(document, '[data-total="generated"]', EW.fmtMinute(stats.generated_at_ms));

  document.querySelectorAll('[data-venue]').forEach((card) => {
    const v = stats.venues[card.dataset.venue];
    setText(card, '[data-field="first"]', EW.fmtDate(v.first_minute_ms));
    setText(card, '[data-field="last"]', EW.fmtMinute(v.last_minute_ms));
    setText(card, '[data-field="rows"]', EW.fmtInt(v.rows_1m));
    setText(card, '[data-field="missing"]', v.gaps ? `${EW.fmtInt(v.missing_minutes)} (${v.gaps} outages)` : EW.fmtInt(v.missing_minutes));
    setText(card, '[data-field="sync"]', v.last_ok_sync_ms ? EW.fmtMinute(v.last_ok_sync_ms) : 'n/a');
  });
}

/** Daily bars folded into one candle per UTC month. */
function monthlyCandles(b) {
  const months = [];
  let cur = null;
  for (let i = 0; i < b.n; i++) {
    const d = new Date(b.time[i] * 1000);
    const key = d.getUTCFullYear() * 12 + d.getUTCMonth();
    if (!cur || cur.key !== key) {
      cur = { key, open: b.open[i], high: b.high[i], low: b.low[i], close: b.close[i] };
      months.push(cur);
    } else {
      cur.high = Math.max(cur.high, b.high[i]);
      cur.low = Math.min(cur.low, b.low[i]);
      cur.close = b.close[i];
    }
  }
  return months;
}

function svgEl(name, attrs, text) {
  const el = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (text) el.textContent = text;
  return el;
}

/** Candles on a log axis, drawn at the plot's real pixel size so the labels keep their size on a phone. */
function drawHistory(plot, months) {
  const css = getComputedStyle(document.documentElement);
  const color = (name) => css.getPropertyValue(name).trim();
  const W = plot.clientWidth;
  const H = plot.clientHeight;
  const m = { top: 16, right: 16, bottom: 28, left: 68 };
  const lo = Math.log10(Math.min(...months.map((c) => c.low)));
  const hi = Math.log10(Math.max(...months.map((c) => c.high)));
  const y = (p) => m.top + (hi - Math.log10(p)) / (hi - lo) * (H - m.top - m.bottom);
  const step = (W - m.left - m.right) / months.length;
  const x = (i) => m.left + (i + 0.5) * step;
  const bodyW = Math.max(1, Math.floor(step) - 1);

  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, 'aria-hidden': 'true' });

  for (const p of [10, 100, 1000, 10000, 100000]) {
    if (Math.log10(p) < lo || Math.log10(p) > hi) continue;
    svg.append(svgEl('line', { x1: m.left, x2: W - m.right, y1: y(p), y2: y(p), stroke: color('--line') }));
    svg.append(svgEl('text', { x: m.left - 8, y: y(p) + 4, 'text-anchor': 'end' }, `$${EW.fmtInt(p)}`));
  }

  const yearEvery = W < 420 ? 4 : 2;
  months.forEach((c, i) => {
    const year = Math.floor(c.key / 12);
    if (c.key % 12 === 0 && year % yearEvery === 0) {
      svg.append(svgEl('text', { x: x(i), y: H - 8, 'text-anchor': 'middle' }, String(year)));
    }
  });

  const paths = { up: '', down: '' };
  months.forEach((c, i) => {
    const dir = c.close >= c.open ? 'up' : 'down';
    const cx = Math.round(x(i));
    const top = y(Math.max(c.open, c.close));
    const bot = y(Math.min(c.open, c.close));
    paths[dir] += `M${cx + 0.5} ${y(c.high).toFixed(1)}V${y(c.low).toFixed(1)}`;
    paths[dir] += `M${cx - bodyW / 2 + 0.5} ${top.toFixed(1)}h${bodyW}V${Math.max(bot, top + 1).toFixed(1)}h${-bodyW}Z`;
  });
  svg.append(svgEl('path', { d: paths.up, stroke: color('--up'), fill: color('--up') }));
  svg.append(svgEl('path', { d: paths.down, stroke: color('--down'), fill: color('--down') }));

  plot.replaceChildren(svg);
}

async function startHistory(stats) {
  const plot = document.querySelector('.history-plot');
  const months = monthlyCandles(await EW.loadBars(stats, HISTORY_VENUE, '1d'));
  drawHistory(plot, months);
  setText(document, '[data-history="from"]', String(Math.floor(months[0].key / 12)));
  let width = plot.clientWidth;
  new ResizeObserver(() => {
    if (plot.clientWidth === width) return;
    width = plot.clientWidth;
    drawHistory(plot, months);
  }).observe(plot);
}

EW.loadStats().then((stats) => {
  fillStats(stats);
  return startHistory(stats);
}).catch((err) => {
  console.warn('site data is not available:', err);
  document.querySelector('.history')?.setAttribute('hidden', '');
  setText(document, '[data-total]', 'n/a');
  setText(document, '[data-field]', 'n/a');
});

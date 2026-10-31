/**
 * Counts panel for the chart page: the top-down tree from `ewave-counts export` as a Finder-style list, with the details
 * of each line in a popover. Choosing a count draws it and all its higher-degree parents on the chart, at that count's
 * timeframe. What falls off the chart stays on it as an edge marker.
 *
 * The data is private (site/data/local/ is gitignored), so on the public hosts this script does nothing at all: it asks
 * for no file, because a browser logs every 404 in its console whatever the page does with it.
 */
(() => {
  if (/(^|\.)yaga\.sh$|\.vercel\.app$/.test(location.hostname)) return;

  const TF_NAME = { '1d': '1D', '12h': '12H', '4h': '4H', '1h': '1H', '15m': '15m' };
  const chartTf = (tf) => (tf === '12h' ? '1d' : tf); // the chart has no 12H bars: a 12H pivot sits inside its day

  const given = new URLSearchParams(location.search);
  const ui = {
    on: given.get('counts') === '1',
    root: given.get('croot') ?? null,
    node: given.get('cn') ?? null,
    pendingZoom: Boolean(given.get('cn')),
    view: null,   // 'chain' fits the parents, 'focus' fits the chosen count alone
    closed: null, // ids of the collapsed rows
    cursor: null, // the row the keyboard is on
    why: false,   // "Why this score" open
    kills: false, // "Killed by what is inside" open
    more: false,  // "All levels" open
    pm: false,    // the premise's details open
  };

  let data = null;
  let primitive = null;
  let byId = new Map();
  let scrollToPick = Boolean(ui.node);

  /** What outlives the page: collapsed rows and the zoom choice. A browser may refuse storage; then they last the visit. */
  const KEEP = 'ewave.counts.ui';
  const stored = (() => {
    try { return JSON.parse(localStorage.getItem(KEEP)) ?? {}; } catch { return {}; }
  })();
  function keep() {
    try { localStorage.setItem(KEEP, JSON.stringify({ ...stored, view: ui.view, closed: stored.closed })); } catch { /* not kept */ }
  }
  ui.view = ['chain', 'focus'].find((v) => v === (given.get('cview') ?? stored.view)) ?? 'chain';

  const px = (p) => Math.round(p).toLocaleString('en-US');
  const shortP = (p) => (p >= 1000 ? `${(p / 1000).toFixed(1)}k` : p.toFixed(0));
  const pct = (x) => (x < 0.001 ? 'under 0.1%' : `${(x * 100).toFixed(x < 0.1 ? 1 : 0)}%`);
  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const degreeColor = (d) => color(`--degree-${Math.min(d, 3)}`);
  const hexA = (hex, a) => `${hex}${Math.round(a * 255).toString(16).padStart(2, '0')}`;
  const tree = () => data.trees[ui.root];
  const narrow = () => innerWidth < 600;
  const WAVE = (l) => (/^\d$/.test(l) ? `W${l}` : l === 'X2' ? 'X' : l);
  const num = (x) => x.toFixed(2);
  const at = (l) => l.at ?? l.t; // the exact minute of a pivot, not the open of its own timeframe's bar: on a finer chart the two are far apart

  /** The chain from the root to a node: what gets drawn. */
  function chain(node) {
    const out = [];
    for (let n = node; n; n = n.parent ? byId.get(n.parent) : null) out.unshift(n);
    return out;
  }

  /** Degree notation: circled at the root, then (1), 1, i. Letters go the same way down. */
  const ROMAN = { 1: 'i', 2: 'ii', 3: 'iii', 4: 'iv', 5: 'v' };
  function labelText(raw, depth) {
    const l = raw === 'X2' ? 'X' : raw;
    if (depth === 0) return l;
    if (depth === 1) return `(${l})`;
    if (depth === 2) return l;
    return ROMAN[l] ?? l.toLowerCase();
  }

  /** Bar position of any time on the current chart: the bar holding it, or a fraction past either end. */
  function logical(t) {
    const step = BAR_MINUTES[state.tf] * 60;
    if (t <= bars.time[0]) return (t - bars.time[0]) / step;
    if (t >= bars.time[bars.n - 1] + step) return bars.n - 1 + (t - bars.time[bars.n - 1]) / step;
    let a = 0;
    let b = bars.n - 1;
    while (a < b) {
      const m = (a + b + 1) >> 1;
      if (bars.time[m] <= t) a = m;
      else b = m - 1;
    }
    return a;
  }

  const xOfBar = (i) => chart.timeScale().logicalToCoordinate(Math.round(i)); // the library answers 0 for a fractional position
  const xAt = (t) => xOfBar(logical(t));
  const visibleVenue = () => data && state.venue === data.venue;

  /** The price levels worth keeping on screen: not one that would crush the candles to a line. */
  function keepLevels(node) {
    const out = [node.invalidation.p, ...node.zone.map((z) => z.p)];
    if (node.odds[0]) out.push(node.odds[0].target);
    const reach = state.tf === '1d' ? 3 : 1.5;
    return out.filter((p) => p > data.price / reach && p < data.price * reach);
  }

  /** Which of a count's finished waves show their inside. At the root, whatever leads to a 5: the five he sees may sit two
   * levels down, as the C of a flat X. Below it, only a wave that is a 5 itself: every small correction holds some small 5. */
  const isFive = (r) => /impulse|diagonal/.test(r.pattern);
  const hasFive = (r) => isFive(r) || r.inside.some(hasFive);
  const shownInside = (n) => n.inside.filter(n.depth === 0 ? hasFive : isFive);

  const bracketRow = () => (narrow() ? 12 : 14);
  const EDGE_ROW = 14;

  /** The running wave in its own degree's notation: "1D Y running down from 87,384". */
  function waveTag(n) {
    const w = n.wave;
    const name = w.label === 'after' ? `after ${labelText(n.labels[n.labels.length - 1].l, n.depth)}` : labelText(w.label, n.depth);
    return narrow() ? `${TF_NAME[n.tf]} ${name} ${w.dir}` : `${TF_NAME[n.tf]} ${name} running ${w.dir} from ${px(w.start.p)}`;
  }

  class Overlay {
    constructor() {
      const self = this;
      this.views = [
        { zOrder: () => 'bottom', renderer: () => ({ draw: (t) => self.drawBack(t) }) },
        { zOrder: () => 'top', renderer: () => ({ draw: (t) => self.drawFront(t) }) },
      ];
    }

    attached({ requestUpdate }) { this.requestUpdate = requestUpdate; }
    detached() { this.requestUpdate = null; }
    updateAllViews() {}
    paneViews() { return this.views; }

    selected() {
      if (!ui.on || !bars || !ui.node || !visibleVenue()) return null;
      return byId.get(ui.node) ?? null;
    }

    autoscaleInfo(from, to) {
      const node = this.selected();
      if (!node) return null;
      const keep = keepLevels(node);
      const margins = { above: 30, below: chain(node).length * bracketRow() + 4 }; // room for a stack of labels on top; the brackets get their own strip, under the candles
      if (!keep.length) return { priceRange: null, margins };
      return { priceRange: { minValue: Math.min(...keep), maxValue: Math.max(...keep) }, margins };
    }

    /** Each parent's running wave, faintly, from its start to the right edge: they nest, so the chosen count sits in the darkest part. */
    drawBands(c, node, hr) {
      const width = chart.timeScale().width();
      const paneH = c.canvas.height;
      for (const n of chain(node).slice(0, -1)) {
        const x = xAt(at(n.wave.start));
        if (x == null || x > width) continue;
        const col = degreeColor(n.depth);
        c.fillStyle = hexA(col, 0.05);
        c.fillRect(Math.max(0, x) * hr, 0, (width - Math.max(0, x)) * hr, paneH);
        if (x < 0) continue;
        c.fillStyle = hexA(col, 0.4);
        c.fillRect(x * hr, 0, Math.max(1, hr), paneH);
      }
    }

    /** Where the boxes go: just right of the last bar. */
    boxSpan() {
      const r = chart.timeScale().getVisibleLogicalRange();
      const a = bars.n + 1;
      const b = r ? Math.max(a + 4, r.to - 1) : a + 8;
      return [xOfBar(a), xOfBar(b)];
    }

    /** The running wave's time window on screen: its edges, clipped to the pane, and whether it has already passed. */
    windowSpan(node) {
      const w = node.window;
      if (!w) return null;
      const lo = xAt(w.lo);
      const hi = xAt(w.hi);
      if (lo == null || hi == null || hi <= lo) return null;
      const width = chart.timeScale().width();
      if (hi < 0 || lo > width) return null;
      return { lo: Math.max(0, lo), hi: Math.min(width, hi), loRaw: lo, hiRaw: hi, past: w.status === 'past' };
    }

    /** The red line of his premise, wherever it is on the chart. */
    drawPremiseLine(target) {
      const pm = data.premise;
      if (!ui.on || !bars || !pm || !pm.applied || !visibleVenue()) return;
      const x = xAt(pm.top_t);
      if (x == null || x < 0 || x > chart.timeScale().width()) return;
      target.useBitmapCoordinateSpace(({ context: c, horizontalPixelRatio: hr }) => {
        c.strokeStyle = hexA(color('--down'), 0.8);
        c.lineWidth = Math.max(1, 1.5 * hr);
        c.beginPath();
        c.moveTo(x * hr, 0);
        c.lineTo(x * hr, c.canvas.height);
        c.stroke();
      });
    }

    drawBack(target) {
      this.drawPremiseLine(target);
      const node = this.selected();
      if (!node) return;
      target.useBitmapCoordinateSpace(({ context: c, horizontalPixelRatio: hr }) => this.drawBands(c, node, hr));
      target.useBitmapCoordinateSpace(({ context: c, horizontalPixelRatio: hr, verticalPixelRatio: vr }) => {
        const [a, b] = this.boxSpan();
        if (a == null || b == null) return;
        const box = (levels, col, fill, x0, x1) => {
          if (!levels.length || x1 <= x0) return;
          const ps = levels.map((l) => l.p);
          const top = candles.priceToCoordinate(Math.max(...ps));
          const bot = candles.priceToCoordinate(Math.min(...ps));
          if (top == null || bot == null) return;
          const h = Math.max(3, bot - top);
          c.fillStyle = hexA(col, fill);
          c.fillRect(x0 * hr, top * vr, (x1 - x0) * hr, h * vr);
          c.strokeStyle = hexA(col, 0.9);
          c.lineWidth = Math.max(1, hr);
          c.strokeRect(x0 * hr, top * vr, (x1 - x0) * hr, h * vr);
        };
        const span = this.windowSpan(node);
        if (span) { // the time window: a band over the whole pane, its edges dashed
          const col = span.past ? color('--down') : color('--accent');
          const paneH = c.canvas.height;
          c.fillStyle = hexA(col, span.past ? 0.06 : 0.1);
          c.fillRect(span.lo * hr, 0, (span.hi - span.lo) * hr, paneH);
          c.strokeStyle = hexA(col, 0.55);
          c.lineWidth = Math.max(1, hr);
          c.setLineDash([3 * hr, 3 * hr]);
          for (const x of [span.loRaw, span.hiRaw]) {
            if (x < 0 || x > chart.timeScale().width()) continue;
            c.beginPath();
            c.moveTo(x * hr, 0);
            c.lineTo(x * hr, paneH);
            c.stroke();
          }
          c.setLineDash([]);
        }
        // the target: a price x time box when the window is still ahead, otherwise a box just right of the last bar
        const live = span && !span.past;
        box(node.zone, color('--line-strong'), 0.35, live ? span.lo : a, live ? span.hi : b);
        const nextFrom = live ? Math.max(a, span.hi) : a;
        box(node.next.targets, node.next.dir === 'up' ? color('--up') : color('--down'), 0.14, nextFrom, b);
      });
    }

    drawFront(target) {
      this.taken = [];
      if (ui.on && bars && visibleVenue() && data.premise?.applied) {
        target.useBitmapCoordinateSpace(({ context: c, horizontalPixelRatio: hr, verticalPixelRatio: vr }) => {
          this.drawPremise(c, hr, vr);
        });
      }
      const node = this.selected();
      if (!node) return;
      target.useBitmapCoordinateSpace((scope) => {
        const { context: c, horizontalPixelRatio: hr, verticalPixelRatio: vr } = scope;
        c.textBaseline = 'middle';
        const path = chain(node);
        for (const n of path) this.drawCount(c, n, hr, vr, n === node); // first: they get the places next to their pivots
        for (const n of path) this.drawInside(c, shownInside(n), n.depth + 1, hr, vr);
        this.drawRunning(c, node, hr, vr);
        this.drawLegs(c, node, hr, vr);
        this.drawCrosshairs(c, node, hr, vr);
        this.drawWindowTag(c, node, hr, vr);
        this.drawLevels(c, node, hr, vr);
        this.drawBrackets(c, path, hr, vr);
        this.drawEdges(c, path, hr, vr);
      });
    }

    /** One bracket per level at the foot of the pane, the largest on top: "15m after y" under "1H Y" under "4H (Y)" under "1D Y". */
    drawBrackets(c, path, hr, vr) {
      const paneH = c.canvas.height / vr;
      const width = chart.timeScale().width();
      c.font = `${(narrow() ? 9 : 10) * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'left';
      path.forEach((n, i) => {
        const y = paneH - 8 - (path.length - 1 - i) * bracketRow();
        const raw = xAt(at(n.wave.start));
        if (raw == null || raw > width) return;
        const x = Math.max(0, raw);
        const col = degreeColor(n.depth);
        c.strokeStyle = hexA(col, 0.85);
        c.lineWidth = Math.max(1, hr);
        c.beginPath();
        c.moveTo(x * hr, y * vr);
        c.lineTo(width * hr, y * vr);
        if (raw >= 0) { // its start is on the chart: a tick; otherwise it runs off the left edge, and the text says from where
          c.moveTo(x * hr, (y - 4) * vr);
          c.lineTo(x * hr, (y + 4) * vr);
        }
        c.stroke();
        const text = `${raw < 0 ? '← ' : ''}${waveTag(n)}`;
        const w = c.measureText(text).width / hr;
        const tx = Math.max(2, Math.min(x + 5, width - w - 6));
        c.fillStyle = color('--bg');
        c.fillRect((tx - 3) * hr, (y - 6) * vr, (w + 6) * hr, 12 * vr);
        c.fillStyle = n.id === ui.node ? color('--ink') : col;
        c.fillText(text, tx * hr, y * vr);
      });
    }

    /** Every label of the chain that the chart cannot show right now: pinned to the top left, never dropped. */
    /** The lowest wave label under a stack of rows at the left edge, or null. */
    hitBy(wide, y, count) {
      const under = this.taken.filter((t) => t.x < wide + 12 && t.y > y - 15 && t.y < y + count * EDGE_ROW);
      return under.length ? Math.max(...under.map((t) => t.y)) : null;
    }

    edgeRows(path) {
      const width = chart.timeScale().width();
      const rows = [];
      for (const n of path) {
        for (const l of n.labels) {
          const x = xAt(at(l));
          if (x != null && x >= 0 && x <= width) continue;
          const same = rows.find((r) => r.l.p === l.p); // a child's 0 is its parent's last label: one pivot, one row, under the larger degree
          if (same) {
            same.also.push(l);
            continue;
          }
          rows.push({ n, l, also: [], text: `${x != null && x > width ? '→' : '←'} ${TF_NAME[n.tf]}: ${labelText(l.l, n.depth)} at ${px(l.p)} on ${EW.fmtDate(at(l) * 1000)}` });
        }
      }
      return rows;
    }

    drawEdges(c, path, hr, vr) {
      let rows = this.edgeRows(path);
      if (!rows.length) return;
      if (narrow()) { // no room for prices and dates: which labels, one line a level, and All levels has the rest
        rows = path.map((n) => ({ n, list: rows.filter((r) => r.n === n) })).filter((g) => g.list.length).map(({ n, list }) => ({
          n, text: `${list[0].text[0]} ${TF_NAME[n.tf]}: ${list.map((r) => labelText(r.l.l, n.depth)).join(' ')}`,
        }));
      }
      const paneH = c.canvas.height / vr;
      const fits = Math.max(2, Math.floor((paneH / 2 - 8) / EDGE_ROW));
      const shown = rows.length > fits ? rows.slice(-(fits - 1)) : rows; // the nearest levels, and a count of the rest
      c.font = `${(narrow() ? 9 : 10) * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'left';
      const line = (text, col, ink, y) => {
        const w = c.measureText(text).width / hr;
        c.fillStyle = hexA(color('--bg'), 0.9);
        c.fillRect(0, (y - 7) * vr, (w + 10) * hr, EDGE_ROW * vr);
        c.fillStyle = col;
        c.fillRect(0, (y - 7) * vr, 2 * hr, EDGE_ROW * vr);
        c.fillStyle = ink;
        c.fillText(text, 6 * hr, y * vr);
      };
      // top left, or the first place below it that hides no wave label
      const count = shown.length + (shown.length < rows.length ? 1 : 0);
      const wide = Math.max(...shown.map((r) => c.measureText(r.text).width / hr)) + 16;
      const foot = paneH - (path.length + 1) * bracketRow();
      let y = 10;
      for (let hit = this.hitBy(wide, y, count); hit != null && hit + 14 + count * EDGE_ROW < foot; hit = this.hitBy(wide, y, count)) y = hit + 18;
      if (this.hitBy(wide, y, count) != null) y = 10;
      if (shown.length < rows.length) {
        line(`${rows.length - shown.length} more off the chart: see All levels`, color('--line-strong'), color('--muted'), y);
        y += EDGE_ROW;
      }
      for (const r of shown) {
        line(r.text, degreeColor(r.n.depth), r.n.id === ui.node ? color('--ink') : color('--body'), y);
        y += EDGE_ROW;
      }
    }

    drawCount(c, node, hr, vr, active) {
      const col = degreeColor(node.depth);
      const pts = node.labels.map((l) => ({ ...l, x: xAt(at(l)), y: candles.priceToCoordinate(l.p) }));
      c.strokeStyle = hexA(col, active ? 0.95 : 0.55);
      c.lineWidth = Math.max(1, (active ? 2 : 1) * hr);
      c.beginPath();
      let started = false;
      for (const p of pts) {
        if (p.x == null || p.y == null) continue;
        if (!started) c.moveTo(p.x * hr, p.y * vr);
        else c.lineTo(p.x * hr, p.y * vr);
        started = true;
      }
      c.stroke();
      const size = narrow() ? 10 : 12;
      c.font = `${active ? 500 : 400} ${size * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'center';
      for (const p of pts) {
        if (p.x == null || p.y == null || p.l === '0') continue;
        const text = labelText(p.l, node.depth);
        const up = p.kind === 'H';
        let y = p.y + (up ? -14 : 14);
        while (this.taken.some((t) => Math.abs(t.x - p.x) < 18 && Math.abs(t.y - y) < 14)) y += up ? -14 : 14;
        this.taken.push({ x: p.x, y });
        if (node.depth === 0) { // the root's degree: a ring round the label
          c.strokeStyle = col;
          c.lineWidth = Math.max(1, 1.25 * hr);
          c.beginPath();
          c.arc(p.x * hr, y * vr, 9 * hr, 0, Math.PI * 2);
          c.fillStyle = color('--bg');
          c.fill();
          c.stroke();
        } else {
          const w = c.measureText(text).width / hr + 6;
          c.fillStyle = hexA(color('--bg'), 0.82);
          c.fillRect((p.x - w / 2) * hr, (y - 8) * vr, w * hr, 16 * vr);
        }
        c.fillStyle = active ? color('--ink') : color('--body');
        c.fillText(text, p.x * hr, y * vr);
      }
    }

    /** His five, faintly: it is given, not the engine's. */
    drawPremise(c, hr, vr) {
      const pm = data.premise;
      const pts = pm.labels.map((l) => ({ ...l, x: xAt(at(l)), y: candles.priceToCoordinate(l.p) })).filter((p) => p.x != null && p.y != null);
      c.textBaseline = 'middle';
      c.strokeStyle = hexA(color('--down'), 0.32);
      c.lineWidth = Math.max(1, hr);
      c.beginPath();
      pts.forEach((p, i) => (i ? c.lineTo(p.x * hr, p.y * vr) : c.moveTo(p.x * hr, p.y * vr)));
      c.stroke();
      c.font = `${(narrow() ? 10 : 11) * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'center';
      c.fillStyle = hexA(color('--down'), 0.7);
      for (const p of pts) {
        if (p.l === '0') continue;
        const y = p.y + (p.kind === 'H' ? -13 : 13);
        c.fillText(p.l, p.x * hr, y * vr);
        this.taken.push({ x: p.x, y });
      }
      const line = xAt(pm.top_t);
      if (line != null && line >= 0 && line < chart.timeScale().width() - 70) {
        c.font = `${(narrow() ? 9 : 10) * vr}px 'Geist Mono', monospace`;
        c.textAlign = 'left';
        c.fillStyle = hexA(color('--down'), 0.85);
        c.fillText('Premise: 5 up ended', (line + 5) * hr, (narrow() ? 42 : 30) * vr);
      }
    }

    /** What a chosen count's finished waves look like inside, one degree down: a 5 in plain lines, a 3 dotted, and only
     * what leads to a 5, since that is what the eye looks for. Too narrow on this chart to be read: left out. */
    drawInside(c, rows, depth, hr, vr) {
      for (const r of rows) {
        if (!hasFive(r)) continue;
        const pts = r.labels.map((l) => ({ ...l, x: xAt(at(l)), y: candles.priceToCoordinate(l.p) }));
        if (pts.some((p) => p.x == null || p.y == null)) continue;
        if (Math.abs(pts[pts.length - 1].x - pts[0].x) < (narrow() ? 70 : 100)) continue;
        const five = isFive(r);
        const col = degreeColor(depth);
        c.strokeStyle = hexA(col, five ? 0.7 : 0.35);
        c.lineWidth = Math.max(1, hr);
        c.setLineDash(five ? [] : [2 * hr, 3 * hr]);
        c.beginPath();
        pts.forEach((p, i) => (i ? c.lineTo(p.x * hr, p.y * vr) : c.moveTo(p.x * hr, p.y * vr)));
        c.stroke();
        c.setLineDash([]);
        c.font = `${(narrow() ? 9 : 11) * vr}px 'Geist Mono', monospace`;
        c.textAlign = 'center';
        for (const p of pts) {
          if (p.l === '0') continue;
          const up = p.kind === 'H';
          let y = p.y + (up ? -12 : 12);
          while (this.taken.some((t) => Math.abs(t.x - p.x) < 16 && Math.abs(t.y - y) < 12)) y += up ? -12 : 12;
          this.taken.push({ x: p.x, y });
          const text = labelText(p.l, depth);
          const w = c.measureText(text).width / hr + 4;
          c.fillStyle = hexA(color('--bg'), 0.7);
          c.fillRect((p.x - w / 2) * hr, (y - 7) * vr, w * hr, 14 * vr);
          c.fillStyle = hexA(color('--body'), five ? 0.95 : 0.7);
          c.fillText(text, p.x * hr, y * vr);
        }
        this.drawInside(c, r.inside, depth + 1, hr, vr);
      }
    }

    /** The running wave so far, dashed: from the last label to its extreme, then to the latest price. */
    drawRunning(c, node, hr, vr) {
      const w = node.wave;
      const from = { x: xAt(at(w.start)), y: candles.priceToCoordinate(w.start.p) };
      const mid = { x: xAt(w.so_far_t), y: candles.priceToCoordinate(w.so_far) };
      const end = { x: xOfBar(bars.n - 1), y: candles.priceToCoordinate(data.price) };
      if ([from.x, from.y, mid.x, mid.y, end.x, end.y].some((v) => v == null)) return;
      c.strokeStyle = hexA(degreeColor(node.depth), 0.9);
      c.lineWidth = Math.max(1, 1.5 * hr);
      c.setLineDash([5 * hr, 4 * hr]);
      c.beginPath();
      c.moveTo(from.x * hr, from.y * vr);
      c.lineTo(mid.x * hr, mid.y * vr);
      c.lineTo(end.x * hr, end.y * vr);
      c.stroke();
      c.setLineDash([]);
    }

    /** Each finished leg's duration and its ratio to the wave it is judged by. Red when time fails on that leg. */
    drawLegs(c, node, hr, vr) {
      const size = narrow() ? 9 : 10;
      c.font = `${size * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'center';
      for (const leg of node.legs) {
        const xa = xAt(leg.t0);
        const xb = xAt(leg.t1);
        const ya = candles.priceToCoordinate(leg.p0);
        const yb = candles.priceToCoordinate(leg.p1);
        if ([xa, xb, ya, yb].some((v) => v == null)) continue;
        const wide = Math.abs(xb - xa) + Math.abs(yb - ya);
        if (wide < (narrow() ? 60 : 44)) continue; // too small to carry a tag
        const small = narrow(); // a phone has room for the duration only, and only where nothing else sits
        const text = leg.x != null && !small ? `${leg.text} · ${leg.x}x` : leg.text;
        const x = (xa + xb) / 2 + (small ? 4 : 10);
        let y = (ya + yb) / 2 + (yb < ya ? 10 : -10);
        const clash = () => this.taken.some((t) => Math.abs(t.x - x) < (small ? 28 : 44) && Math.abs(t.y - y) < 13);
        if (small && clash()) continue;
        while (clash()) y += yb < ya ? 13 : -13;
        this.taken.push({ x, y });
        const w = c.measureText(text).width / hr + 6;
        c.fillStyle = hexA(color('--bg'), 0.78);
        c.fillRect((x - w / 2) * hr, (y - 7) * vr, w * hr, 14 * vr);
        c.fillStyle = leg.bad ? color('--down') : color('--muted');
        c.fillText(text, x * hr, y * vr);
      }
    }

    /** Where a price level meets a time level (FIB-T9). Ringed when the extreme so far already sits on one. */
    drawCrosshairs(c, node, hr, vr) {
      const width = chart.timeScale().width();
      c.strokeStyle = color('--ink');
      c.lineWidth = Math.max(1, hr);
      const arm = 4;
      for (const x of node.crosshairs) {
        const px_ = xAt(x.t);
        const py = candles.priceToCoordinate(x.p);
        if (px_ == null || py == null || px_ < 0 || px_ > width) continue;
        c.beginPath();
        c.moveTo((px_ - arm) * hr, py * vr);
        c.lineTo((px_ + arm) * hr, py * vr);
        c.moveTo(px_ * hr, (py - arm) * vr);
        c.lineTo(px_ * hr, (py + arm) * vr);
        c.stroke();
      }
      const hit = node.crosshair_hit;
      if (hit) {
        const hx = xAt(hit.t);
        const hy = candles.priceToCoordinate(hit.p);
        if (hx != null && hy != null) {
          c.strokeStyle = color('--accent');
          c.lineWidth = Math.max(1, 1.5 * hr);
          c.beginPath();
          c.arc(hx * hr, hy * vr, 7 * hr, 0, Math.PI * 2);
          c.stroke();
        }
      }
    }

    /** The dates of the window, at the top of its band. */
    drawWindowTag(c, node, hr, vr) {
      const span = this.windowSpan(node);
      if (!span) return;
      const w = node.window;
      const text = span.past ? `Window passed ${w.hi_str}` : `Due ${w.lo_str} to ${w.hi_str}`;
      c.font = `${(narrow() ? 9 : 10) * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'left';
      const tw = c.measureText(text).width / hr;
      const width = chart.timeScale().width();
      const x = Math.max(2, Math.min(span.lo + 4, width - tw - 8));
      c.fillStyle = hexA(color('--bg'), 0.82);
      c.fillRect((x - 3) * hr, 3 * vr, (tw + 6) * hr, 15 * vr);
      c.fillStyle = span.past ? color('--down') : color('--accent');
      c.fillText(text, x * hr, 11 * vr);
    }

    /** A level on the right edge of the pane, or pinned to the pane's edge with an arrow when it is off screen. */
    levelTag(c, text, p, col, hr, vr) {
      const paneH = c.canvas.height / vr;
      const raw = candles.priceToCoordinate(p);
      if (raw == null) return null;
      let y = raw;
      let shown = text;
      if (raw < 10) { y = 10; shown = `↑ ${text}`; }
      if (raw > paneH - 10) { y = paneH - 10; shown = `↓ ${text}`; }
      const step = y < paneH / 2 ? 15 : -15; // one way only: flipping at the middle could bounce between two taken slots forever
      while (this.tags.some((t) => Math.abs(t - y) < 15)) y += step;
      this.tags.push(y);
      const w = c.measureText(shown).width / hr;
      const x = Math.max(2, chart.timeScale().width() - w - 8);
      c.fillStyle = hexA(color('--bg'), 0.85);
      c.fillRect((x - 3) * hr, (y - 8) * vr, (w + 6) * hr, 16 * vr);
      c.fillStyle = col;
      c.fillRect((x - 3) * hr, (y - 8) * vr, 2 * hr, 16 * vr);
      c.fillStyle = color('--ink');
      c.textAlign = 'left';
      c.fillText(shown, x * hr, y * vr);
      return raw;
    }

    drawLevels(c, node, hr, vr) {
      c.font = `${(narrow() ? 10 : 11) * vr}px 'Geist Mono', monospace`;
      this.tags = this.windowSpan(node) ? [11] : []; // the top line belongs to the window's dates
      const width = chart.timeScale().width();
      const start = xAt(at(node.wave.start)) ?? 0;
      const line = (p, col, dash) => {
        const y = candles.priceToCoordinate(p);
        if (y == null) return;
        c.strokeStyle = col;
        c.lineWidth = Math.max(1, 1.25 * hr);
        c.setLineDash(dash.map((d) => d * hr));
        c.beginPath();
        c.moveTo(Math.max(0, start) * hr, y * vr);
        c.lineTo(width * hr, y * vr);
        c.stroke();
        c.setLineDash([]);
      };
      const inv = node.invalidation;
      const down = color('--down');
      line(inv.p, down, [6, 4]);
      this.levelTag(c, `Invalid ${inv.side} ${shortP(inv.p)}`, inv.p, down, hr, vr);
      if (node.kill_next.p !== inv.p) {
        line(node.kill_next.p, hexA(down, 0.6), [2, 3]);
        this.levelTag(c, `Kill ${node.kill_next.side} ${shortP(node.kill_next.p)}`, node.kill_next.p, hexA(down, 0.6), hr, vr);
      }
      if (node.zone.length) {
        const ps = node.zone.map((l) => l.p);
        const mid = (Math.max(...ps) + Math.min(...ps)) / 2;
        this.levelTag(c, `Zone ${shortP(Math.min(...ps))}-${shortP(Math.max(...ps))}`, mid, color('--line-strong'), hr, vr);
      }
      if (node.next.targets.length) {
        const ps = node.next.targets.map((l) => l.p);
        const mid = (Math.max(...ps) + Math.min(...ps)) / 2;
        const col = node.next.dir === 'up' ? color('--up') : color('--down');
        this.levelTag(c, `Next ${shortP(Math.min(...ps))}-${shortP(Math.max(...ps))}`, mid, col, hr, vr);
      }
    }
  }

  // --- panel ---

  function crossLine(cr) {
    const s = cr.split;
    if (cr.shared) {
      const first = cr.shared.first != null ? `, first ${px(cr.shared.first)}` : '';
      const guard = cr.shared.guard != null ? `, while ${cr.shared.d > 0 ? 'above' : 'below'} ${px(cr.shared.guard)}` : '';
      return `<span class="cp-shared">All ${cr.shared.n} kept expect ${cr.shared.dir} next${first}${guard}</span>`;
    }
    const part = (n, way, f) => (n ? `${n} ${way}${f != null ? ` (first ${px(f)})` : ''}` : `0 ${way}`);
    return `No shared move: ${part(s.up, 'up', s.ups_first)}, ${part(s.down, 'down', s.downs_first)}`;
  }

  function ysLine(cr) {
    const nearest = (side) => cr.ys.filter((y) => y.side === side).sort((a, b) => (side === 'above' ? a.price - b.price : b.price - a.price))[0];
    const piece = (y, word) => (y ? `${word} ${px(y.price)} kills ${y.kills.length} of ${y.kills.length + y.survive.length}` : '');
    return [piece(nearest('above'), 'Above'), piece(nearest('below'), 'Below')].filter(Boolean).join(' · ');
  }

  const AXES = ['price', 'time', 'structure'];

  /** The three sub-scores, the failing one marked: "price 0.66 · time 0.20 · structure 0.55". */
  function axesLine(n) {
    return AXES.map((a) => {
      const v = n.fit.axes[a];
      return `<span class="${v <= 0.25 ? 'cp-fail' : ''}">${a} ${num(v)}</span>`;
    }).join(' · ');
  }

  function legsLine(n) {
    if (!n.legs.length) return 'none finished yet';
    return n.legs.map((g) => {
      const ratio = g.x != null ? `, ${g.x} x ${WAVE(g.of)}` : '';
      return `<span class="${g.bad ? 'cp-fail' : ''}">${esc(WAVE(g.to))} ${g.text}${ratio}</span>`;
    }).join('; ');
  }

  function targetLine(n) {
    const ps = n.zone.map((l) => l.p);
    const where = ps.length ? `${px(Math.min(...ps))} to ${px(Math.max(...ps))}` : 'no price zone yet';
    return `${where}, ${esc(n.window_text)}`;
  }

  function oddsText(o) {
    return `${o.dir} to ${px(o.target)} (${esc(o.pull)}) before ${px(o.stop)}: ${pct(o.p)} within ${o.h_bars} bars (${o.h_src === 'window' ? 'its time window' : 'fixed horizon'}), ${pct(o.p_nolimit)} no limit, R:R ${o.rr.toFixed(2)}`;
  }

  function whyBlock(n) {
    const rows = AXES.map((a) => {
      const items = n.fit.reasons.filter((r) => r.axis === a && r.note);
      const line = (r) => `<li class="${r.f < 0.3 && r.counted ? 'cp-fail' : ''}">${esc(r.note)} <span class="cp-sec-id">[${esc(r.sec)}]</span></li>`;
      return `<div class="cp-axis"><b>${a} ${num(n.fit.axes[a])}</b><ul>${items.map(line).join('') || '<li>nothing judged yet: it stays at the prior</li>'}</ul></div>`;
    });
    return rows.join('');
  }

  function moreBlock(n) {
    const row = (k, v) => `<div><span class="k">${k}</span>${v}</div>`;
    const zone = n.zone.length ? n.zone.map((l) => `${px(l.p)} (${esc(l.pull)})`).join(', ') : 'none yet';
    const times = n.window ? n.window.levels.map((t) => `${EW.fmtMinute(t.t * 1000).slice(0, 10)} (${t.k})`).join(', ') : 'none';
    const labels = n.labels.map((l) => `${esc(l.l)} ${EW.fmtMinute(l.t * 1000).slice(0, n.tf === '1d' ? 10 : 16)} ${px(l.p)}`).join(' | ');
    const kills = n.kills.map((k) => `${k.side} ${px(k.p)}: ${esc(k.note)}`).join('; ');
    return [
      row('Labels', labels),
      row('Zone', zone),
      row('Time levels', `${times}${n.window ? `, ${esc(n.window.tool)} ${esc(n.window.pull)}, base ${esc(n.window.base)} ${esc(n.window.base_text)}` : ''}`),
      row('Next', esc(n.next.text)),
      row('Kills', kills),
      n.odds.slice(1).map((o) => row(`Odds, ${o.name}`, oddsText(o))).join(''),
      chain(n).slice(0, -1).map((p) => row(`${TF_NAME[p.tf]} labels`, p.labels.map((l) => `${esc(labelText(l.l, p.depth))} ${px(l.p)} ${EW.fmtDate(at(l) * 1000)}`).join(' | '))).join(''),
    ].join('');
  }

  /** One line per finished wave whose inside shows a 5, with the 5 spelled out. */
  function insideLines(rows, pad = '') {
    return rows.filter(hasFive).map((r) => {
      const labels = r.labels.slice(1).map((l) => `${WAVE(l.l).replace(/^W/, '')} ${px(l.p)}`).join(' · ');
      return `<div>${pad}<span class="k">Inside ${esc(WAVE(r.wave))}</span>${esc(r.name)}: ${labels}</div>${insideLines(r.inside, `${pad}&nbsp;&nbsp;`)}`;
    }).join('');
  }

  /** Each wave against what it must hold (rules/counts.yaml, inside): "W1 5 ok (1H) · W2 3 ok · W5 5 unreadable". */
  function insideRuleLine(n) {
    if (!n.inside_rule.length) return '';
    const word = (v) => `<span class="cp-in cp-in-${v.state}${v.found === '3 or 5' ? ' cp-in-both' : ''}" title="${esc(v.note)}">${esc(v.text)}</span>`;
    return `<div><span class="k">Inside</span>${n.inside_rule.map(word).join(' · ')}</div>`;
  }

  function alikeLine(n) {
    if (!n.alike?.length) return '';
    const row = (k, v) => `<div><span class="k">${k}</span>${v}</div>`;
    return row('Same move', n.alike.map((a) => `${esc(a.name)} in ${esc(WAVE(a.wave))} ${num(a.score)}`).join(' · '));
  }

  function detail(n) {
    const row = (k, v) => `<div><span class="k">${k}</span>${v}</div>`;
    const o = n.odds[0];
    const path = chain(n);
    return [
      path.length > 1 ? row('Part of', path.slice(0, -1).map((p) => esc(waveTag(p).split(' running')[0])).join(' &gt; ')) : '',
      row('Fit', `<b class="cp-fit-big">${num(n.fit.score)}</b> ${axesLine(n)}`),
      row('Legs', legsLine(n)),
      insideRuleLine(n),
      insideLines(shownInside(n)),
      alikeLine(n),
      row('Running', `${esc(n.wave.name)} ${n.wave.dir} from ${px(n.wave.start.p)}, so far ${px(n.wave.so_far)}`),
      row('Target', targetLine(n)),
      n.crosshair_hit ? row('Crosshair', `the extreme so far sits on one (${esc(n.crosshair_hit.pull)})`) : '',
      n.fit.fails.length ? `<div class="cp-fail"><span class="k">Missed</span>${esc(n.fit.fails.join(', '))}: ranks lower, kills nothing</div>` : '',
      row('Invalid', `${n.invalidation.side} ${px(n.invalidation.p)}`),
      n.kill_next.p !== n.invalidation.p ? row('Nearest kill', `${n.kill_next.side} ${px(n.kill_next.p)}, ${pct(n.kill_next.dist)} away`) : '',
      o ? row(`Odds, ${o.name}`, oddsText(o)) : row('Odds', 'none: no target ahead of price with an invalidation behind it'),
      n.no_child ? row('One frame down', 'no legal parse of the running wave') : '',
      `<details class="cp-more" data-open="why"${ui.why ? ' open' : ''}><summary>Why this score</summary>${whyBlock(n)}</details>`,
      `<details class="cp-more" data-open="more"${ui.more ? ' open' : ''}><summary>All levels</summary>${moreBlock(n)}</details>`,
    ].join('');
  }

  /** His premise and its own levels, above everything the engine says. */
  function premiseBlock() {
    const pm = data.premise;
    if (!pm) return '';
    const row = (k, v) => `<div><span class="k">${k}</span>${v}</div>`;
    if (!pm.applied) return `<section class="cp-premise"><p>${esc(pm.statement)}</p><div class="cp-fail">${esc(pm.status_note)}</div></section>`;
    const w = pm.window;
    const state = pm.status === 'review' ? `<div class="cp-fail">${esc(pm.status_note)}</div>` : '';
    const pulls = pm.pulls.map((x) => `${x.k} at ${px(x.linear)} (log ${px(x.log)})`).join(', ');
    const r = pm.ratios;
    const leg = (name) => `${name} ${r[name].days}d, ${r[name].time} x ${r[name].of}`;
    const broken = [...new Set(pm.rule_notes.flatMap((x) => x.broken.map((b) => b.note)))];
    const clean = pm.rule_notes.filter((x) => !x.broken.length).length;
    const notes = (broken.length
      ? row('Hard rules', `<span class="cp-fail">${clean} of ${pm.rule_notes.length} pivot choices pass. ${esc(broken.join('; '))}.</span> Given by him, so nothing is killed`)
      : '') + (pm.time_notes?.length
      ? row('Time minimum', `${esc(pm.time_notes.join('; '))}. A strong guideline: ranks lower, kills nothing; the book reads it as a lower degree or wrong pivots (FIB-T3)`)
      : '');
    return `<section class="cp-premise"><p>${esc(pm.statement)}. Given by ${esc(pm.owner)}, not the engine's.</p>${state}`
      + row('Invalid', `below ${px(pm.invalid_below.p)}, the origin of the 5`)
      + row('New high', `above ${px(pm.review_above.p)} under review, above ${px(pm.broken_above.p)} broken`)
      + row('So far', `${num(w.x)} x the five; minimum ${w.levels[0].str}, full length ${w.hi_str}`)
      + `<details class="cp-more" data-open="pm"${ui.pm ? ' open' : ''}><summary>Its levels</summary>`
      + row('Pull 0-5', pulls)
      + row('His five', `${leg('W2')}; ${leg('W3')}; ${leg('W4')}; ${leg('W5')}`)
      + row('New high', `${esc(pm.review_above.note)}. At ${px(pm.broken_above.p)}, ${esc(pm.broken_above.note)}`)
      + notes
      + `<div class="cp-sec-id">${esc(pm.version)}, in rules/premise.yaml: his to edit</div></details></section>`;
  }

  /** How many readings the inside rule killed on each frame, and why. */
  function killBlock(t) {
    const rows = t.levels.filter((lv) => lv.stats?.inside).map((lv) => {
      const i = lv.stats.inside;
      const why = Object.entries(i.by).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => `${esc(k)}: ${v}`).join(', ');
      return `<div class="cp-cross"><span class="cp-tf">${TF_NAME[lv.tf]}</span><span>${i.killed} of ${i.read} readings died${why ? `: ${why}` : ''}</span></div>`;
    }).join('');
    return `<details class="cp-more" data-open="kills"${ui.kills ? ' open' : ''}><summary>Killed by what is inside</summary>${rows}<div class="cp-sec-id">A wave must hold what its label says. It dies only when readable; too short, or a 3 and a 5 too close to tell, is held. The running wave is never killed.</div></details>`;
  }

  /** The one-line state of a timeframe: "up next, first 81,576, while above 76,232". */
  function crossShort(cr) {
    const s = cr.shared;
    if (!s) return `no shared move: ${cr.split.up} up, ${cr.split.down} down`;
    const first = s.first != null ? `, first ${px(s.first)}` : '';
    const guard = s.guard != null ? `, while ${s.d > 0 ? 'above' : 'below'} ${px(s.guard)}` : '';
    return `${s.dir} next${first}${guard}`;
  }

  function crossBlock(t) {
    return t.levels.map((lv) => {
      const cr = lv.crossroads;
      const ys = ysLine(cr);
      return `<div class="cp-cross"><span class="cp-tf">${TF_NAME[lv.tf]}</span><span>${crossLine(cr)}${ys ? `<br><span class="cp-ys">${ys}</span>` : ''}</span></div>`;
    }).join('');
  }

  function aboutBlock(t) {
    const stats = t.levels[0].stats;
    return `<p>${esc(VENUES[data.venue].label)}, as of ${esc(data.as_of_str)} UTC, close ${px(data.price)}. Rules ${esc(data.rules_version)}.</p>`
      + '<p class="cp-note">Ranked by rulebook fit on three axes, not by win chance. Odds are volatility only. Fib time is the book\'s filter, not a proven edge.</p>'
      + `<p>${stats.legal} legal readings in ${stats.states} states at the root${data.premise?.applied ? ', all of them the correction since the red line' : ''}. Top ${t.levels[0].nodes.length} kept; other or unclear: ${pct(stats.other_share)} of fit.</p>`
      + killBlock(t)
      + '<p class="cp-sec-id">Keys in the list: up and down move, left and right collapse and expand, Enter selects, i shows more.</p>';
  }

  // --- popover: one at a time, on the page rather than in the panel, so that it can leave the panel's scroll box ---

  const pop = { key: null, pinned: false, el: null, keyboard: false, openTimer: 0, closeTimer: 0 };

  /** The small "show more" button. key: a node's id, or premise, cross, about. */
  const infoBtn = (key, label, tab = 0) => `<button type="button" class="cp-i" data-pop="${key}" aria-label="Show more: ${esc(label)}" aria-haspopup="dialog" aria-expanded="false" tabindex="${tab}">i</button>`;
  const iconOf = (key) => $('counts-panel').querySelector(`.cp-i[data-pop="${key}"]`);

  function popContent(key) {
    const t = tree();
    if (key === 'premise') return { head: 'Premise', body: premiseBlock() };
    if (key === 'cross') return { head: 'Crossroads and Y\'s', body: crossBlock(t) };
    if (key === 'about') return { head: 'About these counts', body: aboutBlock(t) };
    const n = byId.get(key);
    if (!n) return null;
    return { head: `<span class="cp-chip" style="${chipVars(n)}">${TF_NAME[n.tf]}</span> ${esc(n.title)}`, body: detail(n) };
  }

  function openPop(key, pinned, keyboard = false) {
    const c = popContent(key);
    if (!c) return;
    clearTimeout(pop.openTimer);
    clearTimeout(pop.closeTimer);
    if (!pop.el) {
      pop.el = document.createElement('div');
      pop.el.className = 'cp-pop';
      pop.el.setAttribute('role', 'dialog');
      document.body.append(pop.el);
    }
    const scroller = pop.key === key ? pop.el.scrollTop : 0;
    pop.key = key;
    pop.pinned = pinned;
    pop.keyboard = keyboard;
    pop.el.hidden = false;
    pop.el.dataset.pinned = pinned;
    pop.el.setAttribute('aria-label', key.includes('.') ? 'Details of this count' : 'More');
    pop.el.innerHTML = `<div class="cp-pop-head"><div>${c.head}</div><button type="button" class="cp-pop-x" aria-label="Close">×</button></div><div class="cp-pop-body">${c.body}</div>`;
    for (const d of pop.el.querySelectorAll('details.cp-more')) {
      d.addEventListener('toggle', () => { ui[d.dataset.open] = d.open; placePop(); });
    }
    pop.el.querySelector('.cp-pop-x').addEventListener('click', () => closePop(true));
    markIcons();
    placePop();
    pop.el.scrollTop = scroller;
    if (keyboard) pop.el.querySelector('.cp-pop-x').focus({ preventScroll: true });
  }

  function closePop(giveFocusBack = false) {
    clearTimeout(pop.openTimer);
    clearTimeout(pop.closeTimer);
    if (!pop.key) return;
    const key = pop.key;
    pop.key = null;
    pop.pinned = false;
    pop.el.hidden = true;
    markIcons();
    if (giveFocusBack) iconOf(key)?.focus({ preventScroll: true });
  }

  function markIcons() {
    for (const b of $('counts-panel').querySelectorAll('.cp-i')) {
      const mine = b.dataset.pop === pop.key;
      b.setAttribute('aria-expanded', String(mine));
      b.dataset.pinned = mine && pop.pinned;
    }
  }

  /** Beside the panel when there is room for it, so it covers no row. Otherwise in the largest gap the anchor and the chosen row leave. */
  function placePop() {
    if (!pop.key) return;
    const el = pop.el;
    const M = 8;
    const panel = $('counts-panel').getBoundingClientRect();
    const a = iconOf(pop.key)?.closest('.cp-row, .cp-line')?.getBoundingClientRect() ?? { top: panel.top, bottom: panel.top };
    const sel = $('counts-panel').querySelector('.cp-row[aria-selected="true"]')?.getBoundingClientRect();
    el.dataset.mode = 'beside';
    el.style.left = el.style.right = el.style.bottom = el.style.width = el.style.top = '';
    if (narrow()) { // the list stays in view under it: the sheet takes the chart's half of the screen
      el.dataset.mode = 'sheet';
      el.style.left = `${M}px`;
      el.style.width = `${innerWidth - 2 * M}px`;
      el.style.top = `${M}px`;
      el.style.maxHeight = `${Math.max(180, panel.top - 2 * M)}px`;
      return;
    }
    const room = panel.left - 2 * M;
    if (room >= 320) {
      const w = Math.min(460, room);
      el.style.width = `${w}px`;
      el.style.left = `${panel.left - w - 4}px`;
      el.style.maxHeight = `${innerHeight - 2 * M}px`;
      el.style.top = `${Math.max(M, Math.min(a.top, innerHeight - M - el.offsetHeight))}px`;
      return;
    }
    const blocks = [a, sel].filter(Boolean).sort((p, q) => p.top - q.top);
    const gaps = [];
    let from = M;
    for (const b of blocks) {
      gaps.push([from, b.top - 4]);
      from = Math.max(from, b.bottom + 4);
    }
    gaps.push([from, innerHeight - M]);
    const [top, bottom] = gaps.reduce((best, g) => (g[1] - g[0] > best[1] - best[0] ? g : best));
    const w = Math.min(460, innerWidth - 2 * M);
    el.style.width = `${w}px`;
    el.style.left = `${Math.max(M, panel.right - w - 4)}px`;
    el.style.maxHeight = `${bottom - top}px`;
    el.style.top = `${Math.max(top, Math.min(a.bottom + 4, bottom - el.offsetHeight))}px`;
  }

  /** Hover opens only from the icon: a popover that came up while reaching for a row would cover the chart he is reading.
   * The way across the row to the popover, and the popover itself, keep it open. */
  function onHover(e) {
    if (e.pointerType === 'touch' || !e.target.closest) return;
    const icon = e.target.closest('.cp-i');
    if (icon && !pop.pinned) {
      clearTimeout(pop.closeTimer);
      clearTimeout(pop.openTimer);
      if (pop.key !== icon.dataset.pop) pop.openTimer = setTimeout(() => openPop(icon.dataset.pop, false), 110);
      return;
    }
    clearTimeout(pop.openTimer);
    if (!pop.key || pop.pinned) return;
    const ownRow = iconOf(pop.key)?.closest('.cp-row, .cp-line');
    if (e.target.closest('.cp-pop') || (ownRow && ownRow.contains(e.target))) {
      clearTimeout(pop.closeTimer);
      return;
    }
    clearTimeout(pop.closeTimer);
    pop.closeTimer = setTimeout(() => closePop(), 280);
  }

  function onPointerDown(e) {
    if (!pop.key || !e.target.closest) return;
    if (e.target.closest('.cp-pop')) { // working inside it: it stays
      pop.pinned = true;
      pop.el.dataset.pinned = true;
      markIcons();
      return;
    }
    if (!e.target.closest('.cp-i')) closePop();
  }

  // --- the list ---

  const isClosed = (id) => ui.closed.has(id);
  const chipVars = (n) => `--c:${degreeColor(n.depth)};--t:${n.depth >= 3 ? '#fff' : color('--bg')}`;

  /** The rows on show, in order. */
  function visibleRows() {
    const out = [];
    const walk = (n) => {
      out.push(n);
      if (!isClosed(n.id)) for (const id of n.children) walk(byId.get(id));
    };
    for (const n of tree().levels[0].nodes) walk(n);
    return out;
  }

  function rowHtml(n, path, pos, size, cursor) {
    const sel = n.id === ui.node;
    const onPath = !sel && path.has(n.id);
    const kids = n.children.length > 0;
    const hides = kids && isClosed(n.id) && path.has(n.id) && !sel; // the choice sits inside this collapsed row
    const tri = kids ? `<span class="cp-tri" data-open="${!isClosed(n.id)}" aria-hidden="true"></span>` : '<span class="cp-tri-none"></span>';
    return `<div class="cp-row" role="treeitem" data-id="${n.id}" aria-level="${n.depth + 1}" aria-posinset="${pos}" aria-setsize="${size}" aria-selected="${sel}"`
      + `${kids ? ` aria-expanded="${!isClosed(n.id)}"` : ''}${onPath ? ' data-path="true" aria-current="true"' : ''} tabindex="${cursor === n.id ? 0 : -1}" style="--indent:${n.depth};--c:${degreeColor(n.depth)}">`
      + `<span class="cp-guides"></span>${tri}<span class="cp-chip" style="${chipVars(n)}">${TF_NAME[n.tf]}</span>`
      + `<span class="cp-name" title="${esc(n.title)}">${esc(n.short)}</span>${hides ? `<span class="cp-holds" title="The chosen count is inside this row">●</span>` : ''}`
      + `<span class="cp-fit">${num(n.fit.score)}</span>${infoBtn(n.id, `${TF_NAME[n.tf]} ${n.short}`, cursor === n.id ? 0 : -1)}</div>`;
  }

  /** Scroll the panel, and only the panel, so the row is not under the pinned line. */
  function intoView(row) {
    const host = $('counts-panel');
    const box = host.getBoundingClientRect();
    const r = row.getBoundingClientRect();
    const pin = host.querySelector('.cp-pin')?.offsetHeight ?? 0;
    if (r.top < box.top + pin) host.scrollTop -= box.top + pin - r.top;
    else if (r.bottom > box.bottom) host.scrollTop += r.bottom - box.bottom;
  }

  function render() {
    const host = $('counts-panel');
    const t = tree();
    const stats = t.levels[0].stats;
    const hadFocus = document.activeElement?.closest?.('.cp-row')?.dataset.id ?? null;
    const off = !visibleVenue() ? `<p class="cp-note">These counts are for ${esc(VENUES[data.venue].label)}. Pick a count to switch to it.</p>` : '';
    const cross = t.levels.map((lv) => `<div class="cp-crossline"><span class="cp-tf">${TF_NAME[lv.tf]}</span><span class="cp-crosstext">${crossShort(lv.crossroads)}</span></div>`).join('');
    const selected = ui.node ? byId.get(ui.node) : null;
    const path = new Set(selected ? chain(selected).map((n) => n.id) : []);
    const shown = visibleRows();
    const wanted = ui.cursor ?? ui.node;
    const cursor = shown.some((n) => n.id === wanted) ? wanted : shown[0]?.id; // the one stop of the list in the tab order
    const rows = shown.map((n, i) => rowHtml(n, path, i + 1, shown.length, cursor)).join('');
    const scroller = host.scrollTop;
    const pm = data.premise;
    const line = pm ? `<div class="cp-pin cp-line"><span class="cp-pin-text"><span class="cp-pin-k">Premise</span> ${esc(pm.statement.split(';')[0])}</span>${infoBtn('premise', 'the premise')}</div>` : '';
    host.innerHTML = `${line}<div class="cp-head"><div class="cp-title cp-line"><b>Counts</b><div class="seg" id="seg-count-root" role="group" aria-label="Root timeframe"></div>${infoBtn('about', 'about these counts')}</div>`
      + `<div class="cp-asof">${esc(VENUES[data.venue].label)}, as of ${esc(data.as_of_str)} UTC, close ${px(data.price)}</div>${off}</div>`
      + `<section class="cp-crossroads cp-line"><div class="cp-crosslines">${cross}</div>${infoBtn('cross', 'crossroads and Y\'s')}</section>`
      + `<section class="cp-list"><div class="cp-listbar"><span class="cp-listbar-k">Chart zoom</span><div class="seg" id="seg-count-view" role="group" aria-label="Chart zoom"></div></div>`
      + `<div class="cp-cols" aria-hidden="true"><span>Count</span><span class="cp-cols-fit" title="Rulebook fit, not a win chance">Fit</span></div>`
      + `<div class="cp-tree" role="tree" aria-label="Wave counts, largest degree first">${rows}</div>`
      + `<p class="cp-foot">Top ${t.levels[0].nodes.length} of ${stats.legal} legal readings at the root. Other or unclear: ${pct(stats.other_share)} of fit. Fit is rulebook fit, not a win chance.</p></section>`;
    host.scrollTop = scroller;
    if (scrollToPick) {
      scrollToPick = false;
      const row = host.querySelector('.cp-row[aria-selected="true"]');
      if (row) intoView(row);
    }
    if (hadFocus) host.querySelector(`.cp-row[data-id="${hadFocus}"]`)?.focus({ preventScroll: true });
    const seg = $('seg-count-root');
    buildSeg(seg, Object.fromEntries(Object.keys(data.trees).map((r) => [r, `${TF_NAME[r]} root`])), (r) => {
      closePop();
      ui.root = r;
      ui.node = null;
      ui.cursor = null;
      index();
      if (autoPick() && bars) zoomTo(byId.get(ui.node));
      render();
      changed();
    });
    markSeg(seg, ui.root);
    const views = $('seg-count-view');
    buildSeg(views, { chain: 'Whole chain', focus: 'This count' }, (v) => {
      ui.view = v;
      keep();
      const n = ui.node ? byId.get(ui.node) : null;
      if (n && bars && visibleVenue()) zoomTo(n);
      render();
      syncControls();
      primitive.requestUpdate?.();
    });
    markSeg(views, ui.view);
    markIcons();
    placePop();
  }

  /** Open what leads to a row: a row chosen from elsewhere must not stay hidden, or the list and the chart would disagree. */
  function reveal(id) {
    const n = byId.get(id);
    if (n) for (const p of chain(n).slice(0, -1)) ui.closed.delete(p.id);
  }

  function setClosed(id, closed) {
    if (closed) ui.closed.add(id);
    else ui.closed.delete(id);
    stored.closed = [...ui.closed];
    keep();
    render();
  }

  function focusRow(id) {
    ui.cursor = id;
    const host = $('counts-panel');
    for (const r of host.querySelectorAll('.cp-row')) r.tabIndex = r.dataset.id === id ? 0 : -1;
    for (const b of host.querySelectorAll('.cp-row .cp-i')) b.tabIndex = b.dataset.pop === id ? 0 : -1;
    const row = host.querySelector(`.cp-row[data-id="${id}"]`);
    if (row) {
      row.focus({ preventScroll: true });
      intoView(row);
    }
  }

  function onListClick(e) {
    const icon = e.target.closest('.cp-i');
    if (icon) {
      const key = icon.dataset.pop;
      if (pop.key === key && pop.pinned) closePop();
      else openPop(key, true, e.detail === 0); // detail 0: Enter or Space on the button
      return;
    }
    const row = e.target.closest('.cp-row');
    if (!row) return;
    const id = row.dataset.id;
    if (e.target.closest('.cp-tri')) {
      setClosed(id, !isClosed(id));
      return;
    }
    ui.cursor = id;
    pick(id);
  }

  function onListKey(e) {
    const row = e.target.closest?.('.cp-row');
    if (!row || e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.target.closest('.cp-i') && (e.key === 'Enter' || e.key === ' ')) return; // the button's own
    const id = row.dataset.id;
    const n = byId.get(id);
    const shown = visibleRows();
    const i = shown.findIndex((x) => x.id === id);
    const go = (x) => { if (x) focusRow(x.id); };
    switch (e.key) {
      case 'ArrowDown': go(shown[i + 1]); break;
      case 'ArrowUp': go(shown[i - 1]); break;
      case 'Home': go(shown[0]); break;
      case 'End': go(shown[shown.length - 1]); break;
      case 'ArrowRight':
        if (n.children.length && isClosed(id)) setClosed(id, false);
        else if (n.children.length) go(byId.get(n.children[0]));
        break;
      case 'ArrowLeft':
        if (n.children.length && !isClosed(id)) setClosed(id, true);
        else if (n.parent) go(byId.get(n.parent));
        break;
      case 'Enter':
      case ' ':
        ui.cursor = id;
        pick(id);
        break;
      case 'i':
        if (pop.key === id && pop.pinned) closePop(true);
        else openPop(id, true, true);
        break;
      default:
        return;
    }
    e.preventDefault();
  }

  /** The count drawn when none is chosen, or when the chosen one belongs to another timeframe: stay on the chosen
   * count's branch (its ancestor or best-ranked descendant at this timeframe), else the best-ranked count here. */
  function autoNode() {
    const want = state.tf;
    const lv = tree().levels.find((l) => chartTf(l.tf) === want && l.nodes.length);
    if (!lv) return null;
    const cur = ui.node ? byId.get(ui.node) : null;
    if (cur) {
      const up = chain(cur).find((n) => chartTf(n.tf) === want);
      if (up) return up.id;
      const queue = [cur];
      while (queue.length) {
        const n = queue.shift();
        if (chartTf(n.tf) === want) return n.id;
        for (const id of n.children) queue.push(byId.get(id));
      }
    }
    return lv.nodes[0].id;
  }

  /** Draw something by default: returns true when it changed the chosen count. */
  function autoPick() {
    if (!ui.on || !visibleVenue()) return false;
    const cur = ui.node ? byId.get(ui.node) : null;
    if (cur && chartTf(cur.tf) === state.tf) return false;
    const id = autoNode();
    if (!id || id === ui.node) return false;
    ui.node = id;
    ui.cursor = id;
    reveal(id);
    scrollToPick = true;
    return true;
  }

  function index() {
    byId = new Map(tree().levels.flatMap((lv) => lv.nodes.map((n) => [n.id, n])));
    if (ui.node && !byId.has(ui.node)) ui.node = null;
  }

  /** Bars newer than the published files, so that the chart reaches the count's as-of time. */
  function addRecentBars() {
    if (!bars || !visibleVenue() || bars.withRecent) return;
    bars.withRecent = true;
    const rows = data.recent_bars[state.tf] ?? [];
    for (const [t, o, h, l, cl, v] of rows) {
      if (t <= bars.time[bars.n - 1]) continue;
      bars.time.push(t);
      bars.open.push(o);
      bars.high.push(h);
      bars.low.push(l);
      bars.close.push(cl);
      bars.volume.push(v);
      indexByTime.set(t, bars.n);
      bars.n += 1;
      candles.update({ time: t, open: o, high: h, low: l, close: cl });
      volume.update({ time: t, value: v });
    }
    renderReadout(bars.n - 1);
  }

  /** The foot line reads the published files: say so when the private bars reach further. */
  function footNote() {
    if (!bars || !visibleVenue() || !ui.on || !data.recent_bars[state.tf]?.length) return;
    $('foot-until').textContent = `Data until the ${TIMEFRAMES[state.tf]} bar opening ${EW.fmtMinute(bars.time[bars.n - 1] * 1000)}, the last ones from the private counts file. All times UTC.`;
  }

  /** The visible range that starts at bar `first` and leaves room for the boxes and tags on the right. */
  function viewFrom(first, node) {
    const last = bars.n - 1;
    const span = Math.max(30, last - first);
    const left = Math.min(first - span * 0.06, last - 30);
    const room = Math.max(8, span * (narrow() ? 0.6 : 0.25));
    // and for the time window, unless it is so far ahead that it would crush the count: then its band runs off the edge
    const own = Math.max(30, last - logical(at(node.labels[0])));
    const due = node.window ? logical(node.window.hi) + own * 0.04 - last : 0;
    return { from: left, to: last + Math.max(room, Math.min(due, own * 0.9)) };
  }

  /** Whole chain: the widest parent to start from at which the chosen count still has room for its labels, about 24 px a leg.
   * A parent's whole structure first, then the running wave that holds the child, one degree at a time. What this leaves out
   * becomes edge markers. */
  function chainStart(node) {
    const own = logical(at(node.labels[0]));
    const last = bars.n - 1;
    const width = chart.timeScale().width();
    const need = node.labels.length * (narrow() ? 18 : 24); // its labels make as many legs, with the running one
    for (const n of chain(node).slice(0, -1)) {
      for (const t of [at(n.labels[0]), at(n.wave.start)]) {
        const first = Math.max(0, logical(t));
        if (first >= own) continue;
        const v = viewFrom(first, node);
        if ((last - own) * width / (v.to - v.from) >= need) return first;
      }
    }
    return own;
  }

  function zoomTo(node) {
    const first = ui.view === 'chain' ? chainStart(node) : logical(at(node.labels[0]));
    chart.timeScale().setVisibleLogicalRange(viewFrom(first, node));
  }

  /** Zoom now, and again if the panel's layout narrows the chart just after: its resize keeps the right edge and would cut off the count's start. */
  function settleZoom(node) {
    const width = chart.timeScale().width();
    zoomTo(node);
    for (const wait of [120, 400]) {
      setTimeout(() => {
        if (ui.node === node.id && bars && chart.timeScale().width() !== width) {
          zoomTo(node);
          primitive.requestUpdate?.();
        }
      }, wait);
    }
  }

  function pick(id) {
    const node = byId.get(id);
    if (!node) return;
    ui.node = id;
    reveal(id);
    const tf = chartTf(node.tf);
    render();
    if (state.tf !== tf || state.venue !== data.venue) {
      state.tf = tf;
      state.venue = data.venue;
      ui.pendingZoom = true;
      load();
      return;
    }
    zoomTo(node);
    syncControls();
    primitive.requestUpdate?.();
  }

  function changed() {
    markSeg($('seg-counts'), ui.on ? 'on' : '');
    $('counts-panel').hidden = !ui.on;
    $('chart-wrap').classList.toggle('with-counts', ui.on);
    syncControls();
    primitive.requestUpdate?.();
  }

  globalThis.EWCounts = {
    addParams(q) {
      if (!data || !ui.on) return;
      q.set('counts', '1');
      if (ui.root !== data.default_root) q.set('croot', ui.root);
      if (ui.node) q.set('cn', ui.node);
      if (ui.view !== 'chain') q.set('cview', ui.view);
    },
    /** What the chart draws right now, for tools/shots_counts.mjs: each level, each label, on the chart or as a marker. */
    drawn() {
      const node = primitive.selected();
      if (!node) return { node: null, path: [], labels: [] };
      const width = chart.timeScale().width();
      const markers = primitive.edgeRows(chain(node));
      return {
        node: node.id,
        path: chain(node).map((n) => n.id),
        labels: chain(node).flatMap((n) => n.labels.map((l) => {
          const x = xAt(at(l));
          const m = markers.find((r) => r.l === l || r.also.includes(l));
          return { tf: n.tf, l: l.l, onChart: x != null && x >= 0 && x <= width, marker: Boolean(m), text: m?.text ?? '' };
        })),
      };
    },
    onBars() {
      if (!data) return;
      if (ui.on) {
        addRecentBars();
        footNote();
        if (autoPick()) {
          ui.pendingZoom = true;
          syncControls();
        }
      }
      const node = ui.node ? byId.get(ui.node) : null;
      if (ui.on && ui.pendingZoom && node) {
        ui.pendingZoom = false;
        scrollToPick = true;
        settleZoom(node);
      }
      if (ui.on) render();
      primitive.requestUpdate?.();
    },
  };

  /** Everything open on a desktop. A phone starts with the other roots shut: its half-screen list cannot hold twelve rows. */
  function firstClosed() {
    if (Array.isArray(stored.closed)) return new Set(stored.closed);
    if (!narrow()) return new Set();
    const rootOf = (id) => (id ? id.split('.').slice(0, 2).join('.') : null);
    return new Set(Object.values(data.trees).flatMap((t) => t.levels[0].nodes.slice(ui.node && rootOf(ui.node) ? 0 : 1).map((n) => n.id).filter((id) => id !== rootOf(ui.node))));
  }

  async function start() {
    let file;
    try {
      const r = await fetch('data/local/counts.json', { cache: 'no-cache' });
      if (!r.ok) return;
      file = await r.json();
    } catch {
      return; // no data, no toggle
    }
    if (file.format !== 'ewave-counts-4') return;
    data = file;
    ui.root = data.trees[ui.root] ? ui.root : data.default_root;
    index();
    ui.closed = firstClosed();
    if (ui.node) reveal(ui.node);
    primitive = new Overlay();
    candles.attachPrimitive(primitive);
    const host = $('counts-panel');
    host.addEventListener('click', onListClick);
    host.addEventListener('keydown', onListKey);
    host.addEventListener('scroll', placePop, { passive: true });
    document.addEventListener('pointerover', onHover);
    document.addEventListener('pointerdown', onPointerDown, true);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && pop.key) closePop(true); });
    addEventListener('resize', () => { if (pop.key) placePop(); });
    const seg = $('seg-counts');
    buildSeg(seg, { on: 'Counts' }, () => {
      ui.on = !ui.on;
      closePop();
      if (ui.on) {
        addRecentBars();
        footNote();
        if (autoPick() && bars) ui.zoomAfterLayout = true;
        render();
      }
      changed();
      if (ui.zoomAfterLayout) {
        ui.zoomAfterLayout = false; // the panel narrows the chart first; zoom once it has resized
        setTimeout(() => { const n = byId.get(ui.node); if (n && bars) { zoomTo(n); primitive.requestUpdate?.(); } }, 80);
      }
    });
    seg.hidden = false;
    changed();
    if (ui.on) render();
    if (bars) {
      EWCounts.onBars();
      syncControls();
    }
  }

  start();
})();

/**
 * Cycles overlay for the chart page: market cycles from `ewave-cycles export`, drawn over any venue and timeframe.
 *
 * The data is private for now (site/data/local/ is gitignored), so on the public hosts this script does nothing at all:
 * it asks for no file, because a browser logs every 404 in its console whatever the page does with it.
 *
 * Series markers draw the hindsight lows, a series primitive draws everything else: live lows, translation labels,
 * failed cycles and the prediction boxes. Marks come from Bitstamp 1D; a day is a day on every venue.
 */
(() => {
  if (/(^|\.)yaga\.sh$|\.vercel\.app$/.test(location.hostname)) return;

  const LEVELS = {
    fouryear: { key: '4y', label: '4Y', name: '4-year', css: '--cycle-4y', size: 2, ring: 7 },
    weekly: { key: 'w', label: 'Weekly', name: 'weekly', css: '--cycle-w', size: 1.1, ring: 5 },
    daily: { key: 'd', label: 'Daily', name: 'daily', css: '--cycle-d', size: 0.5, ring: 3.5 },
  };
  const LAYERS = { h: 'Hindsight', l: 'Live', z: 'Zones', i: 'Info' };
  const TEXT_ZOOM = 1.2; // px per bar from which daily marks and labels have room for text
  const CROWDED = 0.12; // px per bar below which (the whole history on a phone) only the bigger marks fit

  const given = new URLSearchParams(location.search);
  const ui = {
    on: given.get('cycles') === '1',
    levels: new Set((given.get('clv') ?? '4y,w,d').split(',')),
    layers: new Set((given.get('cly') ?? (innerWidth < 600 ? 'h,l,z' : 'h,l,z,i')).split(',')), // a phone has no room for the text
  };
  const levelOn = (name) => ui.levels.has(LEVELS[name].key);

  let data = null;
  let markers = null;
  let primitive = null;

  const narrow = () => innerWidth < 600;
  const hexA = (hex, a) => `${hex}${Math.round(a * 255).toString(16).padStart(2, '0')}`;
  const levelColor = (name) => color(LEVELS[name].css);
  const money = (p) => `$${EW.fmtPrice(p)}`;
  const shortMoney = (p) => (p >= 1000 ? `$${(p / 1000).toFixed(1)}k` : `$${p.toFixed(0)}`);
  const day = (s) => EW.fmtDate(s * 1000);

  /** First index with bars.time[i] >= t. */
  function lowerBound(t) {
    let a = 0;
    let b = bars.n;
    while (a < b) {
      const m = (a + b) >> 1;
      if (bars.time[m] < t) a = m + 1;
      else b = m;
    }
    return a;
  }

  /** The bar that shows a day's low on the current timeframe; null if that day is not on this chart. */
  function barOfDay(t) {
    const a = lowerBound(t);
    if (a >= bars.n || bars.time[a] >= t + 86400) return null;
    let best = a;
    for (let i = a + 1; i < bars.n && bars.time[i] < t + 86400; i++) if (bars.low[i] < bars.low[best]) best = i;
    return best;
  }

  /** Any time, also past the data on either side, as a logical bar position. */
  function logicalOf(t) {
    const step = BAR_MINUTES[state.tf] * 60;
    if (t <= bars.time[0]) return (t - bars.time[0]) / step;
    if (t >= bars.time[bars.n - 1]) return bars.n - 1 + (t - bars.time[bars.n - 1]) / step;
    return lowerBound(t);
  }

  const xOf = (t) => chart.timeScale().logicalToCoordinate(logicalOf(t));
  const barSpacing = () => {
    const r = chart.timeScale().getVisibleLogicalRange();
    return r ? chart.timeScale().width() / Math.max(1, r.to - r.from) : 0;
  };

  function buildMarkers() {
    if (!ui.on || !ui.layers.has('h') || !bars) return [];
    const zoomed = barSpacing() >= TEXT_ZOOM;
    const crowded = barSpacing() < CROWDED;
    const seen = new Set();
    const out = [];
    for (const name of Object.keys(LEVELS)) { // top level first: a 4-year low is also weekly and daily, one mark says it all
      if (!levelOn(name) || (crowded && name === 'daily')) continue;
      const lv = LEVELS[name];
      const provisional = new Set(data.hindsight[name].cycles.filter((c) => c.status === 'provisional').map((c) => c.e));
      for (const low of data.hindsight[name].lows) {
        const i = barOfDay(low.t);
        if (i == null || seen.has(i)) continue;
        seen.add(i);
        const open = provisional.has(low.t); // no signal yet: drawn fainter, with a question mark
        const letter = name === 'fouryear' ? '4Y' : name === 'weekly' ? (crowded ? '' : 'W') : zoomed ? 'D' : '';
        const text = letter && open ? `${letter}?` : letter;
        out.push({ time: bars.time[i], position: 'belowBar', shape: 'arrowUp', color: hexA(levelColor(name), open ? 0.55 : 1), size: crowded && name === 'weekly' ? 0.5 : lv.size, text });
      }
    }
    return out.sort((a, b) => a.time - b.time);
  }

  /** Everything the primitive draws. Coordinates are worked out on each paint, so it follows zoom and scroll. */
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

    /** Keep a box in view when the price scale fits itself. Daily charts only: on 1H a box would crush the candles. */
    autoscaleInfo(from, to) {
      if (!ui.on || !ui.layers.has('z') || !bars || state.tf !== '1d') return null;
      let lo = Infinity;
      let hi = -Infinity;
      for (const z of data.zones) {
        if (!levelOn(z.level) || z.p_lo == null) continue;
        const a = logicalOf(z.t_from);
        const b = logicalOf(z.t_to);
        if (b < from || a > to) continue;
        lo = Math.min(lo, z.p_lo);
        hi = Math.max(hi, z.p_hi);
      }
      return lo < hi ? { priceRange: { minValue: lo, maxValue: hi } } : null;
    }

    drawBack(target) {
      if (!ui.on || !bars || !ui.layers.has('z')) return;
      target.useBitmapCoordinateSpace(({ context: c, bitmapSize, horizontalPixelRatio: hr, verticalPixelRatio: vr }) => {
        for (const o of data.overlaps) {
          if (!o.levels.every(levelOn)) continue;
          const a = xOf(o.t_from);
          const b = xOf(o.t_to);
          if (a == null || b == null) continue;
          c.fillStyle = hexA(color('--ink'), 0.07);
          c.fillRect(a * hr, 0, Math.max(1, (b - a)) * hr, bitmapSize.height);
        }
        for (const z of data.zones) {
          if (!levelOn(z.level)) continue;
          const a = xOf(z.t_from);
          const b = xOf(z.t_to);
          if (a == null || b == null) continue;
          const col = levelColor(z.level);
          const w = Math.max(2, b - a);
          if (z.p_lo == null) { // time only: a band over the whole height
            c.fillStyle = hexA(col, 0.1);
            c.fillRect(a * hr, 0, w * hr, bitmapSize.height);
            continue;
          }
          const top = candles.priceToCoordinate(z.p_hi);
          const bot = candles.priceToCoordinate(z.p_lo);
          if (top == null || bot == null) continue;
          c.fillStyle = hexA(col, 0.2);
          c.fillRect(a * hr, top * vr, w * hr, (bot - top) * vr);
          c.strokeStyle = hexA(col, 0.9);
          c.lineWidth = Math.max(1, hr);
          c.setLineDash(z.overdue ? [4 * hr, 3 * hr] : []);
          c.strokeRect(a * hr, top * vr, w * hr, (bot - top) * vr);
          c.setLineDash([]);
        }
      });
    }

    drawFront(target) {
      if (!ui.on || !bars) return;
      target.useBitmapCoordinateSpace((scope) => {
        const { context: c, horizontalPixelRatio: hr, verticalPixelRatio: vr } = scope;
        c.textBaseline = 'middle';
        this.labels = []; // placed translation labels: a later one that would touch them is left out
        for (const name of Object.keys(LEVELS)) {
          if (!levelOn(name)) continue;
          if (ui.layers.has('h')) this.drawCycles(c, name, hr, vr);
          if (ui.layers.has('l')) this.drawLive(c, name, hr, vr);
        }
        if (ui.layers.has('z')) this.drawZoneLabels(c, hr, vr);
      });
    }

    /** Failed cycles and translation labels. Text only where the cycle is wide enough to carry it. */
    drawCycles(c, name, hr, vr) {
      const ink = color('--muted');
      const down = color('--down');
      const minWidth = name === 'daily' ? 34 : 24;
      const raise = name === 'daily' ? 10 : name === 'weekly' ? 22 : 34;
      c.font = `${10 * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'center';
      for (const cy of data.hindsight[name].cycles) {
        if (cy.len == null) continue;
        const a = xOf(cy.s);
        const b = xOf(cy.e);
        if (a == null || b == null || b < 0 || a > chart.timeScale().width()) continue;
        if (b - a < minWidth) continue;
        if (cy.failed && cy.failed_t) {
          const y = candles.priceToCoordinate(cy.sp);
          const x2 = xOf(cy.failed_t);
          if (y != null && x2 != null) {
            c.strokeStyle = hexA(down, 0.75);
            c.lineWidth = Math.max(1, hr);
            c.setLineDash([3 * hr, 3 * hr]);
            c.beginPath();
            c.moveTo(a * hr, y * vr);
            c.lineTo(x2 * hr, y * vr);
            c.stroke();
            c.setLineDash([]);
            c.fillStyle = down;
            c.fillText('×', x2 * hr, y * vr);
          }
        }
        const x = xOf(cy.top);
        const y = candles.priceToCoordinate(cy.topp);
        if (x != null && y != null) {
          const tag = name === 'daily' ? '' : `${name === 'fouryear' ? '4Y' : 'W'} `;
          const text = `${tag}${cy.tr}`;
          const ly = Math.max(raise - 2, y - raise); // stays inside the pane at the top
          const half = c.measureText(text).width / hr / 2 + 2;
          if (!this.labels.some((l) => Math.abs(l.x - x) < l.half + half && Math.abs(l.y - ly) < 11)) {
            this.labels.push({ x, y: ly, half });
            c.fillStyle = hexA(ink, 0.9);
            c.fillText(text, x * hr, ly * vr);
          }
        }
      }
    }

    /** A ring at the low, a line along its price to the bar that confirmed it; revised lows are dim and crossed out,
     * a candidate still waiting for its signal is a dotted ring. */
    drawLive(c, name, hr, vr) {
      const col = levelColor(name);
      const r = LEVELS[name].ring;
      const tiny = barSpacing() < TEXT_ZOOM;
      if (barSpacing() < CROWDED && name !== 'fouryear') return;
      const cand = data.zones.find((z) => z.level === name)?.candidate;
      if (cand) {
        const x = xOf(cand.t);
        const y = candles.priceToCoordinate(cand.p);
        if (x != null && y != null) {
          c.strokeStyle = col;
          c.lineWidth = Math.max(1, 1.25 * hr);
          c.setLineDash([2 * hr, 2 * hr]);
          c.beginPath();
          c.arc(x * hr, y * vr, (r + 1) * hr, 0, Math.PI * 2);
          c.stroke();
          c.setLineDash([]);
        }
      }
      for (const low of data.live[name].lows) {
        const revised = low.status === 'revised';
        if (tiny && name === 'daily') continue; // on the whole history these are only noise
        const x = xOf(low.t);
        const y = candles.priceToCoordinate(low.p);
        const x2 = xOf(low.conf);
        if (x == null || y == null || x2 == null) continue;
        c.strokeStyle = hexA(col, revised ? 0.45 : 1);
        c.lineWidth = Math.max(1, 1.25 * hr);
        c.beginPath();
        c.moveTo((x + r) * hr, y * vr);
        c.lineTo(x2 * hr, y * vr);
        c.stroke();
        c.beginPath();
        c.moveTo(x2 * hr, (y - 3) * vr);
        c.lineTo(x2 * hr, (y + 3) * vr);
        c.stroke();
        c.beginPath();
        c.arc(x * hr, y * vr, r * hr, 0, Math.PI * 2);
        c.stroke();
        if (revised) {
          c.beginPath();
          c.moveTo((x - r) * hr, (y - r) * vr);
          c.lineTo((x + r) * hr, (y + r) * vr);
          c.stroke();
        }
      }
    }

    drawZoneLabels(c, hr, vr) {
      c.font = `${11 * vr}px 'Geist Mono', monospace`;
      c.textAlign = 'left';
      const taken = [];
      for (const z of data.zones) {
        if (!levelOn(z.level) || z.p_lo == null) continue;
        const a = xOf(z.t_from);
        const b = xOf(z.t_to);
        const top = candles.priceToCoordinate(z.p_hi);
        if (a == null || b == null || top == null) continue;
        const n = z.level === 'fouryear' ? `, n=${z.n_bears}` : '';
        let text = `Next ${LEVELS[z.level].name} low${n}${z.overdue ? ', late' : ''}`;
        if (narrow() || c.measureText(text).width / hr > (b - a) * 3) text = LEVELS[z.level].label; // a box too small for its name
        let y = top - 9;
        while (taken.some((t) => Math.abs(t - y) < 14)) y -= 14; // boxes share a time range: stack their names
        taken.push(y);
        const width = c.measureText(text).width / hr;
        const x = Math.min(a, chart.timeScale().width() - width - 4);
        c.fillStyle = hexA(color('--bg'), 0.75);
        c.fillRect((x - 2) * hr, (y - 7) * vr, (width + 4) * hr, 14 * vr);
        c.fillStyle = color('--ink');
        c.fillText(text, x * hr, y * vr);
      }
    }
  }

  function zoneLine(z) {
    const box = z.p_lo == null ? 'no price box yet' : `${shortMoney(z.p_lo)} to ${shortMoney(z.p_hi)}`;
    const when = `${day(z.t_from)} to ${day(z.t_to)}`;
    if (z.level === 'fouryear') {
      const f = z.lowest_so_far;
      return `next low ${when}, ${box} (from ${z.n_bears} bears, ${z.n_gaps} gaps). Lowest so far ${day(f.ts)} ${money(f.price)}, -${(f.drawdown * 100).toFixed(0)}%`;
    }
    const cand = z.candidate ? `. Candidate ${day(z.candidate.t)} ${money(z.candidate.p)}, not confirmed` : '';
    const parts = [`day ${z.elapsed} since ${day(z.anchor_ts)}`, z.translation === '?' ? 'translation not known yet' : `${z.translation} so far`];
    if (z.failed) parts.push('failed');
    if (z.overdue) parts.push('window passed');
    return `${parts.join(', ')}. Next low ${when}, ${box} (${z.n} past cycles)${cand}`;
  }

  function stateLines() {
    const lines = [];
    for (const name of Object.keys(LEVELS)) {
      const z = data.zones.find((x) => x.level === name);
      if (levelOn(name) && z) lines.push(`<div><span class="k">${LEVELS[name].label}</span>${zoneLine(z)}</div>`);
    }
    for (const o of data.overlaps) {
      if (o.levels.every(levelOn)) lines.push(`<div><span class="k">Overlap</span>${o.levels.map((n) => LEVELS[n].label).join(' + ')} windows, ${day(o.t_from)} to ${day(o.t_to)}: the shaded band</div>`);
    }
    lines.push(`<div><span class="k">Marks</span>Bitstamp 1D, rules ${data.rules_version}, as of ${data.as_of_day}</div>`);
    return lines.join('');
  }

  /** What the crosshair's bar means, if anything; otherwise the state of each level. */
  function renderInfo(time) {
    if (!ui.on) return;
    const el = $('cycles-info');
    el.hidden = !ui.layers.has('i');
    const hits = [];
    if (time != null) {
      const dayStart = time - (time % 86400);
      for (const name of Object.keys(LEVELS)) {
        if (!levelOn(name)) continue;
        if (ui.layers.has('h')) {
          const cy = data.hindsight[name].cycles.find((x) => x.e === dayStart);
          if (cy) {
            hits.push(`<div><span class="k">${LEVELS[name].label} low</span>${day(cy.e)} ${money(cy.ep)}, closes a cycle of ${cy.len} days, ${cy.tr}${cy.failed ? ', failed' : ''}${cy.hcl_above === null ? '' : `, half-cycle low ${cy.hcl_above ? 'above' : 'below'} its start`}</div>`);
          }
        }
        if (ui.layers.has('l')) {
          const low = data.live[name].lows.find((x) => x.t === dayStart);
          if (low) {
            hits.push(`<div><span class="k">${LEVELS[name].label} live</span>${day(low.t)} ${money(low.p)}, confirmed ${day(low.conf)} by ${low.signal === 'sma' ? 'the 10 SMA' : 'a swing-low candle'}${low.status === 'revised' ? `, revised ${day(low.revised)}` : ''}</div>`);
          }
        }
      }
    }
    if (hits.length) {
      el.innerHTML = hits.join('');
    } else { // the panel keeps this height, so that hovering does not resize the chart under the mouse
      el.style.minHeight = '';
      el.innerHTML = stateLines();
      el.style.minHeight = `${el.offsetHeight}px`;
    }
  }

  function paintToggles() {
    markSeg($('seg-cycles'), ui.on ? 'on' : '');
    $('cycles-bar').hidden = !ui.on;
    for (const b of $('seg-cycle-levels').children) b.setAttribute('aria-pressed', String(ui.on && ui.levels.has(b.dataset.value)));
    for (const b of $('seg-cycle-layers').children) b.setAttribute('aria-pressed', String(ui.on && ui.layers.has(b.dataset.value)));
  }

  /** Room for the boxes on the right of a daily chart. `whole`: the chart has just fitted all bars, which it does
   * lazily, so the range it reports is still the old one. */
  function showZones(whole = false) {
    if (!ui.on || !ui.layers.has('z') || state.tf !== '1d' || !bars) return;
    const ends = data.zones.filter((z) => levelOn(z.level)).map((z) => logicalOf(z.t_to));
    if (!ends.length) return;
    const need = Math.max(...ends) + 6;
    if (whole) {
      chart.timeScale().setVisibleLogicalRange({ from: 0, to: need });
      return;
    }
    const r = chart.timeScale().getVisibleLogicalRange();
    if (r && r.to < need && r.to >= bars.n - 30) chart.timeScale().setVisibleLogicalRange({ from: r.from, to: need });
  }

  function refresh() {
    if (!bars) return;
    markers.setMarkers(buildMarkers());
    primitive.requestUpdate?.();
    renderInfo(null);
  }

  function changed() {
    paintToggles();
    syncControls();
    showZones();
    refresh();
  }

  function toggleIn(set, value) {
    if (set.has(value)) set.delete(value);
    else set.add(value);
    changed();
  }

  function buildUi() {
    const seg = $('seg-cycles');
    buildSeg(seg, { on: 'Cycles' }, () => { ui.on = !ui.on; changed(); });
    seg.hidden = false;
    const levels = $('seg-cycle-levels');
    buildSeg(levels, Object.fromEntries(Object.values(LEVELS).map((l) => [l.key, l.label])), (v) => toggleIn(ui.levels, v));
    for (const b of levels.children) b.insertAdjacentHTML('afterbegin', `<span class="swatch swatch-${b.dataset.value}"></span>`);
    buildSeg($('seg-cycle-layers'), LAYERS, (v) => toggleIn(ui.layers, v));
  }

  globalThis.EWCycles = {
    addParams(q) {
      if (!data || !ui.on) return;
      q.set('cycles', '1');
      q.set('clv', [...ui.levels].join(','));
      q.set('cly', [...ui.layers].join(','));
    },
    onBars() {
      if (!data) return;
      showZones(true);
      refresh();
    },
  };

  async function start() {
    let file;
    try {
      const r = await fetch('data/local/cycles.json', { cache: 'no-cache' });
      if (!r.ok) return;
      file = await r.json();
    } catch {
      return; // no data, no toggle
    }
    if (file.format !== 'ewave-cycles-1') return;
    data = file;
    markers = LightweightCharts.createSeriesMarkers(candles, []);
    primitive = new Overlay();
    candles.attachPrimitive(primitive);
    buildUi();
    paintToggles();
    let bucket = null;
    chart.timeScale().subscribeVisibleLogicalRangeChange(() => { // marks gain their text when there is room for it
      const b = `${barSpacing() >= TEXT_ZOOM}/${barSpacing() < CROWDED}`;
      if (b !== bucket && bars) {
        bucket = b;
        markers.setMarkers(buildMarkers());
      }
    });
    chart.subscribeCrosshairMove((p) => renderInfo(p.time));
    if (bars) {
      syncControls();
      showZones(true);
      refresh();
    }
  }

  start();
})();

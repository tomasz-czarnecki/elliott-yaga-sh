/** Shared by both pages: stats.json, the bar files (format in src/ewave/ingest/export.py), formatting. */

const EW = (() => {
  let statsPromise = null;

  function loadStats() {
    statsPromise ??= fetch('data/stats.json', { cache: 'no-cache' }).then((r) => {
      if (!r.ok) throw new Error(`stats.json: HTTP ${r.status}`);
      return r.json();
    });
    return statsPromise;
  }

  /** Column arrays back from the file's scaled, delta-coded integers. */
  function decodeBars(f) {
    const n = f.n;
    const out = { n, time: new Array(n), open: new Array(n), high: new Array(n), low: new Array(n), close: new Array(n), volume: new Array(n), short: new Map(f.short) };
    const s = f.price_scale;
    let t = 0;
    let o = 0;
    for (let i = 0; i < n; i++) {
      t = i === 0 ? f.t[0] : t + f.t[i] * f.bar_s;
      o = i === 0 ? f.o[0] : o + f.o[i];
      out.time[i] = t;
      out.open[i] = o / s;
      out.high[i] = (o + f.h[i]) / s;
      out.low[i] = (o - f.l[i]) / s;
      out.close[i] = (o + f.c[i]) / s;
      out.volume[i] = f.v[i] / f.volume_scale;
    }
    return out;
  }

  /** One venue and timeframe. The generation time keeps caches from serving an older export. */
  async function loadBars(stats, venue, tf) {
    const entry = stats.venues[venue].bars[tf];
    if (!entry) throw new Error(`no ${tf} bars for ${venue}`);
    const r = await fetch(`data/${entry.file}?v=${stats.generated_at_ms}`);
    if (!r.ok) throw new Error(`${entry.file}: HTTP ${r.status}`);
    return decodeBars(await r.json());
  }

  const iso = (ms) => new Date(ms).toISOString();
  const fmtDate = (ms) => iso(ms).slice(0, 10);
  const fmtMinute = (ms) => `${iso(ms).slice(0, 10)} ${iso(ms).slice(11, 16)} UTC`;
  const fmtInt = (n) => n.toLocaleString('en-US');
  const fmtPrice = (p) => p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtTick = (p) => (p >= 100 ? p.toLocaleString('en-US', { maximumFractionDigits: 0 }) : fmtPrice(p));

  function fmtVolume(v) {
    if (v >= 1e6) return `${(v / 1e6).toFixed(2)} M`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(2)} K`;
    return v.toFixed(2);
  }

  return { loadStats, loadBars, fmtDate, fmtMinute, fmtInt, fmtPrice, fmtTick, fmtVolume };
})();

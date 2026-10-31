/** Candlestick page. The state lives in the URL (?venue=bybit&tf=1h&scale=log), so a view can be linked to. */

const VENUES = {
  bybit_btcusdt_perp: { label: 'Bybit perp', note: 'Equals TradingView BYBIT:BTCUSDT.P.' },
  binance_btcusdt: { label: 'Binance spot', note: 'Bars that span an exchange outage are marked in the readout.' },
  bitstamp_btcusd: { label: 'Bitstamp spot', note: 'Before 2013 it is mostly no-trade minutes: a thin market.' },
};
const TIMEFRAMES = { '1d': '1D', '4h': '4H', '1h': '1H', '15m': '15m' };
const SCALES = { log: 'Log', linear: 'Linear' };
const DEFAULT_TF = '1d';
const BAR_MINUTES = { '1d': 1440, '4h': 240, '1h': 60, '15m': 15 };
const BARS_IN_VIEW = () => (innerWidth < 600 ? 90 : 400);

const { createChart, CandlestickSeries, HistogramSeries, PriceScaleMode, CrosshairMode } = LightweightCharts;

const root = document.documentElement;
const css = getComputedStyle(root);
const color = (name) => css.getPropertyValue(name).trim();
const $ = (id) => document.getElementById(id);

const params = new URLSearchParams(location.search);
const venueParam = params.get('venue') ?? '';
const state = {
  venue: Object.keys(VENUES).find((v) => venueParam && v.startsWith(venueParam)) ?? null,
  tf: TIMEFRAMES[params.get('tf')] ? params.get('tf') : DEFAULT_TF,
  scale: SCALES[params.get('scale')] ? params.get('scale') : null, // null: log on 1D, linear on the others
};
const scaleNow = () => state.scale ?? (state.tf === '1d' ? 'log' : 'linear');

const cache = new Map();
let bars = null;
let indexByTime = new Map();
let stats = null;
let request = 0;

const chart = createChart($('chart'), {
  autoSize: true,
  layout: {
    background: { type: 'solid', color: color('--bg') },
    textColor: color('--muted'),
    fontFamily: "'Geist Mono', ui-monospace, monospace",
    fontSize: 11,
    attributionLogo: true, // required by the Lightweight Charts license
    panes: { separatorColor: color('--line'), separatorHoverColor: color('--surface') },
  },
  grid: { vertLines: { color: color('--surface') }, horzLines: { color: color('--surface') } },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: { color: color('--line-strong'), labelBackgroundColor: color('--line-strong') },
    horzLine: { color: color('--line-strong'), labelBackgroundColor: color('--line-strong') },
  },
  rightPriceScale: { borderColor: color('--line'), scaleMargins: { top: 0.06, bottom: 0.06 } },
  timeScale: { borderColor: color('--line'), rightOffset: 4, secondsVisible: false, minBarSpacing: 0.04 }, // low enough to fit 15 years of days on a phone
  localization: {
    locale: 'en-US',
    timeFormatter: (t) => EW.fmtMinute(t * 1000),
  },
});

const candles = chart.addSeries(CandlestickSeries, {
  upColor: color('--up'),
  downColor: color('--down'),
  wickUpColor: color('--up'),
  wickDownColor: color('--down'),
  borderVisible: false,
  priceFormat: { type: 'custom', minMove: 0.01, formatter: EW.fmtPrice, tickmarksFormatter: (ps) => ps.map(EW.fmtTick) },
});
const volume = chart.addSeries(HistogramSeries, {
  color: color('--volume'),
  priceFormat: { type: 'custom', minMove: 0.001, formatter: EW.fmtVolume },
  priceLineVisible: false,
  lastValueVisible: false,
}, 1);
chart.panes()[0].setStretchFactor(4);
chart.panes()[1].setStretchFactor(1);

function showMessage(text) {
  $('chart-msg').textContent = text;
  $('chart-msg').hidden = !text;
}

function buildSeg(host, options, onPick) {
  host.replaceChildren(...Object.entries(options).map(([value, label]) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.dataset.value = value;
    b.textContent = label;
    b.addEventListener('click', () => onPick(value));
    return b;
  }));
}

function markSeg(host, value) {
  for (const b of host.children) b.setAttribute('aria-pressed', String(b.dataset.value === value));
}

function syncControls() {
  markSeg($('seg-venue'), state.venue);
  markSeg($('seg-tf'), state.tf);
  markSeg($('seg-scale'), scaleNow());
  const q = new URLSearchParams({ venue: state.venue, tf: state.tf });
  if (state.scale) q.set('scale', state.scale);
  globalThis.EWCycles?.addParams(q);
  globalThis.EWCounts?.addParams(q);
  history.replaceState(null, '', `?${q}`);
}

function applyScale() {
  candles.priceScale().applyOptions({
    mode: scaleNow() === 'log' ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
    autoScale: true,
  });
}

function renderReadout(i) {
  const el = $('readout');
  if (i == null) {
    el.textContent = '';
    return;
  }
  const row = (k, v) => `<span><span class="k">${k}</span>${v}</span>`;
  const change = (bars.close[i] - bars.open[i]) / bars.open[i] * 100;
  const short = bars.short.get(i);
  el.innerHTML = [
    `<span>${EW.fmtMinute(bars.time[i] * 1000)}</span>`,
    row('O', EW.fmtPrice(bars.open[i])),
    row('H', EW.fmtPrice(bars.high[i])),
    row('L', EW.fmtPrice(bars.low[i])),
    row('C', EW.fmtPrice(bars.close[i])),
    `<span>${change >= 0 ? '+' : ''}${change.toFixed(2)}%</span>`,
    row('Vol', `${EW.fmtVolume(bars.volume[i])} BTC`),
    short != null ? `<span class="warn">Only ${short} of ${BAR_MINUTES[state.tf]} minutes</span>` : '',
  ].join('');
}

function renderFoot() {
  const entry = stats.venues[state.venue].bars[state.tf];
  const label = TIMEFRAMES[state.tf];
  const parts = [`Data until the ${label} bar opening ${EW.fmtMinute(entry.last_ms)}. All times UTC.`];
  if (entry.recent_days) parts.push(`${label} shows the last ${entry.recent_days} days only.`);
  $('foot-until').textContent = parts.join(' ');
  $('foot-venue').textContent = `${stats.venues[state.venue].title}. ${VENUES[state.venue].note}`;
}

async function load() {
  const mine = ++request;
  const key = `${state.venue}/${state.tf}`;
  syncControls();
  applyScale();
  if (!cache.has(key)) {
    const entry = stats.venues[state.venue].bars[state.tf];
    if (!entry) {
      root.dataset.chartState = 'error';
      showMessage(`No ${TIMEFRAMES[state.tf]} bars for this venue yet.`);
      return;
    }
    root.dataset.chartState = 'loading';
    showMessage(`Loading ${EW.fmtInt(entry.n)} ${TIMEFRAMES[state.tf]} bars`);
    let data;
    try {
      data = await EW.loadBars(stats, state.venue, state.tf);
    } catch (err) {
      if (mine === request) {
        root.dataset.chartState = 'error';
        showMessage(`These bars could not be loaded. ${err.message}`);
      }
      return;
    }
    cache.set(key, data);
    if (mine !== request) return;
  }
  bars = cache.get(key);
  indexByTime = new Map(bars.time.map((t, i) => [t, i]));

  const ohlc = new Array(bars.n);
  const vol = new Array(bars.n);
  for (let i = 0; i < bars.n; i++) {
    ohlc[i] = { time: bars.time[i], open: bars.open[i], high: bars.high[i], low: bars.low[i], close: bars.close[i] };
    vol[i] = { time: bars.time[i], value: bars.volume[i] };
  }
  chart.applyOptions({ timeScale: { timeVisible: state.tf !== '1d' } });
  candles.setData(ohlc);
  volume.setData(vol);

  if (state.tf === '1d') chart.timeScale().fitContent();
  else chart.timeScale().setVisibleLogicalRange({ from: bars.n - BARS_IN_VIEW(), to: bars.n + 4 });

  renderReadout(bars.n - 1);
  renderFoot();
  showMessage('');
  root.dataset.chartState = 'ready';
  globalThis.EWCycles?.onBars();
  globalThis.EWCounts?.onBars();
}

chart.subscribeCrosshairMove((p) => {
  if (!bars) return;
  renderReadout(p.time != null && indexByTime.has(p.time) ? indexByTime.get(p.time) : bars.n - 1);
});

buildSeg($('seg-venue'), Object.fromEntries(Object.entries(VENUES).map(([k, v]) => [k, v.label])), (v) => { state.venue = v; load(); });
buildSeg($('seg-tf'), TIMEFRAMES, (v) => { state.tf = v; load(); });
buildSeg($('seg-scale'), SCALES, (v) => { state.scale = v; syncControls(); applyScale(); });

EW.loadStats().then((s) => {
  stats = s;
  state.venue ??= s.default_venue;
  return load();
}).catch((err) => {
  console.warn('site data is not available:', err);
  root.dataset.chartState = 'error';
  showMessage('Chart data is not generated yet. Run: uv run ewave-data export-site');
});

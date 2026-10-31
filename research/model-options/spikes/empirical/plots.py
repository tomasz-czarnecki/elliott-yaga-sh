"""Density plots for 02-empirical.md, from the raw results of the b1, b2 and c scripts. PNGs go to the scratch folder.

    uv run --with numpy --with matplotlib python research/model-options/spikes/empirical/plots.py

Reads b1_{tf}.npz, b2_{tf}.npz and c_positions.csv. One blue line for BTC, a grey band for the null (5-95 percent of paths), a
dashed line for the null median. Colours: slots 1 and 2 of the dataviz reference palette; text in ink colours only.
"""
from __future__ import annotations

import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import FIB_LEVELS, OUT

BTC = "#2a78d6"
NULL_LINE = "#eb6834"
BAND = "#d9d8d2"
INK = "#0b0b0b"
INK2 = "#52514e"
SURFACE = "#fcfcfb"
GRID = "#e8e7e2"

plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.titlesize": 9.5, "axes.titlecolor": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})


def _density_panel(ax, bins, btc_counts, null_counts, title, levels=FIB_LEVELS, xlim=(0.15, 5.0), label_levels=True, smooth=1):
    width = np.diff(bins)
    centers = np.exp((bins[:-1] + bins[1:]) / 2)

    def norm(x):
        total = x.sum(axis=-1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            out = x / np.maximum(total, 1) / width
        if smooth > 1:
            kernel = np.ones(smooth) / smooth
            out = np.apply_along_axis(lambda v: np.convolve(v, kernel, mode="same"), -1, out)
        return out

    b = norm(btc_counts.astype(float))
    n = norm(null_counts.astype(float))
    lo, mid, hi = np.percentile(n, [5, 50, 95], axis=0)
    ax.fill_between(centers, lo, hi, color=BAND, linewidth=0, zorder=1)
    ax.plot(centers, mid, color=NULL_LINE, linewidth=1.2, linestyle=(0, (4, 2)), zorder=2)
    ax.plot(centers, b, color=BTC, linewidth=1.6, zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(*xlim)
    ax.set_ylim(bottom=0)
    top = ax.get_ylim()[1]
    for level in levels:
        if xlim[0] < level < xlim[1]:
            ax.axvline(level, color=INK2, linewidth=0.5, linestyle=":", zorder=0)
            if label_levels:
                ax.text(level, top * 1.0, f"{level:g}", rotation=90, fontsize=6.5, color=INK2, ha="center", va="top",
                        bbox=dict(facecolor=SURFACE, edgecolor="none", pad=0.6))
    ax.set_xticks([0.25, 0.5, 1, 2, 4])
    ax.set_xticklabels(["0.25", "0.5", "1", "2", "4"])
    ax.minorticks_off()
    ax.set_title(title, loc="left")
    ax.set_xlabel("ratio (log axis)")
    ax.set_ylabel("density per unit of ln(ratio)")


def _legend(fig, null_label: str) -> None:
    handles = [plt.Line2D([], [], color=BTC, linewidth=1.6, label="BTC (Bitstamp)"),
               plt.Line2D([], [], color=NULL_LINE, linewidth=1.2, linestyle=(0, (4, 2)), label=f"{null_label}, median of paths"),
               plt.Rectangle((0, 0), 1, 1, color=BAND, label=f"{null_label}, 5-95% of paths")]
    fig.legend(handles=handles, loc="lower center", ncols=3, frameon=False, fontsize=8.5, labelcolor=INK2)


def b1_figure(kind: str = "signflip") -> None:
    from b1_fib_unconditional import BINS, HIST_TYPES
    cells = (("15m", "15m_pct2"), ("1h", "1h_pct4"), ("4h", "4h_pct8"), ("1d", "1d_pct16"))
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.4), constrained_layout=True)
    fig.get_layout_engine().set(rect=(0, 0.05, 1, 0.9))
    fig.suptitle("Swing retracement ratios, BTC against a volatility-only null. No bump at a Fibonacci level; a step at 1.0, with a hole just above it.",
                 color=INK, fontsize=10.5, x=0.01, ha="left")
    for ax, (tf, cell) in zip(axes.ravel(), cells):
        d = np.load(OUT / f"b1_{tf}.npz")
        ci = [str(c) for c in d["cells"]].index(cell)
        ti = HIST_TYPES.index("ret")
        btc = d["btc_H"][ci, ti].sum(axis=0)
        null = d[f"H_{kind}"][:, ci, ti].sum(axis=1)
        _density_panel(ax, BINS, btc, null, f"{cell}: {int(btc.sum()):,} consecutive leg pairs", xlim=(0.2, 5.0), smooth=2)
    _legend(fig, kind)
    fig.savefig(OUT / "fig_b1_density.png", dpi=150)
    plt.close(fig)


def b2_figure(kind: str = "trendflip") -> None:
    from b2_fib_impulse import BINS, HIST_KEYS, LADDERS
    cells = LADDERS["ladder_pct"]
    panels = (("w2", "W2 retracement, pull 0-1", (0.15, 1.1), (0.382, 0.5, 0.618, 0.786)),
              ("w3", "W3 extension, pull 0-1-2", (0.6, 6.0), (1.0, 1.618, 2.0, 2.618, 3.236, 4.236)),
              ("w4", "W4 retracement, pull 2-3", (0.15, 1.1), (0.236, 0.382, 0.5, 0.618)),
              ("w5_014", "W5 extension, pull 0-1-4", (0.2, 6.0), (0.618, 1.0, 1.618, 2.618)))
    data = {}
    for tf in ("15m", "1h", "4h", "1d"):
        data[tf] = np.load(OUT / f"b2_{tf}.npz")
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.4), constrained_layout=True)
    fig.get_layout_engine().set(rect=(0, 0.05, 1, 0.9))
    fig.suptitle("Inside rule-legal impulses (15m 2%, 1h 4%, 4h 8%, 1d 16%, pooled): BTC against the same detector on trend-and-volatility paths.",
                 color=INK, fontsize=10, x=0.01, ha="left")
    for ax, (key, title, xlim, levels) in zip(axes.ravel(), panels):
        hi_ = HIST_KEYS.index(key)
        btc_h, null_h = 0, 0
        paths = min(data[cell.split("_")[0]][f"H_{kind}"].shape[0] for cell in cells)
        for cell in cells:
            tf = cell.split("_")[0]
            d = data[tf]
            ci = [str(c) for c in d["cells"]].index(cell)
            btc_h = btc_h + d["btc_H"][ci, hi_].sum(axis=0)
            null_h = null_h + d[f"H_{kind}"][:paths, ci, hi_].sum(axis=1).astype(np.int64)
        _density_panel(ax, BINS, btc_h, null_h, f"{title}: {int(btc_h.sum()):,} impulses", levels=levels, xlim=xlim, smooth=3)
    _legend(fig, kind)
    fig.savefig(OUT / "fig_b2_impulse.png", dpi=150)
    plt.close(fig)


def c_figure() -> None:
    with (OUT / "c_positions.csv").open() as f:
        rows = {r["key"]: r for r in csv.DictReader(f)}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
    fig.get_layout_engine().set(rect=(0, 0.08, 1, 0.86))
    fig.suptitle("Where the weekly cycle's top sits. Random paths put most tops late; BTC's tops do not cluster at the midpoint beyond chance (22-23 cycles).",
                 color=INK, fontsize=10, x=0.01, ha="left")
    x = np.arange(10)
    labels = [f"{i / 10:.1f}" for i in range(10)]
    for ax, key, title in ((axes[0], "top_pos|hind", "Hindsight marks"), (axes[1], "top_pos|live", "Live marks")):
        r = rows[key]
        b = [float(r[f"btc_{i}"]) for i in x]
        shuffle = [float(r[f"shuffle_{i}"]) for i in x]
        ax.bar(x, b, width=0.8, color=BTC, zorder=2, label=f"BTC, {r['n_btc']} cycles")
        ax.plot(x, shuffle, color=NULL_LINE, linewidth=1.6, marker="o", markersize=4, zorder=3, label="shuffled days, all cycles")
        ax.axhline(0.1, color=INK2, linewidth=0.8, linestyle=":", zorder=1)
        ax.text(-0.45, 0.103, "uniform", fontsize=7, color=INK2, ha="left", va="bottom")
        ax.set_xticks(x, labels)
        ax.set_xlabel("top position in the cycle (start of each 0.1 bin)")
        ax.set_ylabel("share of cycles")
        ax.set_title(title, loc="left")
        ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper left")
    fig.savefig(OUT / "fig_c1_top_position.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    want = sys.argv[1:] or ["b1", "b2", "c"]
    if "b1" in want:
        b1_figure()
    if "b2" in want:
        b2_figure()
    if "c" in want:
        c_figure()
    print("done")

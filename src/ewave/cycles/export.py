"""`site/data/local/cycles.json`: what the chart overlay draws. It stays out of git (site/data/local/ is ignored), so
it never reaches the public site. Times are in s, as the chart library wants them.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..ingest.config import project_root
from ..ingest.store import atomic_write
from .config import Rules
from .cycle import Cycle
from .hindsight import Hindsight, build
from .live import LiveEngine, LiveLow, replay
from .series import Bars, day_str
from .zones import overlaps

FORMAT = "ewave-cycles-1"
LEVEL_ORDER = ("fouryear", "weekly", "daily")


def default_path() -> Path:
    return project_root() / "site" / "data" / "local" / "cycles.json"


def _s(ms: int | None) -> int | None:
    return None if ms is None else ms // 1000


def _cycle(c: Cycle) -> dict:
    return {
        "s": _s(c.start_ts), "sp": c.start_price, "e": _s(c.end_ts), "ep": c.end_price, "len": c.length,
        "elapsed": c.elapsed, "top": _s(c.top_ts), "topp": c.top_price, "pos": round(c.top_pos, 3), "tr": c.translation,
        "hcl": _s(c.hcl_ts), "hclp": c.hcl_price, "hcl_above": c.hcl_above_start, "failed": c.failed,
        "failed_t": _s(c.failed_ts), "status": c.status,
    }


def _live_low(x: LiveLow) -> dict:
    return {
        "t": _s(x.ts_low), "p": x.price, "conf": _s(x.ts_confirmed), "signal": x.signal, "status": x.status,
        "revised": _s(x.ts_revised), "undercut": _s(x.ts_undercut), "failed": _s(x.ts_failed),
    }


def _zone(z: dict) -> dict:
    out = dict(z)
    for key in ("anchor_ts", "anchor_confirmed", "t_from", "t_to", "top_ts", "ath_ts"):
        if key in out:
            out[key] = _s(out[key])
    if out.get("candidate"):
        out["candidate"] = {"t": _s(out["candidate"]["ts"]), "p": out["candidate"]["price"]}
    if out.get("lowest_so_far"):
        out["lowest_so_far"] = {**out["lowest_so_far"], "ts": _s(out["lowest_so_far"]["ts"])}
    if out.get("spans"):
        out["spans"] = {k: [_s(a), _s(b)] for k, (a, b) in out["spans"].items()}
    return out


def payload(bars: Bars, rules: Rules, now_ms: int, h: Hindsight | None = None, e: LiveEngine | None = None) -> dict:
    h = h or build(bars, rules)
    e = e or replay(bars, rules)
    zones = e.zones()
    machines = {"daily": e.daily, "weekly": e.weekly}
    return {
        "format": FORMAT,
        "rules_version": rules.version,
        "rules_digest": rules.digest,
        "venue": rules.series["venue"],
        "generated_at_ms": now_ms,
        "as_of": _s(bars.ts[-1]),
        "as_of_day": day_str(bars.ts[-1]),
        "hindsight": {
            name: {"lows": [{"t": _s(bars.ts[i]), "p": bars.low[i]} for i in h.lows[name]],
                   "cycles": [_cycle(c) for c in h.cycles[name]]}
            for name in LEVEL_ORDER
        },
        "live": {
            "daily": {"lows": [_live_low(x) for x in e.daily.log], "cycles": [_cycle(c) for c in e.daily.cycles],
                      "open": _cycle(e.daily.open_cycle(len(bars) - 1)) if e.daily.chain else None},
            "weekly": {"lows": [_live_low(x) for x in e.weekly.log], "cycles": [_cycle(c) for c in e.weekly.cycles],
                       "open": _cycle(e.weekly.open_cycle(len(bars) - 1)) if e.weekly.chain else None},
            "fouryear": {"lows": [_live_low(x) for x in e.fouryear.log], "cycles": [], "open": None},
        },
        "revisions": {name: [{k: (_s(v) if k.startswith("ts_") else v) for k, v in r.items()} for r in machines[name].revisions]
                      for name in machines} | {
            "fouryear": [{k: (_s(v) if k.startswith("ts_") else v) for k, v in r.items()} for r in e.fouryear.revisions]},
        "zones": [_zone(z) for z in zones],
        "overlaps": [{"levels": o["levels"], "t_from": _s(o["t_from"]), "t_to": _s(o["t_to"])} for o in overlaps(zones)],
    }


def write(obj: dict, out: Path | str | None = None) -> tuple[Path, int]:
    path = Path(out) if out else default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, separators=(",", ":")).encode()
    atomic_write(path, lambda f: f.write(data))
    return path, len(data)

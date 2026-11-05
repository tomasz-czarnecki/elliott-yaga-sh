"""Cycles as a second clock. Information only: nothing here reaches the fit. Reads `site/data/local/cycles.json` (written by
`ewave-cycles export`, Bitstamp spot) and says whether a running wave's time window agrees with the 4-year and weekly low
windows. A wave down should end near a low the cycles expect; a wave up should not be due to end while they expect a low.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..ingest.config import project_root

DAY = 86_400


def default_path() -> Path:
    return project_root() / "site" / "data" / "local" / "cycles.json"


def _day(s: int) -> str:
    return datetime.fromtimestamp(s, tz=timezone.utc).strftime("%Y-%m-%d")


def load_windows(path: Path | str | None = None) -> list[dict] | None:
    """The cycle low windows, in s. None when the file is missing or unreadable: this clock is optional."""
    try:
        d = json.loads(Path(path or default_path()).read_text())
    except (OSError, ValueError):
        return None
    out = []
    for z in d.get("zones", []):
        if z.get("level") not in ("fouryear", "weekly") or z.get("failed"):
            continue
        row = {"level": z["level"], "name": "4-year" if z["level"] == "fouryear" else "weekly", "lo": z["t_from"], "hi": z["t_to"]}
        gap = (z.get("spans") or {}).get("gap_from_last_low")
        if gap:
            row["spacing"] = {"lo": gap[0], "hi": gap[1], "lo_str": _day(gap[0]), "hi_str": _day(gap[1])}
        row["lo_str"], row["hi_str"] = _day(row["lo"]), _day(row["hi"])
        out.append(row)
    return out or None


def tag(window: dict | None, d: str, windows: list[dict] | None) -> list[dict]:
    """One row per cycle window. `window`: the running wave's, in s. `d`: its direction, up or down."""
    if not window or not windows:
        return []
    out = []
    for z in windows:
        lo, hi = window["lo"], window["hi"]
        overlap = lo <= z["hi"] and z["lo"] <= hi
        gap_days = 0 if overlap else round((lo - z["hi"] if lo > z["hi"] else z["lo"] - hi) / DAY)
        if d == "down":
            state = "agrees" if overlap else "conflicts"
        else:
            state = "conflicts" if overlap else "no clash"
        when = f"{z['lo_str']} to {z['hi_str']}"
        if state == "agrees":
            text = f"{z['name']} low due {when}: the windows overlap"
        elif d == "down":
            side = "after" if lo > z["hi"] else "before"
            text = f"{z['name']} low due {when}: this wave ends {gap_days}d {side} it"
        elif overlap:
            text = f"{z['name']} low due {when}: this wave up is due to end inside it"
        else:
            text = f"{z['name']} low due {when}: no overlap with this wave up"
        row = {"level": z["level"], "state": state, "gap_days": gap_days, "text": text}
        spacing = z.get("spacing")
        if spacing and d == "down":
            row["spacing_gap_days"] = 0 if lo <= spacing["hi"] and spacing["lo"] <= hi else round((lo - spacing["hi"] if lo > spacing["hi"] else spacing["lo"] - hi) / DAY)
            row["text"] += f" (by spacing alone {spacing['lo_str']} to {spacing['hi_str']})"
        out.append(row)
    return out

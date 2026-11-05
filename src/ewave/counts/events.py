"""What changed since the last export. Each export is compared with the state the one before it left behind, and what happened in
between goes to a JSON-lines file, one line per event, as short messages for a person. `ewave-counts events --new` prints the
unseen ones and marks them seen.

  top       the top count of a frame changed, once the new one has led for N consecutive exports on new bars (rules: events.confirm)
  invalid   price crossed a kept count's invalidation
  box       price entered a kept count's target box, or one of the top clusters
  window    a kept count's time window opened or closed

Same as-of time, nothing to compare: the 15-minute sync can export twice on one bar. New rules start a new baseline, because
an engine change is not a market event. The first run is a baseline too, so nothing floods in.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..ingest.config import data_root
from ..ingest.store import atomic_write


def base_dir() -> Path:
    return data_root() / "counts"


def _p(x: float) -> str:
    return f"{x:,.0f}"


def _reading(n: dict) -> str:
    return "|".join([n["tf"], n["pattern"], n["dir"] or "", *(str(x["t"]) for x in n["labels"])])


TF = {"1d": "1D", "12h": "12H", "4h": "4H", "1h": "1H", "15m": "15m"}


def snapshot(obj: dict, spec: dict) -> dict:
    """What the next export needs from this one. Kept small: it is a file on disk, read every 15 minutes."""
    roots = {}
    for root in spec["roots"]:
        tree = obj["trees"].get(root)
        if tree is None:
            continue
        frames, kept = {}, {}
        for lv in tree["levels"]:
            if lv["nodes"]:
                n = lv["nodes"][0]
                frames[lv["tf"]] = {"sig": _reading(n), "title": n["short"]}
            for n in lv["nodes"]:
                sig = _reading(n)
                if sig in kept:
                    continue
                zone = [t["p"] for leg in n["projection"]["legs"][:1] for t in leg["targets"] if not t["reached"]]
                kept[sig] = {"id": n["id"], "tf": n["tf"], "title": n["short"], "inv": n["invalidation"]["p"], "side": n["invalidation"]["side"], "wave": n["wave"]["name"],
                             "box": [min(zone), max(zone)] if zone else None, "win": n["window"]["status"] if n["window"] else None,
                             "win_lo": n["window"]["lo_str"] if n["window"] else None, "win_hi": n["window"]["hi_str"] if n["window"] else None}
        clusters = [{"id": f"{round(c['p'], -1):.0f}", "lo": c["lo"], "hi": c["hi"], "p": c["p"], "readings": c["readings"]} for c in (tree.get("clusters") or {"rows": []})["rows"][: spec["cluster_top"]]]
        roots[root] = {"frames": frames, "kept": kept, "clusters": clusters}
    return {"as_of": obj["as_of"], "digest": obj["rules_digest"], "price": obj["price"], "roots": roots}


def _range(obj: dict, since_s: int) -> tuple[float, float] | None:
    """Highest high and lowest low of the 15m bars printed since then."""
    bars = [b for b in obj["recent_bars"].get("15m", []) if b[0] >= since_s]
    if not bars:
        return None
    return max(b[2] for b in bars), min(b[3] for b in bars)


def _event(kind: str, as_of: int, root: str, msg: str, **data) -> dict:
    key = hashlib.sha256(json.dumps([kind, as_of, root, msg], separators=(",", ":")).encode()).hexdigest()[:12]
    return {"id": key, "kind": kind, "as_of": as_of, "root": root, "msg": msg, **data}


def compare(prev: dict | None, snap: dict, obj: dict, spec: dict) -> tuple[list[dict], dict]:
    """The events between two exports, and the state to keep. Pure: no file is touched here."""
    state = {"as_of": snap["as_of"], "digest": snap["digest"], "roots": {}}
    fresh = prev is None or prev.get("digest") != snap["digest"]
    if not fresh and prev["as_of"] == snap["as_of"]:
        return [], prev
    events: list[dict] = []
    span = None if fresh else _range(obj, prev["as_of"])
    confirm = spec["confirm"]
    for root, now in snap["roots"].items():
        old = None if fresh else prev["roots"].get(root)
        tops = {}
        for tf, row in now["frames"].items():
            had = None if old is None else old["tops"].get(tf)
            if had is None:
                tops[tf] = {"sig": row["sig"], "title": row["title"], "cand": None, "cand_title": None, "streak": 0}
                continue
            top = dict(had)
            if row["sig"] == had["sig"]:
                top.update(cand=None, cand_title=None, streak=0, title=row["title"])
            else:
                streak = had["streak"] + 1 if row["sig"] == had["cand"] else 1
                top.update(cand=row["sig"], cand_title=row["title"], streak=streak)
                if streak >= confirm[tf]:
                    events.append(_event("top", snap["as_of"], root, f"{TF[tf]} top count changed: {had['title']} > {row['title']} (led {streak} exports)", frame=tf, old=had["sig"], new=row["sig"]))
                    top = {"sig": row["sig"], "title": row["title"], "cand": None, "cand_title": None, "streak": 0}
            tops[tf] = top
        kept_old = {} if old is None else old["kept"]
        kept_new = {}
        for sig, row in now["kept"].items():
            had = kept_old.get(sig)
            cur = dict(row)
            cur["in_box"] = bool(had and had.get("in_box"))
            kept_new[sig] = cur
        if old is not None:
            for sig, had in kept_old.items():
                if span is not None:
                    hi, lo = span
                    if (had["side"] == "above" and hi > had["inv"]) or (had["side"] == "below" and lo < had["inv"]):
                        events.append(_event("invalid", snap["as_of"], root, f"{TF[had['tf']]} {had['title']}: invalidated, price went {had['side']} {_p(had['inv'])}", frame=had["tf"], sig=sig, level=had["inv"]))
                        kept_new.pop(sig, None)
            for sig, cur in kept_new.items():
                had = kept_old.get(sig)
                if had is None:
                    continue
                if span is not None and cur["box"]:
                    hi, lo = span
                    touching = hi >= cur["box"][0] and lo <= cur["box"][1]
                    if touching and not cur["in_box"]:
                        events.append(_event("box", snap["as_of"], root, f"{TF[cur['tf']]} {cur['title']}: price entered {cur['wave']}'s box {_p(cur['box'][0])} to {_p(cur['box'][1])}", frame=cur["tf"], sig=sig))
                    cur["in_box"] = touching
                if had["win"] != cur["win"]:
                    if had["win"] == "early" and cur["win"] == "inside":
                        events.append(_event("window", snap["as_of"], root, f"{TF[cur['tf']]} {cur['title']}: {cur['wave']}'s time window opened, to {cur['win_hi']}", frame=cur["tf"], sig=sig))
                    elif cur["win"] == "past":
                        events.append(_event("window", snap["as_of"], root, f"{TF[cur['tf']]} {cur['title']}: {cur['wave']}'s time window closed {cur['win_hi']}, the wave still runs", frame=cur["tf"], sig=sig))
        in_old = set() if old is None else set(old.get("in_clusters", []))
        in_new = set()
        for c in now["clusters"]:
            if span is not None:
                hi, lo = span
                pad = 0
                if hi >= c["lo"] - pad and lo <= c["hi"] + pad:
                    in_new.add(c["id"])
                    if c["id"] not in in_old and old is not None:
                        events.append(_event("box", snap["as_of"], root, f"Price entered the magnet at {_p(c['p'])}: {c['readings']} counts", cluster=c["id"]))
        state["roots"][root] = {"tops": tops, "kept": kept_new, "in_clusters": sorted(in_new)}
    return events, state


def run(obj: dict, spec: dict, folder: Path | str | None = None) -> list[dict]:
    """Compares with the state on disk, appends the events, keeps the new state. Returns the new events."""
    base = Path(folder) if folder else base_dir()
    base.mkdir(parents=True, exist_ok=True)
    path = base / "state.json"
    try:
        prev = json.loads(path.read_text())
    except (OSError, ValueError):
        prev = None
    events, state = compare(prev, snapshot(obj, spec), obj, spec)
    if events:
        with (base / "events.jsonl").open("a") as fh:
            for e in events:
                fh.write(json.dumps(e, separators=(",", ":")) + "\n")
    data = json.dumps(state, separators=(",", ":")).encode()
    atomic_write(path, lambda fh: fh.write(data))
    return events


def read_new(folder: Path | str | None = None, mark: bool = True) -> list[dict]:
    """Events not yet seen, oldest first, and marks them seen. A byte offset, so only whole lines are read; a line being written
    now waits for the next call."""
    base = Path(folder) if folder else base_dir()
    path = base / "events.jsonl"
    seen_path = base / "events.seen"
    if not path.exists():
        return []
    try:
        offset = int(seen_path.read_text().strip())
    except (OSError, ValueError):
        offset = 0
    with path.open("rb") as fh:
        fh.seek(offset)
        raw = fh.read()
    end = raw.rfind(b"\n") + 1
    out = []
    for line in raw[:end].splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    if mark and end:
        data = str(offset + end).encode()
        atomic_write(seen_path, lambda fh: fh.write(data))
    return out


def read_all(folder: Path | str | None = None) -> list[dict]:
    base = Path(folder) if folder else base_dir()
    path = base / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out

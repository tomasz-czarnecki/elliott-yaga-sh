"""The tree as plain text."""
from __future__ import annotations

from .export import NOTE, TF_NAME
from .frames import stamp


def premise_lines(pm: dict | None) -> list[str]:
    if not pm:
        return ["Premise: none applied. Every root is searched.", ""]
    head = f"Premise ({pm['owner']}): {pm['statement']}. {pm['version']} ({pm['digest']}), degree {pm['degree']}."
    r = pm["ratios"]
    pulls = ", ".join(f"{x['k']:g} at {_p(x['linear'])} (log {_p(x['log'])})" for x in pm["pulls"])
    w = pm["window"]
    out = [head, f"  State: {pm['status']}. {pm['status_note']}",
           f"  Its levels: below {_p(pm['invalid_below']['p'])} invalid ({pm['invalid_below']['note']}); above {_p(pm['review_above']['p'])} under review ({pm['review_above']['note']}); above {_p(pm['broken_above']['p'])} broken ({pm['broken_above']['note']}).",
           f"  The correction against the five: pull 0-5 {pulls}. {w['tool']} 0-5 from {pm['top_str']}, {w['base_text']} base: minimum {w['levels'][0]['str']}, full length {w['hi_str']}; {w['x']:.2f} x the five so far.",
           f"  His five, log price and time: W2 {r['W2']['price']:.3f} of W1 in {r['W2']['days']}d ({r['W2']['time']:.2f} x); W3 {r['W3']['price']:.2f} x W1 in {r['W3']['days']}d ({r['W3']['time']:.2f} x); W4 {r['W4']['price']:.3f} of W3 in {r['W4']['days']}d ({r['W4']['time']:.2f} x); W5 {r['W5']['price']:.2f} x W1 in {r['W5']['days']}d ({r['W5']['time']:.2f} x)."]
    seen = sorted({v["rule"] for row in pm["rule_notes"] for v in row["broken"]})
    if seen:
        clean = sum(1 for row in pm["rule_notes"] if not row["broken"])
        out.append(f"  His labels against the hard rules: {clean} of {len(pm['rule_notes'])} pivot choices pass; broken somewhere: {', '.join(seen)}. Given by him, so nothing is killed: the book reads it as a lower degree or wrong pivots (FIB-T3).")
    if pm.get("time_notes"):
        out.append(f"  Time minimum: {'; '.join(pm['time_notes'])}. A strong guideline since r4, ranks lower, kills nothing; the book reads it as a lower degree or wrong pivots (FIB-T3).")
    out.append("")
    return out


def inside_lines(rows: list[dict], pad: str, keep=lambda r: True) -> list[str]:
    out = []
    for r in rows:
        labels = " ".join(f"{x['l']} {_p(x['p'])}" for x in r["labels"][1:])
        out.append(f"{pad}inside {r['wave']}: {r['name']}, {r['tf']}, fit {r['score']:.2f}: {labels}")
        out.extend(inside_lines([x for x in r["inside"] if keep(x)], pad + "  ", keep))
    return out


def _p(x: float | None) -> str:
    return "n/a" if x is None else f"{x:,.0f}"


def _pct(x: float) -> str:
    return "under 0.1%" if x < 0.001 else f"{x:.1%}"


def crossroad_line(cr: dict) -> str:
    tf = TF_NAME[cr["tf"]]
    split = cr["split"]
    if cr["shared"]:
        s = cr["shared"]
        first = f", first level {_p(s['first'])}" if s["first"] is not None else ""
        guard = f", shared while {'above' if s['d'] > 0 else 'below'} {_p(s['guard'])}" if s["guard"] is not None else ""
        head = f"CROSSROADS: all {s['n']} kept counts expect {s['dir']} next{first}{guard}"
    else:
        head = f"no shared move: {split['up']} up (first {_p(split['ups_first'])}) against {split['down']} down (first {_p(split['downs_first'])})"
    return f"  {tf:>3}  {head}. All legal: {cr['legal_up']} up, {cr['legal_down']} down; other/unclear {cr['other_share']:.0%}."


def y_lines(cr: dict) -> list[str]:
    out = []
    for y in cr["ys"]:
        tail = f", leaves {', '.join(y['survive'])}" if y["survive"] else ", none left"
        out.append(f"       Y {y['side']} {_p(y['price'])}: kills {', '.join(y['kills'])}{tail} ({y['rule']})")
    return out


def _labels(n: dict) -> str:
    fmt = (lambda t: stamp(t * 1000)[:10]) if n["tf"] == "1d" else (lambda t: stamp(t * 1000))
    return " | ".join(f"{x['l']} {fmt(x['t'])} {_p(x['p'])}" for x in n["labels"])


def axes_text(fit: dict) -> str:
    a = fit["axes"]
    return f"price {a['price']:.2f} · time {a['time']:.2f} · structure {a['structure']:.2f}"


def legs_text(n: dict) -> str:
    def one(g: dict) -> str:
        ratio = f", {g['x']:.2f} x {g['of'] if not g['of'].isdigit() else 'W' + g['of']}" if g["x"] is not None else ""
        name = f"W{g['to']}" if g["to"].isdigit() else g["to"]
        return f"{name} {g['text']}{ratio}{' (!)' if g['bad'] else ''}"
    return "; ".join(one(g) for g in n["legs"]) or "no finished leg"


def node_lines(n: dict, brief: bool = False) -> list[str]:
    pad = "    " * n["depth"]
    fit = n["fit"]
    veto = f" Failed checks: {', '.join(fit['fails'])}." if fit["fails"] else ""
    lines = [f"{pad}{TF_NAME[n['tf']]} [{n['id']}] {n['title']}. Fit {fit['score']:.2f} ({axes_text(fit)}), share {fit['share']:.1%}.{veto}"]
    if brief:
        lines.append(f"{pad}   legs: {legs_text(n)}. Running: {n['window_text']}.")
        lines.append(f"{pad}   inside: {n['inside_line'] or 'no finished wave'}.")
        wanted = _has_five if n["depth"] == 0 else _is_five
        lines.extend(inside_lines([r for r in n["inside"] if wanted(r)], pad + "   ", _has_five))
        return lines
    pad += "   "
    lines.append(f"{pad}labels: {_labels(n)}")
    lines.append(f"{pad}legs: {legs_text(n)}")
    lines.append(f"{pad}inside rule: {n['inside_line'] or 'no finished wave'}")
    lines.extend(inside_lines(n["inside"], pad))
    if n["alike"]:
        lines.append(f"{pad}same move, other labels: " + "; ".join(f"{a['name']} in {a['wave']} ({a['score']:.2f})" for a in n["alike"]))
    w = n["wave"]
    zone = sorted(n["zone"], key=lambda lv: lv["p"])
    lines.append(f"{pad}running: {w['name']} {w['dir']} from {_p(w['start']['p'])}, so far {_p(w['so_far'])}"
                 + (f"; zone {_p(zone[0]['p'])} to {_p(zone[-1]['p'])} ({', '.join(lv['pull'] for lv in n['zone'])})" if zone else "; no zone yet"))
    lines.append(f"{pad}next: {n['next']['text']}")
    inv = n["invalidation"]
    lines.append(f"{pad}invalidation: {inv['side']} {_p(inv['p'])} ({inv['rule']}): {inv['note']}")
    kn = n["kill_next"]
    lines.append(f"{pad}nearest kill: {kn['side']} {_p(kn['p'])}, {kn['dist']:.1%} away ({kn['rule']})")
    lines.append(f"{pad}time: {n['window_text']}" + (f" ({n['window']['tool']} {n['window']['pull']})" if n["window"] else ""))
    if n["crosshair_hit"]:
        h = n["crosshair_hit"]
        lines.append(f"{pad}crosshair hit: the extreme so far sits on {h['pull']}")
    if n["crosshairs"]:
        first = n["crosshairs"][0]
        lines.append(f"{pad}crosshairs ahead: {len(n['crosshairs'])}, first {stamp(first['t'] * 1000)[:10]} at {_p(first['p'])}")
    for o in n["odds"]:
        lines.append(f"{pad}odds ({o['name']}): {o['dir']} to {_p(o['target'])} ({o['pull']}) before {_p(o['stop'])}: "
                     f"{_pct(o['p'])} within {o['h_bars']} bars ({'its time window' if o['h_src'] == 'window' else 'fixed horizon'}), {_pct(o['p_nolimit'])} with no limit, R:R {o['rr']:.2f}")
    if not n["odds"]:
        lines.append(f"{pad}odds: none (no target ahead of price with an invalidation behind it)")
    good = [r for r in fit["reasons"] if r["f"] >= 0.7 and r["note"] and r["counted"]]
    bad = [r for r in fit["reasons"] if r["f"] < 0.3 and r["note"] and r["counted"]]
    lines.append(f"{pad}fits: " + ("; ".join(f"{r['note']} [{r['sec']}]" for r in good) or "nothing"))
    lines.append(f"{pad}misses: " + ("; ".join(r["note"] for r in bad) or "nothing"))
    if n["no_child"]:
        lines.append(f"{pad}one frame down: no legal parse of the running wave")
    return lines


def inside_rule_lines(tree: dict) -> list[str]:
    """How many readings the inside rule killed on each frame, and why."""
    out = ["Inside rule, readings killed per frame:"]
    for lv in tree["levels"]:
        got = (lv["stats"] or {}).get("inside")
        if not got:
            continue
        why = ", ".join(f"{k}: {v}" for k, v in sorted(got["by"].items(), key=lambda kv: (-kv[1], kv[0])))
        out.append(f"  {TF_NAME[lv['tf']]:>3}  {got['killed']} of {got['read']} read" + (f": {why}" if why else ""))
    return out


def _is_five(r: dict) -> bool:
    return r["pattern"] in ("impulse", "leading_diagonal", "ending_diagonal")


def _has_five(r: dict) -> bool:
    return _is_five(r) or any(_has_five(x) for x in r["inside"])


def render(obj: dict, roots: list[str] | None = None, brief: bool = False) -> str:
    out = [f"BTC counts, {obj['venue']}, as of the last complete 15m bar: {obj['as_of_str']} UTC, close {obj['price']:,.1f}. Rules {obj['rules_version']} ({obj['rules_digest']}).",
           *premise_lines(obj.get("premise")), NOTE, ""]
    for root in roots or list(obj["trees"]):
        tree = obj["trees"][root]
        out.append(f"=== Root {TF_NAME[root]} ===")
        out.append("Crossroads and Y's:")
        for lv in tree["levels"]:
            out.append(crossroad_line(lv["crossroads"]))
            out.extend(y_lines(lv["crossroads"]))
        stats = tree["levels"][0]["stats"]
        out.append("")
        out.extend(inside_rule_lines(tree))
        out.append("")
        out.append(f"Tree. Root: {stats['legal']} legal readings in {stats['states']} states. Kept: top {len(tree['levels'][0]['nodes'])}; other/unclear {stats['other_share']:.0%} of fit. Pairings dropped by FIB-T8, the whole tree: {stats.get('unpaired', 0)}.")
        by_parent: dict[str | None, list[dict]] = {}
        for lv in tree["levels"]:
            for n in lv["nodes"]:
                by_parent.setdefault(n["parent"], []).append(n)

        def walk(pid):
            for n in by_parent.get(pid, []):
                out.extend(node_lines(n, brief))
                walk(n["id"])

        walk(None)
        out.append("")
    return "\n".join(out)

"""His hand-labelled counts against the engine, on the real bars. A regression test that the engine can reproduce his
reading (master plan, gold/), not ground truth. Skipped where the collector's data is absent. The data is cut at each entry's
own date, so that later bars cannot move it."""
from __future__ import annotations

import pytest

from ewave.counts.config import load_config
from ewave.counts.frames import load_frames, to_ms
from ewave.counts.gold import _candidates, _rule_lines, check_enumerate, check_inside, check_kept, check_rank, check_tree, load_gold, run_entry
from ewave.counts.nest import Builder
from ewave.counts.premise import load_premise
from ewave.counts.rules import IMPULSE

CFG = load_config()
GOLD = {e.id: e for e in load_gold()}
FOUR = GOLD["4h-impulse-2026-07-to-09"]
MACRO = GOLD["1d-impulse-2022-to-2025"]


@pytest.fixture(scope="module")
def frames():
    try:
        full = load_frames(CFG.raw["venue"], CFG.pivots["atr_bars"], CFG.pivots["rsi_bars"])
    except Exception as err:  # no data on this machine
        pytest.skip(f"no bars: {err}")
    if not full["1d"].ts or full.as_of_ms < to_ms(FOUR.as_of):
        pytest.skip("the bars do not reach the gold date")
    return full.upto(to_ms(FOUR.as_of))


def test_the_enumerator_produces_his_impulse_at_4h(frames):
    b = Builder(frames, CFG)
    got = check_enumerate(FOUR, b)
    assert got.passed
    rows = [c for c, _, _ in _candidates(FOUR, b) if c.pattern == IMPULSE and FOUR.on(c.labs, c.pts)]
    twos = {c.pts[2].price for c in rows}
    threes = {c.pts[3].price for c in rows}
    assert twos == {62240.0, 62505.1} and threes == {81499.9, 82276.6}  # all four variants he allows


def test_unconstrained_it_ranks_first_among_the_readings_that_cover_it(frames):
    got = check_rank(FOUR, Builder(frames, CFG))
    assert got.passed, got.lines
    assert got.lines[0].lstrip().startswith("rank 1 ")


def test_every_kept_reading_with_room_shows_it(frames):
    got = check_tree(FOUR, frames, CFG, load_premise())
    assert got.passed, got.lines
    assert not [line for line in got.lines if "does not show" in line]


def test_macro_impulse_survives_without_the_premise(frames):
    got = check_kept(MACRO, frames, CFG)
    assert got.passed, got.lines


def test_his_exact_macro_pivots_are_on_the_board_now_that_time_only_ranks(frames):
    """r3 held them back on the time minimum (W4 took 77 days of a W3 of about 500). r4 made that a guideline (FIB-T3 is filed
    under CONVENTION), so what stops a variant now can only be the inside rule, and the check says which."""
    assert not [line for line in _rule_lines(MACRO, frames, CFG) if line.split(":")[-1].strip() != "passes every rule"]
    got = check_kept(MACRO, frames, CFG)
    assert any("his exact pivots too" in line for line in got.lines), got.lines


def test_each_of_his_waves_is_read_for_what_is_inside_it(frames):
    """Each variant of each entry, wave by wave. A regression record, not a target: the rule was not set by this."""
    got = check_inside(FOUR, Builder(frames, CFG))
    assert got.passed and got.lines[0].lstrip().startswith("4 of 4")
    macro = check_inside(MACRO, Builder(frames, CFG))
    assert macro.passed, macro.lines


def test_the_premise_tree_is_what_he_asked_for(frames):
    b = Builder(frames, CFG, load_premise())
    tree = b.build("1d")
    roots = tree.levels[0].nodes
    assert len(roots) == CFG.tree["keep_root"] == 3
    assert CFG.tree["keep_child"] == 1
    for n in roots:
        assert n.count.pts[0].price == 126150.0 and n.count.s == -1
        chain = n
        for _ in range(3):
            assert len(chain.children) == 1
            chain = chain.children[0]


def test_every_entry_passes_as_a_whole(frames):
    premise = load_premise()
    for e in GOLD.values():
        got = run_entry(e, frames.upto(to_ms(e.as_of)), CFG, premise)
        assert got.passed, [c.lines for c in got.checks if not c.passed]

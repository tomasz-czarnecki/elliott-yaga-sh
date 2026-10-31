"""The prompts of the LLM counter test. BTC and null windows get exactly the same text. Only the chart block differs.

The rulebook is read at run time from the read-only source copy and is never written into the repo.
"""
from __future__ import annotations

import os
from pathlib import Path

RULEBOOK = Path(os.environ.get("BAKE_RULEBOOK", "/opt/data/cache/scratch/elliott_research_r1/sources/newwave-ew-compact.md"))

PATTERNS = "impulse | leading_diagonal | ending_diagonal | zigzag | flat_regular | flat_running | flat_expanded | triangle | combination"

COUNT_PIVOT = """{
  "segments": [
    {"pattern": "<one of the patterns>", "direction": "up|down (direction of this structure's first wave)", "degree": "<one word>",
     "labels": [{"label": "0", "pivot": 0}, {"label": "1", "pivot": 0}]}
  ],
  "current_wave": "<the wave now unfolding, e.g. 3 or C>",
  "next_move": "up|down",
  "invalidation": {"price": 0.0, "side": "below|above", "rule": "<short, cite the section>"},
  "target_zone": {"low": 0.0, "high": 0.0, "rule": "<short, cite the pull and the level>"},
  "p_target_before_invalidation": 0.0,
  "confidence": 0.0
}"""

COUNT_RAW = COUNT_PIVOT.replace('{"label": "0", "pivot": 0}, {"label": "1", "pivot": 0}',
                                '{"label": "0", "bar": 0, "price": 0.0}, {"label": "1", "bar": 0, "price": 0.0}')
COUNT_IMAGE = COUNT_PIVOT.replace('{"label": "0", "pivot": 0}, {"label": "1", "pivot": 0}',
                                  '{"label": "0", "time": "<as on the x axis>", "price": 0.0}, {"label": "1", "time": "<as on the x axis>", "price": 0.0}')

MASKED = ("Masking: prices are multiplied by an undisclosed constant and dates are moved by an undisclosed number of days, so "
          "that you work from the numbers and not from memory of what happened next. All price ratios and bar spacing are unchanged.")
REAL = "Dates and prices are the real ones."


def chart_block(w: dict, condition: str) -> str:
    head = [f"Instrument: BTC/USD spot. Chart timeframe: {w['tf'].upper()}.",
            MASKED if w["masked"] else REAL,
            "The last bar is now. Nothing after it exists yet.",
            f"Last bar: {w['last_time']}, close {w['last_close']:.2f}, rsi11 {w['last_rsi']}."]
    if condition == "pivot":
        head.append(f"Pivots come from a causal zigzag: a swing is listed only after price reversed by at least {w['k']} x ATR(14). "
                    "Smaller swings are not shown, so the inside of a leg is not visible here. The row marked provisional is the "
                    "running extreme of the unfinished leg, not a confirmed pivot. rsi11 is RSI(11) at the bar of the pivot, the line "
                    "of the NewWave TDI; its bands and signal are not given. Two pivots can share one bar (a long-range bar).")
        return "\n".join(head) + "\n\n" + w["pivot_table"]
    if condition == "raw":
        head.append("OHLC bars follow, all of them, UTC. rsi11 is RSI(11) on the close, the line of the NewWave TDI; its bands and "
                    "signal are not given.")
        return "\n".join(head) + "\n\n" + w["raw_table"]
    if condition == "image":
        head.append("The attached chart shows the candles (log price) and RSI(11) under them. Read the levels from the axes.")
        return "\n".join(head)
    raise ValueError(condition)


def prompt(w: dict, condition: str, rulebook: str | None = None) -> str:
    book = rulebook if rulebook is not None else RULEBOOK.read_text()
    shape = {"pivot": COUNT_PIVOT, "raw": COUNT_RAW, "image": COUNT_IMAGE}[condition]
    ref = {"pivot": 'A label names a row of the pivot table by its "pivot" number. Label only rows that exist.',
           "raw": 'A label names a bar by its "bar" number and gives the price of the extreme you mean (that bar\'s high or low).',
           "image": 'A label gives the time as on the x axis and the price as read from the y axis.'}[condition]
    return f"""You count Elliott waves with the NewWave rulebook below, for a BTC trader. You have no tools. Work only from the data given here.

<rulebook>
{book}
</rulebook>

<chart>
{chart_block(w, condition)}
</chart>

Task: follow the rulebook's section 9 protocol on this chart. Give the most likely count and the best alternate, each with its invalidation level and the target zone of the next move. Count only what has printed and project one structure ahead. If you cannot form an honest count, set "primary" to null and "other_unclear_share" to 1.

Answer with one JSON object and nothing else: no prose, no code fence.

{{
  "primary": <count object or null>,
  "alternate": <count object or null>,
  "other_unclear_share": 0.0,
  "reasoning": "<at most 60 words>",
  "recognised_period": "<none, or the real dates you think this chart comes from>",
  "data_note": "<none, or at most 20 words on anything odd about this data>"
}}

A count object is:
{shape}

Patterns: {PATTERNS}.
Labels: 0,1,2,3,4,5 for impulses and diagonals; 0,A,B,C for zigzags and flats; 0,A,B,C,D,E for triangles; 0,W,X,Y,X2,Z for combinations. Label 0 is the start of the structure. Give a label only for a wave that has ended or for the running extreme of the wave now unfolding. {ref} Use more than one segment when one structure follows another, in time order; put the structure that is still open last.
"confidence" is your probability that this count is the one that plays out. primary.confidence + alternate.confidence + other_unclear_share must equal 1.
"p_target_before_invalidation" is your probability that price reaches the target zone before it reaches the invalidation price, within the next {w['horizon']} bars of this timeframe. All prices are in the units of the chart above."""


__all__ = ["prompt", "chart_block", "RULEBOOK"]

# Checklist dials v2.7 — FINAL freeze

Built from frozen v2.6 (v2.6 files untouched). Round 4 reads (blind charts 41–50, jumpiest-quintile common stocks, 2020–24) produced 2 new items + 1 borderline, so per the rule they are folded into v2.7, frozen with no further rounds.

## What changed vs v2.6
Exactly 3 new history facets (rows added only; every v2.6 row is byte-identical and in the same order):

| type / variant | facet | answers |
|---|---|---|
| candles / OHLC | gap_given_back | {gap_up,gap_down}x{given_back,partial,held}+none |
| phase_list / 3ATR_legs | pump_fade_cycles | pump_fade:{0,1,2,3+}x{lower_peaks,higher_peaks,mixed,n/a} / dump_recover:{0,1,2,3+}x{higher_troughs,lower_troughs,mixed,n/a} |
| range_position / HiLo_window | range_box | {upper_half,lower_half}x{<5,5-10,>10 ATR}x{0-1,2-3,4+ crossings}+none |

All have bull/bear mirrors, ATR14-relative sizes, the standard leak rule (answer for D uses only bars < D), and the variant's existing unit/lookback grid (gap_given_back is a short facet like gap_up).

**range_box rule:** range_box rule: walk back from D-1 over strict pivots (PIV). Box = [min L, max H] of the first 4 alternating pivots (2 highs + 2 lows) counted back from D-1. Extend the stretch backward bar by bar while every close stays inside [box_low-0.5ATR, box_high+0.5ATR]; the stretch starts at the first bar after the last close outside. Box top/bottom are then max H/min L of the stretch. Valid only if stretch >=10 bars and has >=4 alternating pivots, else none. Height = (top-bottom)/ATR14(D-1). Full crossing = a move from a close in the bottom 25% of the box to a close in the top 25% (or top->bottom); counted alternately. Bull/bear mirror = side of the box where C[D-1] sits (upper half = bull, lower half = bear). All bars < D.

Generator fix: the history-lever "duplicate of facet kind" reason now joins kinds deterministically (`sorted(...,reverse=True)`), reproducing the v2.6 bytes regardless of PYTHONHASHSEED (v2.6 output varied with hash seed on 3 rows).

HISTORY_LEVER is unchanged (identical sha to v2.6): history families are counted per variant, and no variant was added.

## Question totals
- v2.6: 6,599 base + 7,989 history = **14,588**
- v2.7: 6,654 base + 7,989 history = **14,643** (+55: gap_given_back 21, pump_fade_cycles 17, range_box 17)
- dial rows: 433 → 436; facet-count checks failing: 0

## sha256
- `DIAL_TABLE_v2.7.csv` 41bad6b6313591b04988ab44b376078e86d1c8f81812caef5805aef6ed851e30
- `HISTORY_LEVER_v2.7.csv` 33c66afb7ce8be6fc2b2f637901110785a3c9bf25ad436e44fd4084aca07d704
- `gen4_v2.7.py` c5d15d6a118bbf84f4d9c1bfe511a951518204eee3b5ddca732b9867d7ba3f24
- `counts.json` c0bd4fcd7dea28117d12d339d9dc7978cab827f45075add17a43394004bf8be2

## Regenerate
```
cd dials/v2.7 && python3 gen4_v2.7.py   # writes DIAL_TABLE_v2.7.csv, HISTORY_LEVER_v2.7.csv, counts.json
```

## Drive
- DIAL_TABLE_v2.7.csv: https://drive.google.com/file/d/1YxIeX9Cj0ObE940KSnn0w99HCr_FBWOa/view
- HISTORY_LEVER_v2.7.csv: https://drive.google.com/file/d/1Vyrx_89o5nIvCScK2NB9pq8eLnexiUaa/view
- gen4_v2.7.py: https://drive.google.com/file/d/1eUx4fcdZ4WBTlrSBPbG6V8yTM2rWGi7O/view

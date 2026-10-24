# Review: theme-radar PR #17 — F4TR insider casebook 2020–24 (Kimi, 2026-10-24)

Reviewed `research/casebook/build_cases.py` and `mcap100_v1/build_cases_mcap100.py` on branch
`research/casebook-2020-24`. 2020–24 only; sealed-data discipline verified in code.

## Done right

- **Sealed data:** every chunk asserted `2020..2024`, `D.date.max() < '2025-01-01'`, prices
  filtered `<= 2024-12-31` — the hard rules are enforced by asserts, not habit.
- **Tags integrity:** tags file sha asserted (`201f39f3…`) before use.
- **Fees:** 30bp each way on both exits, exactly the house convention.
- **No overlapping-trade inflation:** consecutive YES days collapsed to one case (first day),
  run length recorded.
- **Controls:** same-day equal-weight mean of buyable stock-days, per exit — same spirit as
  the engine's benchmark, computed over the same filtered universe.
- **Entry realism:** entry at open of D+1; target gap-through fills at the open
  (`max(open, target)`); h10 exits at close.
- **Context features** are all `shift(1)` — bars through D−1 only. No peeking in the features.

## Findings

### 1. Circularity risk in the "confirm 2023–24" split (the big one)

The 10 cells in `W` are "pass-bar F4TR row ids". If the pass-bar determination used the full
2020–24 scorecard (or anything that saw 2023–24), then splitting cases into
discovery/confirm and quoting confirm-window performance is **in-sample for the confirm
window** — the cells passed the bar partly *because* 2023–24 went their way. That doesn't
invalidate "no edge found" (the conclusion is negative, and circularity usually *flatters*),
but it means the confirm split carries no independent evidence either way.
**Fix:** re-derive pass-bar cells using 2020–22 data only, then evaluate 2023–24 once.

### 2. Censoring counts bars, not sessions

Outcomes require `rem >= 15` *rows* after the signal row, where "next bar" is the next row in
the price file. If a ticker misses sessions (halt, data gap), the post-gap bar is treated as
the next session and the 15-bar window silently spans the gap. The checklist-engine's
NOT_READY rule requires a bar on **every session D..D+29** — stricter and more honest about
execution. The casebook can therefore keep cases the engine would censor, with slightly
optimistic outcomes after gaps. Not a leak; an execution-realism gap. Quantify by counting
cases whose 15-row window spans a >3-session calendar gap; expect small.

### 3. Fund/shell filter uses a 2026-09 snapshot on 2020–24 rows

`snap_2026-09-29.csv` industries decide which 2020–24 tickers are funds/shells. Industry
status is sticky, so the misclassification rate is likely low — but it's a point-in-time
violation in principle. If the casebook is ever re-run, use an industry source with dates
(or accept and document the assumption).

### 4. Minor

- `nomatch` (signal days with no price row) is reported (good) — confirm it's near zero and
  not concentrated in one year.
- MCAP100 addendum: `Sh['date']=Sh.filed+1` then `merge_asof(backward)` — shares filed before
  the entry open are correctly excluded; cap sanity filters reasonable.

## Verdict

Sound engineering and clean data discipline. The one methodological fix that matters is (1):
until the pass-bar cells are re-selected on 2020–22 only, treat all confirm-window numbers
as descriptive, not evidentiary. Conclusion "no edge found" is likely robust anyway — a
circularity-flattered window still found nothing.

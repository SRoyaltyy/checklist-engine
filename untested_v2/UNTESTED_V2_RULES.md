# UNTESTED_V2 — rules (pre-registered; committed BEFORE any result was computed)
PRACTICE 2020–24 only, **HINT, SURVIVORS-ONLY**. No bar after 2024-12-31 read (filtered on load + asserted). 2025–26 sealed.
Price file universe_2020_survivors.parquet sha fb9bbe69…ef337 (asserted). qa/redundancy/feats.py not used.

## Scope
The 1,660 rows marked TOO_FEW in untested_v1/untested_results_v1.csv (86 master + 1,574 map v5.1; 1,123 never fired on v1 cells),
using the same answer column as v1 (column `col`). Distinct columns = tests.

## Universe (change vs v1)
EVERY buyable stock-day 2020-01-01..2024-12-31: story_q/panel.parquet minus Taskforce drop_list_v2, with bars D..D+20 ≤ 2024-12-31.
Answers are read from the engine's full-universe chunks (checklist_brainstorm/engine/universe/chunks: per-stock JG/NB/TR files,
per-date SHARED file — same reader as lookalike_features/build.py attach_npz). Master price/volume rows (MPV) are recomputed with the
ported formulas in master_pv.py on the full price history (bars before D only). Code 2 = YES, 1 = NO, 0 = NR.
A stock-day with no stored answer counts as NR. Market-cap floor ($100M) NOT applied (no point-in-time share file) — flagged.

## Trades, controls, labels (unchanged from v1)
Trade = buyable stock-day with answer YES, entry open D. Control = mean of all buyable stock-days that date.
30bp/side. 10-day: open D → close D+9. EXIT_RULE_V1: +20% take-profit (gap fills at open), no stop, else day-15 close.

## Pass bar (per label; row passes under either label, both reported)
2020–22 and 2023–24 each: n ≥ 30, win > 55%, mean excess vs control > 0; plus 2020–22 BH q < 0.10 on excess
(date-clustered bootstrap, 500 draws, seed 13) over the GLOBAL family = 10,060 prior + 2 × (tests here); prior p treated as 1.
A row under 30 YES trades in either period = TOO_RARE_TO_TEST.

## Never-fires check (zero YES on every buyable stock-day 2020–24)
Mechanical rule, then a hand read of the definition vs the stored answers for each indicator group:
- BUG if (a) every sibling row of the same indicator (same map indicator text / master data_type+variant, all buckets and BUT variants)
  is also zero-YES while the row is answered NO (not NR) on ≥ 1 day — a partition of buckets cannot all be empty on real data, so
  missing data is being coded NO; or (b) the hand read finds the stored answer contradicts the written definition.
- NR on every day → BUG (no data reader output; should have been BLOCKED).
- Otherwise GENUINELY_RARE (definition reachable but never met on buyable days).
Nothing here is a keep; any pass is a live-day HINT only.

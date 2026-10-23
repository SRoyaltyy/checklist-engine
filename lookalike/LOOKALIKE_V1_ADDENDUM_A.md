# LOOKALIKE_V1 — Addendum A (registered 2026-10-23 ~12:55 HKT, BEFORE any feature build, matching or outcome join)
Additions requested by Cyrus via the War room after f1cc345. Not part of tonight's 21:00 HKT freeze. 2020–24 only; 2025–26 sealed.
Where this addendum conflicts with LOOKALIKE_V1.md, this addendum wins.

## A1. Extra matching blocks (each its own equal-weight block, bars strictly before D)
8. RSI14 (Wilder) of the last bar (1 dim).  9. MACD(12,26,9) histogram / scale (1 dim).  10. RVOL = volume of last bar / mean volume of the 20 bars
before it, log (1 dim).
11. Trajectory (how the answers changed day by day): for the six continuous indicators RSI14, %B, MACD hist/scale, trend slope, dip depth,
log RVOL — value at last bar minus value 5 bars earlier, and minus value 10 bars earlier (12 dims).
Note stated now: path_bank_v2 yes/no answers are stored only for the target day of each sampled row, not for each prior day, so day-by-day
trajectory is built from the underlying indicator series (same idea as path_bank_v2 ph2_* streak/flip items), not from stored answer files.

## A2. Outcomes (replace the two combo exits). All net of 30bp each way, entry open of D, price bars <= 2024-12-31 only.
- HOLD_h for every h = 1..21 trading days (exit close of day h; day 1 = D) — 21 exits.
- TP_X: sell at +X% (fills at X%, or at the open if it gaps above), else close of day 21; X in {5, 10, 15, 20, 30} — 5 exits.
Rows without 21 forward bars <= 2024-12-31 are dropped (as before). Excess = r minus same-date mean of filtered rows, per exit.
- Also reported (not a test): share of twins whose max high within 21 days reaches >= +10% from entry, vs the same share for all filtered rows.

## A3. Winners vs losers inside twin sets
For every discovery-period pick at K=100 under HOLD_10, split its twins into winners (r>0) and losers; for each path_bank_v2 / New Bot / halt
yes/no item stored for the library rows (combo pb_bits / nb2_bits / halt_bits) plus master-list items "downtrend 2 months earlier"
(close 21 bars before D-21 > close at D-21... i.e. 42-bar-ago close > 21-bar-ago close) and "setup rising while price flat"
(%B up >= 0.2 over 10 bars while |10-bar return| < 2%), compute pooled YES share winners minus losers; two-sided z test clustered by target.
Items with BH q < 0.05 are then checked once on check-period picks (same direction and p < 0.05 required). Missing = unknown, excluded.

## A4. Luck correction
Twin trade tests: 6 K x 26 exits x 2 periods = 312. Winner/loser items: every item tested counts. Family = 14,075 + 312 + #items.
Supersedes the 24-test family in LOOKALIKE_V1.md.

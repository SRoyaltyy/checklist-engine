# FINDINGS_FREEZE_V1 — look-alike winner-vs-loser differences, frozen for lock index v9 (PRACTICE 2020–24, HINT only)
Frozen Fri 2026-10-23 HKT. No bar after 2024-12-31 read. Price file sha fb9bbe69…ef337. Tradable filter: Taskforce drop_list_v2 (ETF rule partial; market cap NOT applied).

## What counts as a finding
An item × setup (setups: chart pass all-6, Q5, Q7, Q8 inside chart pass) that, with symmetric 1:1 same-date winner–loser pairs (audit-fixed pairing),
was discovered on 2020–22 pairs (BH q<0.1, winner-favour ≥5pp from 50%) AND confirmed on 2023–24 pairs (same direction, >5pp, n≥30, BH q<0.1 over the discovered set).
Global BH family: every item tested (sheet/map rows, master.csv ported rows, path bank v2, NEW rows, lookback grid, path-level v2).
Two outcome labels: (a) 10-day: open D → open D+10, 30bp/side, beat same-day matched controls; (b) Taskforce EXIT_RULE_V1 (sha 215de513…97d3): open D, +20% take-profit (gap fills at open), no stop, else day-15 close, 30bp/side, vs same-day controls.
Excluded: look-alike shape and nearest-neighbour rows (failed on 2023–24); chart-picture story questions (no separation after the pairing fix).

## Counts
- Rows in `FINDINGS_FREEZE_V1.csv`: **1,503** — pass under 10-day label: 1,498; pass under exit v1: 5; pass under both: 0.
- Loser-leaning 1,229 / winner-leaning 274.
- Big-move / high-volatility LOSER set (`family_bigmove_highvol_loser`): 745 rows.
- Q5 longer base (`q5_longer_base`, path2_base_len top tercile, winner-leaning, 55.5% both periods): 1 row.
- SURVIVOR-BIAS RISK flags (near-low / near-high / drawdown items): 320 rows. The price data (2020–24 AND sealed 2025–26) is survivors-only; only live trading days after the lock can clear these.

## Under exit v1 vs the 10-day label
The 10-day findings mostly do NOT survive the exit-v1 label: of 1,498 10-day passes, 1,125 keep the same direction under v1 on the full period but only 19 are BH-significant, and **none** passes discover+confirm under v1. The big-move/high-vol loser set weakens most — a +20% take-profit rewards volatile names (they hit the target), offsetting their 10-day underperformance. Exit-v1 passes (5, none also in 10-day):

| setup | item | definition | direction | v1 disc favour % (n) | v1 confirm favour % (n) |
|---|---|---|---|---|---|
| chartpass_all6 | ph2_pctbmean_20_ge0p8 | mean %B(20,2) over lb >= 0.8 (lb=20) :: mean (C-lowerBB)/(4sd20) >= 0.8 | winner-leaning | 55.2 (1038) | 55.7 (763) |
| q5_in_all6 | ph2_abv10frac_25_ge0p7 | share of lb closes above SMA10 >= 0.7 (lb=25) :: mean C>SMA10 >= 0.7 | winner-leaning | 56.0 (634) | 57.7 (470) |
| q5_in_all6 | ph2_abv20run_20_ge20 | longest run of consecutive closes above SMA20 within lb >= 20 (lb=20) :: max consecutive C | winner-leaning | 56.9 (513) | 58.3 (415) |
| q5_in_all6 | ph2_xc20up_20_eq1 | close crossed above SMA20 within lb == 1 (lb=20) :: any(C>SMA20 & C[-1]<=SMA20[-1]) == 1 | loser-leaning | 43.5 (597) | 42.0 (478) |
| q8_in_all6 | ph2_pctbmean_25_ge0p7 | mean %B(20,2) over lb >= 0.7 (lb=25) :: mean (C-lowerBB)/(4sd20) >= 0.7 | winner-leaning | 63.2 (185) | 65.8 (114) |

## Columns (CSV)
item, found_on (every row was discovered on 2020–22 pairs only; 2023–24 served only to confirm — safe for Taskforce's 2020–22-only selection), setup, source, definition (exact formula / strict definition from its source list), coding (YES vs NO, or top vs bottom tercile), direction,
pass_10d, pass_exit_v1, n / winner-favour % / q for discover (2020–22) and confirm (2023–24) under each label (effect size = favour − 50 pp),
flag_SURVIVOR_BIAS_RISK, family_bigmove_highvol_loser, q5_longer_base.

## Caveats
HINT only. Many rows are correlated cuts of one feature family (and Theme Radar |N variants duplicate each other) — count families, not rows.
Market-cap rule not applied; ETF rule partial. Sector/industry rows use today's Finviz map.

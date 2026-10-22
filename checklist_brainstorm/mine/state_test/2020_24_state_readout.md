# 2020–2024 STATE test (v2 method). EXPLORATORY, survivors only, no 2025–26 outcomes touched

Method: funds/CEFs/shells excluded (Finviz Industry, 2026-09-29 snapshot). Entry at next open, 0.20% round trip, dividends added on ex-dates (capped at 20%), date-clustered 95% CIs, n ≥ 30 dates. Edge = return minus the same-date average of non-fund stocks. Lean fifths are pooled across 2020–24 (L5 ≥ 0.619). Asterisks = Grok's `ctx_opp|stk|*` columns.
**Dropped for comparability:** 2020–2023 have no `COUNTS2_TR__Financial` file, so non-fund Financial rows in those years lack theme-radar votes and asterisks. Leaving them in would have turned "zero asterisks" into "Financial stock" (it inflated L5&ast0 from about 15k to 134k observations). Those rows are excluded in every year. 4.63M stock-mornings remain.
**Fresh warnings:** exact `qw_fresh` from `{y}__FRESH__<sector>` files for 2023, 2024 (except Financial) and 5 sectors of 2022. Everything else uses the v2 count-difference approximation (labelled in the `fresh_src` column). Jump z is stock-level, as locked: quiet-warning fraction vs its trailing 20-day mean/std, ≥ 1.5, blank under 10 days of history.

## Headline (2020–24 combined; 5-day edge vs average, after fee)
| state | dates / obs | 5d edge | 95% CI | years negative |
|---|---|---|---|---|
| **Strong bull (L5) + warning jump** | 1,068 / 39,657 | **−0.32%** | −0.50 / −0.13 | 4 of 5 (2024 is +0.08%) |
| Strong bull (L5), all | 1,211 / 930,402 | −0.04% | −0.10 / +0.01 | |
| L5 + zero asterisks (Cyrus's core state) | 1,029 / 15,424 | −0.15% | −0.32 / +0.03 | 2020 −0.41% (significant); others mixed |
| L5: zero asterisks minus many asterisks (paired by date) | 1,027 dates | −0.18% (5d) / −0.05% (1d) | −0.48 / +0.13 | |
| L5 + fresh warnings high vs low | about 1,190 dates each | −0.06% vs −0.03% | both CIs cross 0 | |

Per year, L5 + jump 5d edge: 2020 −0.68% (CI −1.14 / −0.22), 2021 −0.36%, 2022 −0.47%, 2023 −0.27% (CI −0.55 / −0.00), 2024 +0.08%.

## Exit test (buy at next open; sell at the next open after the first warning jump, cap 10 days; vs fixed 5-day; 0.20% fee)
| entry | jump exit minus 5-day hold | 95% CI | dates |
|---|---|---|---|
| L5 + zero asterisks | −0.05% | −0.74 / +0.64 | 1,024 |
| all L5 (random 60k sample per period) | +0.05% | −0.11 / +0.20 | 1,159 |
| (extra) bearish-lean exit vs 5-day, all L5 | +0.02% | −0.15 / +0.19 | 1,159 |
2020 was the only year where the jump exit clearly helped (+0.54%, CI +0.10 / +0.98). Median exit came after 8–10 days.

## Plain English
Across five years, when a stock looks most bullish but its quiet warnings suddenly spike above their normal level, it lags the average stock by about a third of a percent over the next week. That held in 4 of 5 years. It is the first result that backs Cyrus's "warnings appearing = rally breaking" idea. Everything else, including "strong bull + zero asterisks", shows no edge. Selling on a warning jump doesn't beat just holding 5 days. A warning jump says "don't buy this one", not "sell what you hold".

## James Outlier / Interaction check: RETRACTED (13:40 HKT)
The all-NR SMCI stock-level Outlier/Interaction cells are James's sector rows plus Grok's 240 analyst rows, which are deferred/not-ready by design. This is not a wiring bug. The earlier bug claim is withdrawn.

## Caveats
Survivors only. 5- and 10-day windows overlap, so CIs are somewhat narrow. Many states have now been tested across v1 to v3. Grok's 240 analyst rows, New Bot's 650 rows and James's sector rows are not in the counts, and the Outlier/Interaction stock rows are effectively missing (above). Fund list is from a 2026 snapshot.

Files: `2020_24_state_table.csv`, `2020_24_paired_ast.csv`, `2020_24_exit_test.csv`, `states_{2020..2024}_v3.parquet`, `log_{y}_v3.csv`, `build_y.py`, `analyze_v3.py`, `outlier_check.py`, `v3_out.txt`.

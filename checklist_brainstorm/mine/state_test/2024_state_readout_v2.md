# 2024 STATE test v2 (EXPLORATORY, 2024 training data, survivors only, no 2025–26 data touched)

## Plain English
1. **Funds removed.** The v1 "strong bull + zero asterisks" edge mostly disappears once funds are taken out. It drops from +0.21% to **+0.05%** over 5 days versus the average stock (CI −0.29% to +0.38%, 229 dates, 2,934 stock-mornings).
2. **Fresh warnings and warning jumps don't sort winners from losers** inside the strongest-bull fifth. Every split is within about ±0.3% of the average stock, and every CI crosses zero.
3. **Selling early on a warning jump doesn't help.** It gives the same result as just holding 5 days. The difference is +0.09% (CI −0.33% to +0.51%) on the zero-asterisk entries and +0.02% (CI −0.19% to +0.23%) on all strong-bull entries.

## 1. Fund exclusion
Funds were identified using the Industry column of the Finviz snapshot `/workspace/snap_2026-09-29.csv`. Industries beginning with "Exchange Traded Fund", "Closed-End Fund" (Debt, Equity or Foreign) or "Shell Companies" (SPACs) were removed. 3,920 tickers and 892,402 stock-mornings came out, all from the Financial sector: 3,562 ETFs, 193 debt CEFs, 105 equity CEFs, 29 foreign CEFs and 31 shells. "Asset Management" was **kept**, because it holds operating managers and BDCs (BLK and similar). 11 tickers in the "Unknown" sector aren't in the snapshot and were kept. The remaining universe is 1.18M stock-mornings. Lean fifths were recomputed on that universe (L5 is lean ≥ 0.621). See `v2_fund_exclusion.csv`.

## 2. Fresh warnings and warning jump (New Bot's locked definitions)
- **Fresh** = quiet-warning YES today that were NO yesterday, per lens. The counts files hold per-lens totals, not per-question answers, so I approximate fresh as the sum over lenses of max(0, YES today − YES yesterday). That's a lower bound whenever some questions flip off while others flip on. Fresh divergence is the same sum over divergence lenses only.
- **Jump** = (today's stock-level quiet-warning fraction − trailing 20-day mean, excluding today) / trailing 20-day std. A "jump" means ≥ 1.5. It's left blank with fewer than 10 days of history.
- **Return** = 5-day hold, next open to open, minus 0.20%. Edge is measured against all non-fund stocks on the same date, with date-clustered 95% CIs.

| state (within strongest-bull fifth L5) | dates / obs | 5d edge vs avg | 95% CI |
|---|---|---|---|
| L5 (all) | 246 / 234,964 | −0.05% | −0.16 / +0.05 |
| L5 & zero asterisks | 229 / 2,934 | +0.05% | −0.29 / +0.38 |
| L5 & fresh high (top third) | 245 / 50,012 | +0.11% | −0.07 / +0.28 |
| L5 & fresh low | 244 / 116,142 | −0.08% | −0.22 / +0.06 |
| L5 & fresh-divergence high | 240 / 52,573 | −0.05% | −0.20 / +0.11 |
| L5 & jump (z ≥ 1.5) | 224 / 9,591 | +0.06% | −0.36 / +0.48 |
| L5 & no jump | 236 / 217,880 | −0.07% | −0.17 / +0.04 |
| L5 & zero asterisks & jump | 59 / 126 | −0.04% | −1.20 / +1.12 |
| L5 & zero asterisks & fresh high | 142 / 443 | +0.16% | −0.52 / +0.85 |

There is no sign that a fresh warning or a warning jump marks a strong-bull rally breaking.

## 3. Exit test (buy at next open; 10bp per side = 0.20% round trip; date-clustered CIs)
| entry | rule | mean after fee | 95% CI | hit rate | n dates / obs |
|---|---|---|---|---|---|
| L5 & zero asterisks | fixed 5-day | −0.08% | −0.50 / +0.35 | 46% | 225 / 2,911 |
| | sell at next open after first jump, cap 10 days | +0.02% | −0.50 / +0.54 | 46% | |
| | jump exit minus fixed 5-day | **+0.09%** | −0.33 / +0.51 | | |
| | (extra) sell after first bearish-lean morning (< 0.5), cap 10 days | 0.00% | −0.50 / +0.50 | 44% | |
| All L5 | fixed 5-day | −0.02% | −0.31 / +0.27 | 46% | 241 / 232,807 |
| | jump exit | −0.00% | −0.27 / +0.27 | 44% | |
| | jump exit minus fixed 5-day | **+0.02%** | −0.19 / +0.23 | | |
| | bearish-lean exit minus fixed 5-day | −0.02% | −0.24 / +0.19 | | |

About half of entries (53–55%) see a jump before the 10-day cap. The median exit comes after 8–9 days, so the jump rule mostly behaves like a longer hold, not a quick bail-out.

## Caveats
- Fresh warnings use the count-difference approximation described above.
- Grok's 240 analyst rows, New Bot's 650 rows and James's sector rows aren't in the counts.
- Survivors only; one year; about 40 more comparisons on top of v1, so false positives are expected.
- Overlapping 5- to 10-day holds make the CIs somewhat too narrow.
- Entries in the last 11 sessions of 2024 are dropped from the exit test, because no 2025 prices were loaded.

Files: `2024_v2_fresh_jump_states.csv`, `2024_v2_exit_test.csv`, `v2_fund_exclusion.csv`, `states_2024_v2.parquet`, `build_v2.py`, `analyze_v2.py`, and `PRELOCK_2025_26.md`.

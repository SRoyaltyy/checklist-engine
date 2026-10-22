# 2020–24 full re-run (v5). EXPLORATORY, survivors only, no 2025–26 touched

## Exact rule as tested (for PRELOCK)
- **Universe:** survivors-only stock universe (`universe_2020_survivors.parquet`). Funds removed where the Finviz 2026-09-29 Industry starts with "Exchange Traded Fund", "Closed-End Fund" or "Shell Companies". **Non-fund Financials are now included in every year** (via `{y}__COUNTS2_TR__Financial[_partN]`; `*_partN` wildcard for STK, TR and FRESH).
- **Morning lean:** `lean_bull_share_all` (TR file). **Top fifth = lean ≥ 0.6205** (pooled 2020–24 80th percentile; freeze this number).
- **Stock-own warning spike:** per stock, q = Σ qw_yes / Σ qw_ready over the stock-scope FRESH lenses (grok + james + theme-radar). z = (q_today − mean(q, previous 20 rows)) / std(same 20 rows); blank if fewer than 10 prior rows. **Spike = z ≥ 1.5.**
- **Stock+market spike:** same formula on q = (stock yes + market yes) / (stock ready + market ready), with market yes/ready from `{y}__FRESH_MKT_ADDON` joined on date.
- **Market spike:** same z on the market-only q, one value per date.
- **Trade:** morning d → buy the open of the next session (d+1), sell the open of d+6 (5-day hold). Dividends with ex-date inside the hold are added back, capped at 20% of price. Cost is **0.20% round trip** (10bp per side). Returns with |r| > 200% are dropped as junk.
- **Score:** edge = trade return − same-date average of all non-fund stocks. 95% CI clustered by date. Need ≥ 30 distinct dates. The market spike vs IWM uses one observation per date.
- **FRESH source:** real Grok FRESH files everywhere except **2020 Technology, Unknown and Utilities** (143,665 rows), which use the count-difference estimate (labelled `approx_countdiff`).

## Results: 5-day edge vs average, after fee
| state | 2020–24 pooled | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|
| Top fifth, all | −0.04% (−0.10 / +0.01), 1,212 dates | −0.32% | +0.01% | +0.05% | −0.02% | +0.10% |
| **Top fifth + stock-own spike** | **−0.29% (−0.46 / −0.11)**, 1,073 dates, 44,397 obs | −0.52% (sig) | −0.33% | −0.48% | −0.27% (sig) | +0.09% |
| Top fifth + stock+market spike | **−0.26% (−0.46 / −0.07)**, 1,092 dates, 40,016 obs | −0.61% (sig) | −0.04% | −0.58% (sig) | −0.36% (sig) | +0.31% |
| Top fifth on market-spike dates | −0.28% (−0.49 / −0.06), **161 dates** | −0.89% | −0.33% | −0.45% | −0.23% | +0.35% |

Spike vs no-spike, pooled: −0.29% vs −0.03%.

## Market spike vs IWM (one observation per date; IWM 5-day, next open to open, after fee)
| | spike dates | IWM spike | IWM no spike | difference (95% CI) |
|---|---|---|---|---|
| 2020–24 | 175 | −0.48% | +0.06% | −0.55% (−1.26 / +0.16) |
| 2020 / 21 / 22 / 23 / 24 | 35 / 33 / 33 / 36 / 38 | −0.94 / +0.86 / −0.47 / −1.16 / −0.61% | | only 2023 significant (−1.40%) |

## Plain English
Adding the Financial stocks back and using the real fresh-warning files barely moves the result. The most bullish stocks whose own warnings suddenly spike lag the average stock by about **0.3% over the next 5 days**. That was true in 4 of 5 years, and 2024 is the exception. Adding the market-wide warnings to the spike gives almost the same number (−0.26%). On their own, market spikes hint at a weaker week for IWM (−0.55%), but that isn't statistically clear.

## Changes vs the v3 readout
- v3 stock-only spike was −0.32% (CI −0.50 / −0.13) without Financials. v5 is −0.29% (CI −0.46 / −0.11) with Financials and real FRESH files. Same conclusion.
- The Outlier/Interaction "wiring bug" claim is **retracted**. Those blanks are James's sector rows and Grok's 240 analyst rows, which are deferred by design.

Caveats: survivors only; 5-day windows overlap; many tests have been run across v1–v5; New Bot's 650 rows and James's sector rows are not included; the fund list comes from a 2026 snapshot.
Files: `2020_24_v5_spike_states.csv`, `2020_24_v5_mkt_iwm.csv`, `states_{y}_v5.parquet`, `log_{y}_v5.csv`, `build_v5.py`, `analyze_v5.py`, `v5_out.txt`.

# Checklist redundancy audit: merged_draft_v7.csv (unpublished, internal QA)

Run 2026-10-22 ~03:40 HKT. Read-only: no owner files were changed. Grok Bot did the audit.

## 0. Things found in the file itself
- The file has **21,308 rows**, not 21,320.
- **128 rows reuse 64 ids**, all in Grok Bot's Finviz block (for example FV-GB-2449..). Each reused id points to a *different* rule, so the ids have to be renumbered.
- **There are no SEC fails-to-deliver rows in v7** (0 matches), even though Manager Bot said that FTD stays in.
- James's root map comes from /workspace/james_row_sources.csv, with FRED relabelled to Treasury etc.

## 1. Rows per root raw input (full sheet, all 21,308 rows) -> rows_by_root.csv
| root input | rows | owners |
|---|---|---|
| Price/volume: stock/ETF daily OHLCV | 11,139 | Taskforce 7,620 · James 3,215 · New Bot 202 · Grok 102 |
| Price/volume: Finviz fields that are just OHLCV math (SMA dist, 52w, perf, gap, rel vol, beta) | 2,056 | Theme Radar 1,694 · Taskforce 336 · New Bot 26 |
| Price/volume + earnings dates | 212 | NB 112 · TF 60 · TR 40 |
| Futures/commodities/FX/crypto daily bars | 3,000 | James 2,974 · NB 26 |
| Treasury yields (home.treasury.gov) | 1,220 | James |
| Options-implied (VIX family indices, CBOE put/call) | 618 | James 542 · NB 36 · TF 40 |
| Breadth (constituent OHLC, Stockcharts) | 384 | James |
| Finviz snapshot: fundamentals/analyst/ownership | 1,494 | TR 858 · Grok 560 · NB 76 |
| Yahoo analyst rating actions | 288 | Grok |
| CFTC COT | 320 | Grok |
| Nasdaq halts | 172 | TF 160 · NB 12 |
| Finviz after-hours | 112 | NB |
| Official macro releases / Fed | 82 | James |
| Fed funds futures (FedWatch/ZQ) | 75 | James |
| Calendar/event dates | 64 | James 28 · NB 36 |
| FINRA/RegSHO short volume | 72 | TF 60 · NB 12 |
| SEC FTD | 0 | n/a |

**About 13,400 rows (63%) are arithmetic on one stock's daily bars.** If you count the bars of other instruments too (SPY/sector ETFs, futures, FX, crypto, VIX, yields as candles), it's about 18,300 rows (86%). Only about 3,000 rows (14%) come from a dataset that isn't a price chart.

## 2. Price/volume families (rows): pv_family column
Big-move/outlier candles 3,906 (James 2,168, TF 948, TR 730) · volatility/Bollinger/ATR 1,649 · candle patterns 1,452 (TF) · trend/MAs 1,332 · momentum/RSI/oscillators 1,250 · volume/money flow 762 · returns vs market/sector 728 · streaks/exhaustion 591 · position-in-range/52w/ATH 479 · statistics 300 · earnings-anchored 126 · performance windows 120 · gaps 114 · other 596.

The rows are mostly generated from grids:
- Taskforce: 340 base measures × 20 lenses = 6,800 rows.
- James: one "outlier candle" template × 13 instruments × size × age × location = 5,200 rows.

## 3. Measured overlap (point-in-time sample)
- **Sample:** 50 large US stocks plus SPY/sector ETFs/VIX/futures/Treasury, Yahoo daily bars and Treasury par yields, 2019-01-02..2025-12-31 (1,760 sessions × 50 = 88,000 stock-days).
- **Point-in-time:** every value uses data up to the D-1 close and is shifted to session D. Rolling windows are trailing only.
- **Rows tested:** 466 (Taskforce 230, James 170, Theme Radar 60, New Bot 5, Grok 1), spread across every family that can be computed from bars. 7 of them never fire (or always fire). Each was tested at its first timeframe (1d) only.
- **Untested roots:** Finviz snapshot, COT, FINRA, analyst-action and halt rows can't be tested on 2019-2025, because the saved snapshot history starts 2026-08. They are reported structurally only.

| measure | result on 459 live sampled rows |
|---|---|
| clusters at kappa >= 0.8 (80% agreement beyond chance, the requested cutoff, complete linkage) | 437 |
| clusters at abs(phi) > 0.7 | 418 |
| clusters at abs(phi) >= 0.5 / >= 0.3 | 353 / 250 |
| eigen effective number of signals (participation ratio of the phi matrix) | **141** |
| saturation fit of effective N vs sample size, extrapolated to the whole sheet | **~200 independent signals in all 21k rows** (rough; flattens after ~400 rows) |

Per root in the sample (views = sampled rows → independent at kappa 0.8 / at abs(phi) 0.3 / effective N). The sheet total is in the first number:
- Stock/ETF OHLCV (sheet: 11,139): 260 views → 242 / 140 / **77**
- Finviz OHLCV restatements (sheet: 2,056): 92 → 92 / 70 / **58**
- Futures/FX/crypto bars (sheet: 3,000): 65 → 65 / 48 / **48**
- Treasury yields (sheet: 1,220): 28 → 28 / 18 / **19**
- Options-implied (sheet: 618): 14 → 14 / 10 / **12**

How to read this: strict near-copies (above 0.7) between two *randomly chosen* rows are uncommon. Instead, the redundancy shows up as many weak-to-moderate overlaps. That's why 459 views behave like about 141 independent ones. Rare event rows look "independent" only because they hardly ever fire, so independent doesn't mean useful.

### Worst redundant families / lenses (family_overlap.csv, lens_out.txt, pairs_phi_ge_0.5.csv)
- **Taskforce lens effect.** Same lens on a different indicator gives mean abs(phi) 0.19, while the same indicator through a different lens gives 0.13. So the lens matters more than the indicator. The worst lens is **div_volume (BUT)**: mean abs(phi) 0.54, and 45% of pairs are above 0.5. It reduces to "up day on heavy volume" whatever the indicator is. Examples: CMO14 vs Up-volume share gives phi 0.98, and Volume heatmap z vs C*V/avg gives 0.96 (div_price BUT). Next are div_volume, div_price (BUT) and change, each with 16–22% of pairs above 0.5.
- **MA/oscillator twins.** PPO hist vs MACD hist (change) gives 0.93. Close vs SMA200 vs Distance from 52w low gives 0.93. Close vs WMA20/TRIMA20/EMA20-ATR/SMA20/RSI14 (change) give 0.83–0.87.
- **James VIX family.** VIX vs VIX3M 1-session change gives 0.85, and the options root is the most self-similar, with effective N 12 from 14 rows. Credit (HYG/LQD) and rates rows also overlap heavily (mean abs(phi) 0.46 / 0.34).
- **Cross-owner.** The Theme Radar Finviz price fields are the same quantities Taskforce computes from bars: gap gives phi 0.70, rel volume 0.68, change-from-open 0.63. Grok's 560 Finviz analyst rows and Theme Radar's 858 Finviz fundamental rows read the same snapshot fields (Recom, Target, EPS growth), but there isn't enough history yet to test them.

### Exact / structural duplicates (whole sheet)
- **2,621 James rows are "[BUT twin of the same condition]"**: the YES condition is identical to the base row and only the reading flips. Each pair is one signal, so 2,621 rows add nothing.
- **520 James outlier rows can never fire.** One example: "green outlier exactly 1 session ago AND yesterday's close < the outlier candle's low". When the outlier is yesterday's own candle, its close can't be below its own low or above its own high. That's 0 YES days in 7 years.
- **New Bot event rows:** the BUT mirrors carry "YES if same difference <= -3%", which doesn't apply to an event flag. 32 rows have text identical to their base.
- **89 rows across all owners** share identical rule text with another row.

## 4. Thin root inputs worth adding
- **Single-stock options** (IV rank, skew, put/call, OI): there are 0 rows. The "options" root is only VIX-family indices plus total CBOE P/C. Nightly saving only started 10-20, so these can't be backtested yet.
- **SEC FTD:** 0 rows in v7 (dropped in the merge?).
- **FINRA short volume:** 72 rows. **Official macro:** 82. **Fed funds futures:** 75. **Calendar:** 64. **Halts:** 172.
- **Fundamentals/analyst:** 1,494 + 288, but only about 2.5 months of point-in-time history.
- **Never present:** insider filings (Form 4, dated), 13F, ETF flows/creations, credit spreads beyond HYG/LQD price, and economic surprise.

## Files
- rows_by_root.csv: every row with root, pv_family, and the dup/impossible flags.
- clusters.csv: the 466 sampled rows with cl_kappa80 (primary), rep_kappa80 (suggested representative = highest mean kappa to its cluster), cl_phi70, yes_rate and dead flag.
- per_root_sample.csv, family_overlap.csv, pairs_phi_ge_0.5.csv
- Raw data for Manager Bot recheck: raw_sample_signals.parquet (date×ticker × 466 yes/no), pairs.npz (phi, kappa, jaccard, agreement, n), bars.pkl / bars2.pkl / tsy20*.csv (inputs)
- Code: feats.py, engine.py, run.py, analyze.py, more.py, lens.py, final.py, roots.py

## Caveats
- Only 1d timeframe tested.
- div_sector uses the SPDR sector ETF, and rank_market ranks within the 50-stock universe, not the full 11.6k.
- Taskforce candle-pattern BUT is taken as the bearish sign.
- New Bot and Grok are barely covered empirically (6 rows).
- James's rows that use "BUT stock's own prior-session return..." include the stock condition.

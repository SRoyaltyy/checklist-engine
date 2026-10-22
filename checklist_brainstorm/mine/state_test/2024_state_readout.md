# 2024 STATE test: first readout (EXPLORATORY, 2024 = training data, survivors only)

## The short version
We split every stock-morning in 2024 into "states" based on how bullish the checklist leaned, how many YES answers went against that lean (Grok's asterisk / `ctx_opp` columns), how many quiet warnings fired, and how many loud bearish signals fired. Then we checked whether stocks in each state did better than the average stock over the next 1 and 5 days, after a 0.20% fee.

**Result: mostly no edge.** Almost every state lands within about ±0.1% of the average stock. Cyrus's main idea (strong bull lean, no contrary asterisks and few quiet warnings means better moves) points the right way. It earned about +0.2% over 5 days versus the average stock, but that is **not statistically clear**. **Quiet warnings did NOT weaken bullish states in 2024.** If anything, stocks with *more* divergence-type quiet warnings did slightly *better*.

## Top states by after-fee 5-day edge vs the all-stock average on the same dates (n ≥ 30 dates)
| state | what it means | n dates / obs | 5d edge vs avg | 95% CI (date-clustered) |
|---|---|---|---|---|
| L1 & ast_hi & div_hi | bearish lean, many contrary asterisks, many divergence warnings | 60 / 6,170 | +0.45% | −0.05% to +0.96% |
| L1 & lb_mid | bearish lean, medium loud-bearish count | 176 / 54,603 | +0.24% | +0.08% to +0.40% |
| L5 & ast0 & qw_lo | **Cyrus's hypothesis**: strongest bull lean, zero asterisks, few quiet warnings | 230 / 3,904 | +0.21% | −0.02% to +0.44% |
| L5 & ast0 | strongest bull lean, zero asterisks | 233 / 4,516 | +0.19% | −0.03% to +0.41% |
| div_hi (any lean) | top third of divergence quiet warnings | 251 / 705,867 | +0.10% | +0.06% to +0.15% |

Worst: **L1 & ast_hi & qw_lo** (bearish lean, many asterisks, few quiet warnings) at **−3.1%** over 5d vs the average (57 dates, only 289 obs, CI −5.1% to −1.1%). It is small and could be a fluke, but it is the strongest bearish-mirror signal.

Raw after-fee returns are negative almost everywhere (for example, the all-stock 1d average is −0.24%). That comes from the 0.20% fee plus open-to-close drift, so the "edge vs average" column is the fair comparison.

## Do quiet warnings weaken bullish states? (paired by date, strongest bull lean L5)
- Few vs many quiet warnings: +0.15% (1d) and +0.35% (5d) in favour of few. **Not significant** (5d CI −0.22% to +0.92%).
- Few vs many *divergence* warnings: **−0.30% at 5d** (CI −0.58% to −0.01%). Many divergence warnings did *better*, the opposite of the hypothesis.
- Zero vs many contrary asterisks: **+0.28% at 1d** (CI +0.05% to +0.51%). This is the one piece that supports Cyrus's idea, and only at 1 day (5d +0.34%, not significant).
- Rally length: from a strong-bull morning, the median time to the first bearish signal (lean < 0.5 or loud-bearish count in the top third) is 8 days with zero/few asterisks and few warnings, versus 5 days with many quiet warnings. So warnings do mark rallies that **end sooner**, even though the returns don't show it.

## Market-wide states vs IWM (one observation per date)
A bullish market lean did *not* help IWM: 5d −0.12% vs +0.53% for a bearish lean (about 82 dates each, SEs about 0.3–0.4%). Mid lean with many divergence warnings was the worst: −1.26% 5d (33 dates, hit rate 27%). This is a small sample and only one year, so treat it as a hint only.

## How states were built
- Lean = `lean_bull_share_all` (TR file), split into quintiles L1 (most bearish, below 0.457) to L5 (most bullish, 0.621 and above).
- Asterisks = sum of Grok's `ctx_opp|stk|*` columns (not recomputed). They are counts in the dozens, not 0/1/2, so the bins are 0 / 1–17 / 18+. `ctx_opp|mkt|*` was 0 every day in 2024. Most asterisks come from theme-radar (mean 13.6 of 14.0).
- Quiet warnings fire on every row (median 79 YES), so "absent" never happens. Bins are terciles of the total (`qw`) and of the divergence-lens subset (`qw_div`). Loud bearish is binned the same way.
- Labels: survivors split-only prices plus dividends on ex-dates (capped at 20% of price and flagged; 0.007% of rows flagged). Entry is the **next session's open** after the morning (conservative, no lookahead). Exit is the close 1 or 5 sessions later, minus 0.20%. Only 2024 prices were loaded, so the last few days of December have no 5d label. No 2025–26 data was touched. fullscan `ohlc.parquet` was not used.
- Luck controls: n ≥ 30 distinct dates (flag `enough_dates`), date-clustered SEs, and edge measured vs the same-date all-stock mean. Processing ran one sector at a time.

## Caveats
- **Missing rows:** Grok's 240 analyst rows (not-ready), New Bot's 650 rows (no engine yet) and James's sector rows (add-on pending) are not in these counts.
- About 80 states were tested, so 2 to 4 "significant" results are expected by pure chance. Nothing here is a confirmed signal.
- 5d windows overlap day to day. Date clustering doesn't remove that serial overlap, so the 5d CIs are somewhat too narrow.
- Survivors only (stocks still listed in 2026): this flatters returns and especially hurts the bearish-side read.
- Lean is computed with quiet warnings counted as bear votes, so lean and quiet-warning bins overlap.
- The Financial sector (1.08M of 2.07M rows, mostly funds) dominates the pooled averages.

## Files
- `/workspace/checklist_brainstorm/mine/state_test/2024_state_table.csv`: all stock states, with 1d/5d raw and excess means, SEs, 95% CIs, hit rates, n_dates
- `2024_quietwarning_paired.csv`: paired-by-date comparisons
- `2024_rally_length.csv`: days to the first bearish signal
- `2024_market_states_iwm.csv`: market-wide states vs IWM
- `build_states.py`, `analyze.py`, `states_2024.parquet` (per stock-morning states and labels)

# Methodology: the checklist scanner

This file explains, in plain English, what the scanner is for, how it works, and what we tried before. It replaces the older version of this file (see git history). Related docs: [README.md](README.md), [DATA_INDEX.md](DATA_INDEX.md), [buyable filter](buyable_filter_v1/BUYABLE_FILTER_V1.md), [lookalike](lookalike/LOOKALIKE_V1.md), [combo model](combo/COMBO_MODEL_V1.md), [path bank](path_bank/README.md), [takeaways](dials/TAKEAWAYS.csv).

## 1. Goal
- Find checklist question + answer pairs that make money on average per trade.
- **Expected profit** = win% × average win − loss% × average loss. Fees of 30bp each way are taken off first.
- Every trade uses **exit rule v1**: sell at +20% if it gets there, otherwise sell on day 15.
- A result only counts if it beats what the market did on the same days.
- There is a **minimum win rate**. It starts at 40%, and we also test 35, 40, 45 and 50%.
- Later, the good answers get combined into one model that estimates expected profit.
- Code scans every stock. Nobody reads charts by eye.

## 2. Data
- **Survivors only.** Stocks that were delisted are skipped. Prices come from a Stooq backfill ([history10y/build_stooq.py](history10y/build_stooq.py)) plus the history we already had.
- **Tradeable stocks only.** On each day D, a stock is dropped if it fails the fullscan liquidity filter or is worth under $100M, using split-fixed share counts. Peer groups get the same filter.
- For 553 tickers whose market cap looks wrong, only the dollar-volume filter is used. `integrity/quarantine.csv` is always honored.
- Every question is yes/no or picks from a fixed list of labels. No reading of free text.
- **No peeking.** Answers for day D use data up to the close of D−1, plus pre-open data. A leak test checks this.

## 3. Question tree
- Questions are nested like folders: data type → timeframe → derivative → how it's analysed.
- **v2.7.1** has **15,093 questions**: 6,654 base and 8,439 history. Answer file sha `d8adbb46…`.
- **Cutoff grid v2.7.2.2** has **232 cutoffs** and **154,667 versions**, swept one at a time (commit `67844a6`).
- The cutoffs are the thing being tested. Cyrus's rule: try every definition.

## 4. Outcomes
- For every case: the 30-day close, the best and worst point within 30 days, and the exit rule v1 result.
- For each question + answer, the tallies keep: n, wins, average win, average loss, total profit, the share of profit from the top 5% of trades, and the market's result over the same days.

## 5. Time splits
- **Discover** on 2020–22.
- **Confirm** on 2023–24, with nothing changed.
- **2025–26 stays sealed.** It gets one shot at the very end.

## 6. Plan
- **Step A:** full 2020–24 run at default cutoffs, keeping full rows. Output goes to Drive in parts of about 1GB.
- **Step B:** sweep the cutoff grid on 2020–22, tallies only.
- **Step C:** confirm the winners on 2023–24.
- **Then:** build the combining model.

## 7. Luck bar (James)
- 650,660 tries means a result must be about 5.4 standard errors out. That is roughly 2,500–2,900 setups.
- Measure the gap over the market, not over 50%. Cap how much any single trade can move the average.
- Also run a softer check, and label each result by which check it passed.

## 8. Disk and resources
- Keep 7GB free between 17:00 and 21:00 HKT, and 2GB at other times. If free space is below that, pause between parts.

## 9. What we tried before
- **YES/NO miner pilot.** An AAPL + NVDA smoke test found 0 clears.
- **2020–24 PRELOCK result.** Top-bull fifth plus a stock's own QW spike z≥1.5 gave −0.29% over 5 days (CI −0.46 to −0.11). See `PRELOCK_2025_26.md`, sha `8f1940e3…`.
- **Lookalike / twin matching.** Match the whole 20–30 day picture, the green:red body ratio, Bollinger position and dip depth. See [lookalike/](lookalike/LOOKALIKE_V1.md) and [chart picture formulas](drive_docs/CHART_PICTURE_V2_FORMULAS.md).
- **Rally "tug of war" and probability cloud.** Ways of framing a rally as buyers vs sellers, with a spread of possible outcomes.
- **Theme Radar F4TR insider casebook.** 2,154 cases, no edge found. See [theme-radar PR #17](https://github.com/SRoyaltyy/theme-radar/pull/17) and [practice_results/2020_24_f4tr_score.md](practice_results/2020_24_f4tr_score.md).
- **Short interest and options.** 110 tests, 0 passed.
- **Old smoke test was invalid.** It used made-up history labels. That is now fixed.
- **7-stock smoke test.** 12,285 columns in 192s. It was a pipe test only, with no win/loss results.

## 10. Known gaps
- About 1,262 columns have no data source yet: sector/theme peers, anchored VWAP, volume profile, Fib swing, events and score path.
- `pump_fade_cycles` and `multi_year_position` crash.
- About 200 base cutoffs are not wired up.
- "Last 2 pivots" is not a cutoff yet.

## 11. Takeaways and luck check (James)
_To be filled in by James on this branch._

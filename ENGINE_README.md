# Checklist engine (dials 1-4 + history lever) — plain-words guide

**Status (Fri 23 Oct 2026, ~14:10 HKT):** the code is built and smoke-tested on 6 stocks. It has **not** been run on the full list. It has **not** been joined to any outcomes, and no edge or backtest stats have been run. That waits for Cyrus to sign off on the cutoffs and for the 23:00 HKT unlock.

## What it does
For every stock on every trading day D from 2020 to 2024, it answers a long list of fixed questions about the chart. Example: "Did RSI6 go from oversold to normal over the last 20 bars?" Every answer is a small number, and `codebook.json` turns each number back into its label. **-1 means "can't answer"**, usually because there isn't enough history yet.

## Rules it follows
- **No peeking.** The answer for day D only uses bars from before D. Each answer is worked out at the close of the day before and then shifted forward one day.
- **2025-26 stays sealed.** Data is cut at 2024-12-31, and the code never loads anything later.
- **Train/check split.** The `split` column says `discover_2020_22` or `check_2023_24`.
- **Survivors-only universe.** Stocks that were delisted (for example NKLA and MULN) aren't in the price file, so they get no rows.
- **Filter.** `passes_filter` is true when the stock's market cap on D-1 is unknown or at least $100M, AND its median 20-day dollar volume is at least $1M. The $1M liquidity line is our own guess and can be changed. Rows that fail the filter are kept but flagged, so nothing gets deleted.
- **History flags.** `history_short_252` / `history_short_756` mean fewer than 1 or 3 years of bars before D. Stocks that only start in 2020 have no 2018-19 warm-up bars.
- **Sizes are in ATR.** Every size is measured in the stock's own ATR14, its typical daily move.
- **RSI.** RSI uses 6/12/24, with 14 as a variant. The 30bp fee isn't used here because this engine only produces answers, with no trades.

## Phase list (new in 2.6)
The chart is cut into phases:
- A leg ends when price turns back by 3×ATR from its high or low.
- Ten or more bars without a 3-ATR move is a **base**.
- The labels are up_run, down_run, shock_up/down (3 ATR in 3 bars or fewer), base, retest_high/low (ends within 0.5 ATR of an old phase's high or low), and break_up/down (a close more than 1 ATR outside the last base).

The questions it asks:
- the last phase
- the last 3 phases in order
- the number of phases in the window
- the last phase compared with the one before it: length, size, volume and speed

## History lever (HISTORY_LEVER_v2.6, `keep` rows)
Each variant gets one "main line", for example the RSI value, the distance from the MA in ATR, or RVOL. The same 14 history questions are then asked of that line: speed, route, time since an extreme, retests, stage, vs own past, lead/lag vs SPY, and so on. These columns start with `H|`.

## Output
- One row per stock per day.
- Answer columns are named `variant|facet|1d|lookback` or `H|variant|history_value|1d|lookback`.
- Other columns: ticker, date, bars_before_D, the history_short flags, mcap_D1, dollar_vol_med20_D1, passes_filter and split.

## How big this is
The table counts 14,588 questions across all bar sizes and lookbacks. This build covers **daily bars only, at lookbacks 10/20/60** (plus 1 for "as of now" questions), which comes to **2,023 answer columns** (868 dial + 1,155 history).

- Dial rows built: 309 of 433.
- History keep rows built: 385 of 532.

## Not built yet, and why
- **Bar sizes 2-20 days.** Not built; it would multiply the size by about 10.
- **Analyst actions.** The table marks these NOT_READY.
- **Earnings, form4, short interest, halts.** These need a careful "known before D" date join. Deferred.
- **Sector and theme peers.** Today's sector label leaks the future, and themes need clustering first.
- **rank_route.** Needs the whole cross-section ranked each day.
- **Need a pivot-level engine first:**
  - Fibonacci, volume_profile, prior_pivots (including fail_fail_break), old_ranges_breakdowns and unfilled_gaps
  - most of base_and_run (pause_vs_run and shelf_depth are built), and drawdown's second_leg/capitulation/shape
  - touch_order, VWAP tests, swing_count, hl_base_breakout, staircase_shelves, cup_handle/flag, wick_evolution/run_history, and bounce_ceiling
- **checklist_score_path.** Needs the finished checklist first.
- **History questions on the variants above.** These have no main line yet.
- **Lever 5 extra rows.** Not built, as instructed.

## Known simplifications
- RSI divergence compares the two halves of the window, not strict pivots.
- "Float" is the SEC shares-outstanding count, not true float.
- Breadth is the share of survivor stocks above their 50-day average. Survivors-only means it's a little too rosy.
- The pre-holiday question uses the exchange's published holiday calendar.

## Running it
- Smoke test: `python3 engine.py --tickers AAPL,KO` writes `answers_2020_24/smoke.parquet` plus `codebook.json`.
- Full run: `--all`. Not authorised yet.
  - Single process: about 5-6 s per stock, so roughly 18 CPU-hours for about 11.7k stocks, or about 2.5-3 h with 7 workers. The multiprocess wrapper still needs to be added.
  - Output would be about 14.7M rows and about 8 GB, and the box has only 13 GB free.

## v2.7 update (23 Oct 2026, HKT)
- Now reads DIAL_TABLE_v2.7.csv (sha 41bad6b6…1e30, verified), HISTORY_LEVER_v2.6 (unchanged, 33c66afb…d704), gen4_v2.7.py (c5d15d6a…3f24, verified). v2.7 = v2.6 + 3 rows, nothing else changed.
- New questions (facets_v27.py), windows 10/20/60:
  - gap_given_back: find the latest gap in the window. Did yesterday's close give the gap back (back past the gap-day open), partly give it back, or hold it? 7 answers.
  - range_box: is the stock stuck in a box (at least 2 swing highs + 2 swing lows, 10 or more bars)? How tall is the box in ATR, how many times did price cross from bottom to top, and which half is it in now? 18 answers + none. Swing points are "strict pivots" (higher/lower than 2 bars each side), and the box has to sit inside the window.
  - pump_fade_cycles: written as TWO columns, pump_fade and dump_recover. Count the 3-ATR pumps that then gave back half or more, and say if the peaks got lower. It's rare inside 60 bars because the pump has to start inside the window.
- Split step (integrity/mcap_fix.py). Our prices are "adjusted": every past price is rescaled for splits, even splits in 2025-26. Example: MVIS did a real 1-for-15 reverse split on 2026-08-03, so its 2021 prices show as $150-400. SEC share counts are the real numbers from that date. Multiplying the two made a nonsense market cap. Now we:
  1) turn the adjusted price back into the real traded price (undo every split after that day),
  2) scale the SEC share count for any split between the count date and that day,
  3) market cap = real price × shares.
  Round-number and sub-$1 questions, and float turnover, now use the real traded price and volume. Using 2025-26 split dates this way is metadata, not outcomes. Checks: MVIS Apr-2021 = $2.8B, TSLA Jul-2020 = $200B, AAPL Jul-2020 = $1.58T.
- Integrity (integrity/): compared our monthly closes with Yahoo's adjusted closes for every ticker, 2018-2024. Results: ok 8,684 · no reference 2,995 (mostly ETFs or names with no Yahoo history before 2025) · MISMATCH 33. MVIS = right company, it's just the 2026 split (fixed above).
  quarantine.csv actions:
  - exclude (33, the engine skips them): price doesn't match Yahoo, usually by a clean split-size ratio.
  - mcap_unknown (18): implied mcap above $4T (ADR vs ordinary share counts, or units). Mcap is treated as unknown, so the filter uses dollar volume only.
  - flag (553): SEC share count jumped more than 8× in one month with no matching split. Kept, with mcap_suspect=True.
  - keep_unverified (10: BLFS CCO CYCN LPSN PSKY QNCX QRVO SLP VTAK WBD): Yahoo's history for these starts 2026-07-17, so there is no outside price to check against. These look like real long-lived names, so they are kept.

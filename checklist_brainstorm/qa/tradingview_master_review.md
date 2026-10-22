# Independent review: tradingview_master.csv
Reviewer: Grok Bot · 2026-10-22 03:21 HKT · reviewed the corrected file (M001–M293, last modified 03:20:37 HKT). Snapshot: qa/tradingview_master.snapshot.csv
Recount from the file: 293 rows = 78 n/a (crypto/futures) + 162 have + 40 missing-fetchable + 13 missing-needs-new-data. Of the 215 stock items, 25 are raw and 190 derived. **The corrected counts check out.** The earlier 155/47 figures are superseded; 7 rows moved to "have", including Chandelier, Ulcer, Mass index, RVI and ADR.

## 1. Completeness: PASS (one gap)
I parsed TradingView's Built-in Indicators help folder (support/folders/43000587405), which has 209 links and 208 unique names. Every name is in the master by exact title. That covers the full list, not just a sample of 30, including Pivot Points High/Low and Standard, RSI divergence, Technical Ratings, Seasonality, Trend Strength Index, Woodies CCI, TWAP, Volume Delta and Zigzag.
**Gap:** New Bot is right that there is no "Compare symbol" item (overlaying SPY or a sector ETF on a stock). It should be added as **have**: Taskforce has `Return vs SPY`, `Return vs sector ETF`, `Beta vs SPY 60d` and `Correlation vs SPY 60d`, and James has ratio rows such as IWM/SPY.

## 2. "Covered" accuracy: PASS on existence, 4 mapping errors
I checked a random sample of 25 "have" items (seed 7). All 25 have real rows. Examples: Williams %R(14); StochRSI(14,14,3,3) %K; Realized vol 10d vs 60d; Close vs TEMA20; Connors RSI (3,2,100); CDLDARKCLOUDCOVER; CDLTASUKIGAP; Upper wick share; Range vs ATR14; Theme Radar SMA50 vs SMA200; Perf % window; Return on Equity; Cash/sh and Current Ratio; Short float % and Short ratio; Taskforce Short % of float and Days to cover.
I also matched all 142 Taskforce-cited "have" items by phrase against the 365 unique Taskforce variants. Every one resolves.
Mapping fixes needed (the items are covered, but the master points at the wrong row):
- Inverted Hammer points to `Hammer`. `CDLINVERTEDHAMMER` exists.
- Evening Doji Star and Morning Doji Star point to `CDLDOJISTAR`. `CDLEVENINGDOJISTAR` and `CDLMORNINGDOJISTAR` exist.
- Linear Regression (channel): the actual row is `Close vs regression stdev channel (all data to D-1)`.
- Version label: the master cites "Taskforce v10.2", but the inbox file is `trading-bot-taskforce.csv`, and the only versioned copy is v10.1.compact.

Mis-labelled "missing":
- The 4 named items (Chandelier, Ulcer, Mass index, RVI) are fixed, and so is ADR.
- These are still marked missing but are near-duplicates of rows we have. They are not new signals:
  - Trend Strength Index ≈ `Linear regression R2 20` + slope.
  - Woodies CCI ≈ `CCI20`.
  - Envelope ≈ `Close vs SMA20` (%).
  - Volatility Stop ≈ Chandelier / Supertrend side.
  - Rising/Falling Window ≈ `Overnight gap %` / `CDLGAPSIDESIDEWHITE` (not identical).
- Genuinely absent from Taskforce variants: Tweezer, Split event, Seasonality, Renko/Kagi/Line break/P&F, chart patterns, Technical Ratings.

## 3. Look-ahead / repaint risk: PARTIAL, needs code proof
Every Taskforce row says `known_before_open=Yes` (43,368 of 43,368). The only "code" is the definition table in /workspace/tf/indicators.py (198 lines, names and formulas). **I found no implementation**, so no row's computation can be verified yet. The venv includes pandas_ta, whose `zigzag` repaints.

| Item | Our row | Verdict |
|---|---|---|
| Williams fractal | "+1 if bar D-3 is a 5-bar fractal" | OK by definition: bars D-5..D-1 are all known at D-1 close |
| Zigzag (have) | "days since last 5% zigzag low/high" | **RISK.** The last pivot only confirms after a 5% reversal. Must date the leg from the confirmation bar, and must not use pandas_ta.zigzag |
| Pivot Points High Low → "swing pivots" / AVWAP from last 5-bar swing pivot | anchor = last 5-bar pivot | **RISK.** The pivot needs 2 bars after it. The anchor must be chosen among pivots confirmed by D-1 |
| Auto Fib Retracement → Fibonacci zone of 10/20/60/252d swing | rolling max(H)/min(L) through D-1 | OK. Rolling window, no pivot confirmation |
| Pivot Points Standard → classic pivot R1/S1 | from D-2 HLC vs D-1 C | OK |
| VWAP Auto Anchored (52w high/low) | anchor = running extreme | OK if the running extreme is through D-1 |
| RSI divergence ("Tired run") | new high without RSI high | OK if it uses rolling highs. TradingView's own version uses pivots and repaints |
| Heikin Ashi streak | recursive HA through D-1 | OK. Doesn't repaint |
| Buildable: auto fib extension, auto trendlines/pitchfork/key levels, chart patterns, Elliott, Rob Booker pivots/Ziv ghost, Knoxville | all pivot-based | **RISK when built.** They must use only pivots confirmed by D-1. TradingView's drawings repaint |

Required before any of these is used: Taskforce shows the implementing code for zigzag and swing-pivot rows, plus a test that truncates history at D-1 and recomputes: the value must be identical.

## 4. Redraws / composites: FLAGGED
- Same candles redrawn (no new information beyond the OHLCV we already use): Renko, Kagi, Line break, Point & figure, Heikin Ashi (have), Hollow candles, Line/Area/Baseline, Columns, High-low, Volume candles. Recommend these are not counted as gaps.
- Composites of existing rows: Technical Ratings (MAs plus oscillators we have), MA Ribbon, MovingAvg Cross / 2Line Cross, Moving Averages, Bollinger Bars, BBTrend (two BB widths), RCI Ribbon, Multi-Time Period Charts.
- So of the 40 "buildable" items, about 12 are redraws or composites and about 5 are near-duplicates (§2), which leaves roughly 23 that could carry new information. These are my estimates from reading the rows, not a computed count.

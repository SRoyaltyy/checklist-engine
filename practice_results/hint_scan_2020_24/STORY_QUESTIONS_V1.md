# STORY_QUESTIONS_V1 — 9 "how it got here" yes/no rules (frozen before scoring)

Practice-only (HINT). Point-in-time: the answer for session D uses only the ticker's bars with date < D
(last bar t = the ticker's bar immediately before D; all rolls trailing, ending at t). Entry = open of D.
Bars: daily OHLCV from universe_2020_survivors.parquet, read with date <= 2024-12-31.
Green = close > open; red = close < open; body = |close - open|. BB20: SMA20(close) ± 2·std20(close, ddof=0).
NOT_READY if t has fewer than 60 prior bars of history (index < 60).

**Swing high** at bar i: high[i] > high of bars i-2, i-1, i+1, i+2 (2-bar fractal). Confirmed (usable) only at bar i+2, so as of t only swings with i <= t-2 count.
**Swing low** at bar i: low[i] < low of bars i-2, i-1, i+1, i+2, confirmed at i+2.

| # | id | YES when (as of bar t) |
|---|----|------------------------|
| 1 | sq1_lower_highs3 | the last 3 confirmed swing highs have strictly decreasing highs (oldest > middle > latest) |
| 2 | sq2_higher_lows3 | the last 3 confirmed swing lows have strictly increasing lows |
| 3 | sq3_shrinking_green3 | among bars t-9..t there are >=3 green candles and the bodies of the last 3 green candles strictly decrease (oldest > middle > latest); else NO |
| 4 | sq4_below_mid_5of10 | close < SMA20 on >= 5 of bars t-9..t |
| 5 | sq5_big_red_recent | the largest red body in bars t-19..t lies in bars t-4..t (ties -> most recent); NO if no red bar in window |
| 6 | sq6_dip_vol_lower | "dip" = confirmed swing low bar; volume on the latest dip bar < volume on the prior dip bar; NO if fewer than 2 dips |
| 7 | sq7_lowerbb_reclaim | some bar j in t-9..t has low <= lower BB20(j), and some bar k in j..min(j+3,t) has close > lower BB20(k) |
| 8 | sq8_above_last_red_high | close[t] > high of the most recent red candle at index < t (NO if none in prior 60 bars) |
| 9 | sq9_breakdown_vol | "breakdown" bar j = close[j] < min(low[j-20..j-1]); the most recent breakdown in t-9..t has volume[j] >= 1.5 × mean(volume[j-20..j-1]); NO if no breakdown in window |

Code: story_q.py (features in `story_feats`). Shas recorded in SHAS.txt / below before any scoring.

## Frozen shas (recorded before scoring, 2026-10-22 ~20:25 HKT)
- story_q.py: 3828cfb7cfb019c4da0195c3f66c70b766aab54eee63282e5b5d5cfaf0bfbca9
- this file (pre-sha-section body): 6d7f47984df709e80a425362996e21459a6f83b3afc0b9c250006a407a80523e
Horizons 5/10/21 trading days; exit open[D+h]; only signals whose exit date <= 2024-12-31.

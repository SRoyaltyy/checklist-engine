# 2020–24 OHLCV / price-volume YES/NO score (Taskforce). EXPLORATORY, survivors only, NO 2025–26 read
Scripts: `ohlcv/build.py`, `ohlcv/nb.py`, `ohlcv/score.py`. Price data filtered to before 2025-01-01 (asserted); NB chunks asserted to end before 2025.

**Method:** signal from bars through close D, then buy at the open of D+1 and sell at the open of D+1+h (h = 5/10/20). Fee 30bp/side (0.60% round trip). Dividends added back. Funds excluded.
Control = ready-NO stock-days in the same date × price quintile × ATR% quintile × prior-1-day-return decile cell. Residual = YES minus the cell's control mean. 95% CIs clustered by date.
Win = share of trades with net return > 0 after fees, in the direction of the edge (short side: −ret − fee > 0).
**Pass:** BH q=0.05 across all trials, CI clears 0, win > 50%, ≥4/5 years with the same sign, YES rate ≤ 50%.
**Robustness (every check must clear):** close ≥ $2 (CI clears 0 and win > 50%), ticker-equal mean, first event per ticker, drop the top-10 tickers by event count.

**Trials:** 222 (74 rows × 3 holds). BH survivors 155. Core pass 47. **Full pass 31.** No long-side (buy) row passed.

## Full passes (all are SHORT / avoid flags)
| row | hold | resid | 95% CI | win after fee | years | ≥$2 resid | ticker-eq | first-event | n events / tickers |
|---|---|---|---|---|---|---|---|---|---|
| OB-MFI>80 | 20d | -1.09% | -1.22% / -0.96% | 50.2% | ----- | -1.29% | -0.98% | -0.96% | 332,685 / 4,725 |
| OB-EXT20>+10% | 5d | -0.29% | -0.41% / -0.16% | 50.6% | ----+ | -0.38% | -0.86% | -1.80% | 462,225 / 4,714 |
| OB-EXT20>+10% | 10d | -0.42% | -0.58% / -0.25% | 51.5% | ----+ | -0.59% | -1.30% | -1.84% | 460,422 / 4,712 |
| OB-EXT20>+10% | 20d | -0.80% | -1.03% / -0.57% | 52.3% | ----+ | -1.05% | -2.10% | -1.34% | 454,734 / 4,694 |
| FADE-1d&up5>10% | 5d | -0.30% | -0.45% / -0.14% | 51.5% | ---+- | -0.36% | -0.53% | -1.29% | 51,743 / 4,571 |
| FADE-1d&up5>10% | 10d | -0.32% | -0.53% / -0.11% | 50.4% | ---+- | -0.43% | -0.69% | -0.95% | 51,623 / 4,568 |
| FADE-1d&up5>10% | 20d | -0.53% | -0.81% / -0.26% | 50.9% | ----- | -0.76% | -1.42% | -1.79% | 51,239 / 4,554 |
| OUT-r1>=+10% | 5d | -0.86% | -1.05% / -0.67% | 55.5% | ----- | -1.09% | -0.75% | -0.68% | 89,488 / 4,382 |
| OUT-r1>=+10% | 10d | -1.21% | -1.46% / -0.97% | 55.9% | ----- | -1.57% | -0.95% | -1.03% | 88,778 / 4,375 |
| OUT-r1>=+10% | 20d | -1.80% | -2.11% / -1.50% | 56.8% | ----- | -2.31% | -1.39% | -1.61% | 87,470 / 4,365 |
| OUT-RVOL>=5 | 5d | -1.15% | -1.33% / -0.97% | 50.6% | ----- | -1.44% | -0.55% | -0.97% | 69,143 / 4,508 |
| OUT-RVOL>=5 | 10d | -1.50% | -1.74% / -1.26% | 51.2% | ----- | -1.93% | -0.59% | -1.20% | 68,423 / 4,481 |
| OUT-RVOL>=5 | 20d | -2.02% | -2.33% / -1.71% | 52.2% | ----- | -2.53% | -0.55% | -1.36% | 67,473 / 4,465 |
| OUT-RVOL>=3&up | 5d | -0.80% | -0.97% / -0.64% | 51.0% | ----- | -0.99% | -0.61% | -0.85% | 90,662 / 4,709 |
| OUT-RVOL>=3&up | 10d | -1.01% | -1.24% / -0.79% | 51.5% | ----- | -1.31% | -0.74% | -1.08% | 89,428 / 4,686 |
| OUT-RVOL>=3&up | 20d | -1.35% | -1.64% / -1.07% | 52.0% | ----- | -1.70% | -0.85% | -1.20% | 88,250 / 4,679 |
| OUT-RV10/60>2 | 10d | -1.99% | -2.21% / -1.77% | 50.6% | ----- | -2.22% | -1.20% | -1.56% | 55,659 / 3,462 |
| OUT-RV10/60>2 | 20d | -2.75% | -3.03% / -2.48% | 51.9% | ----- | -3.08% | -1.58% | -2.30% | 54,810 / 3,440 |
| GAP-down<=-5% | 10d | -0.84% | -1.16% / -0.52% | 53.0% | ----- | -1.12% | -0.68% | -1.61% | 90,482 / 4,667 |
| GAP-down<=-5% | 20d | -1.14% | -1.54% / -0.74% | 52.7% | ----- | -1.52% | -0.47% | -0.74% | 89,513 / 4,656 |
| nb4-REL-NB-026-T1-THR | 5d | -1.02% | -1.23% / -0.81% | 54.6% | ----- | -1.23% | -1.19% | -1.28% | 81,794 / 4,145 |
| nb4-REL-NB-026-T1-THR | 10d | -1.36% | -1.62% / -1.10% | 55.4% | ----- | -1.70% | -1.52% | -2.15% | 81,166 / 4,140 |
| nb4-REL-NB-026-T1-THR | 20d | -1.87% | -2.20% / -1.53% | 56.5% | ----- | -2.35% | -2.13% | -2.59% | 79,825 / 4,129 |
| nb4-HIS-NB-029-P5-POSQ | 5d | -0.72% | -0.93% / -0.52% | 55.2% | .---- | -1.05% | -0.53% | -0.95% | 67,336 / 2,542 |
| nb4-HIS-NB-029-P5-POSQ | 10d | -1.40% | -1.66% / -1.14% | 57.5% | .---- | -1.87% | -0.79% | -1.57% | 66,626 / 2,535 |
| nb4-HIS-NB-029-P5-POSQ | 20d | -2.34% | -2.67% / -2.01% | 60.9% | .---- | -3.05% | -1.08% | -1.66% | 65,194 / 2,520 |
| nb4-HIS-NB-029-P5-POSD | 5d | -0.72% | -0.93% / -0.52% | 55.2% | .---- | -1.05% | -0.53% | -0.95% | 67,336 / 2,542 |
| nb4-HIS-NB-029-P5-POSD | 10d | -1.40% | -1.66% / -1.14% | 57.5% | .---- | -1.87% | -0.79% | -1.57% | 66,626 / 2,535 |
| nb4-HIS-NB-029-P5-POSD | 20d | -2.34% | -2.67% / -2.01% | 60.9% | .---- | -3.05% | -1.08% | -1.66% | 65,194 / 2,520 |
| nb4-PDS-NB-036-T20-RXS | 10d | -0.62% | -0.78% / -0.47% | 50.2% | ----- | -0.73% | -0.60% | -0.85% | 83,797 / 2,798 |
| nb4-PDS-NB-036-T20-RXS | 20d | -1.20% | -1.39% / -1.00% | 52.6% | ----- | -1.40% | -1.11% | -1.31% | 82,327 / 2,780 |

## Core pass but failed robustness
| row | hold | resid | failed on |
|---|---|---|---|
| OUT-r1<=-10% | 5d | -0.30% | ticker-eq, first-event |
| OUT-r1<=-10% | 10d | -0.54% | ticker-eq |
| GAP-up>=5% | 10d | -0.39% | ticker-eq, first-event |
| GAP-up>=5% | 20d | -0.35% | ticker-eq, first-event, drop-top10 |
| GAP-down<=-5% | 5d | -0.39% | first-event |
| VOL-upvolshare>0.7 | 20d | -0.98% | first-event |
| nb4-PDS-NB-015-T1-EXT | 10d | -0.36% | first-event |
| nb4-PDS-NB-015-T1-EXT | 20d | -0.67% | first-event |
| nb4-PDS-NB-015-T1-EXT-BUT | 10d | -0.19% | ticker-eq, first-event |
| nb4-PDS-NB-015-T1-EXT-BUT | 20d | -0.49% | ticker-eq, first-event |
| nb4-PDS-NB-015-T1-CHG | 20d | -0.32% | first-event |
| nb4-PDS-NB-015-T1-CHG-BUT | 20d | -0.30% | first-event |
| nb4-REL-NB-026-T1-RNK | 5d | -0.30% | first-event |
| nb4-REL-NB-026-T1-RNK | 10d | -0.38% | first-event |
| nb4-REL-NB-026-T1-RNK | 20d | -0.56% | first-event |
| nb4-PDS-NB-036-T20-RXS-BUT | 10d | -0.34% | ticker-eq, first-event |

## Cyrus's questions
- **Overbought/oversold:** RSI14/RSI2/Stoch/Williams/Bollinger/CCI/oversold extremes and the 52-week-high distance all fail. Only MFI>80 (20d) and price >10% above SMA20 pass, both as 'lags after'.
- **Momentum fading:** plain smaller green candle + lower volume (1/2/3-day) fails. It works only after a run-up (>10% in 5 days): −0.30% to −0.53%.
- **Outliers:** the strongest group. A +10% day, RVOL ≥5, an RVOL ≥3 up-day, a 5% gap-down (10d/20d) and a volatility jump (RV10/60 > 2) all lag their matches.

## Caveats
Survivors only, which biases toward long, so shorts are probably understated. Overlapping holds make CIs somewhat narrow. Short-side win rates are only 50–57%. Borrow costs are not included. Treat these as 'don't buy / trim' flags, not short trades. NB-029 POSQ and POSD are identical rows (counted once in practice).
# 2020–24 same-day BASKET vs one-at-a-time (Taskforce). EXPLORATORY, survivors only, NO 2025–26 read

Scripts: `baskets/score_baskets.py`. Price/feat asserted before 2025-01-01. F4TR/00051 chunks 2020–24 only. Sealed 2025–26 NB/F4TR not opened.

## What was tested
Cyrus asked: buy a **package** of stocks that lit individual signals the same day, mixing different signals, and compare that package to buying the same names one-at-a-time.

**Trade:** signal through close D → enter open D+1, exit open D+1+h (h=5 or 20). Fee 30bp/side (0.60% round trip). Dividends already in feat returns. Survivors, close D ≥ $2, funds excluded (same feat as OHLCV score).

**Matched control (stock level):** ready non-signal stock-days in the same date × price quintile × ATR% quintile × prior-1d-return decile. Residual = stock return − cell mean. Basket residual = equal-weight average of member residuals that day. 95% CI is across basket-dates (one obs per date). BH q=0.05 across 70 tested trials.

**Pass bar (basket):** BH, CI clears 0 in the trade direction, win after fee > 50%, raw mean after fee > 0, ≥4/5 years same sign.

## Signal families (can mix)
| family | what lights | trade direction |
|---|---|---|
| MIX_ANY | OHLCV6 warnings + oversold long-candidates + warnspike + 00051 YES | BUY (as asked) |
| LONG_ONLY | oversold candidates (EXT20&lt;−10%, RSI14&lt;30, MFI&lt;20, upvolshare&lt;0.3, ≤2 green of 10) + 00051 YES | BUY |
| SHORT_PKG | OHLCV6 (VOLJUMP, RVOL≥5, +10% day, NB-029 POSQ, gap-down≤−5%, MFI&gt;80) + warnspike | SHORT / avoid package |
| O51_ONLY | OWN-TR-00051-C = YES | BUY |
| OHLCV6_ONLY | the 6 OHLCV warnings | SHORT |
| WARN_ONLY | top-bull lean ≥ 0.6205 + stock-own QW jump z ≥ 1.5 | SHORT |

Variants per family × hold: all names that day; min-N ≥3 or ≥5; top-5 / top-10 by strength (signal-count then |r1|).

## Plain answer: does the package beat one-at-a-time after fees?

**Buying a mixed package: no.** Mixing every lit signal into a long basket loses after the 0.6% fee (win ~43% at 5d, ~45% at 20d). Equal-weighting hundreds of names does not create an edge the singles did not already have. Top-5 / top-10 (the wildest names) makes the buy basket worse.

**Buying only the long-leaning names: still no as a trade.** LONG_ONLY has a tiny matched residual (~+0.18% at 5d, all years +) but win after fee is only 44%. The fee eats the edge. The package’s date-level win is ~2pp higher than singles (44% vs 42%), and day-to-day volatility is ~⅓ of single-stock vol — so packaging smooths the ride, but you still lose money after fees.

**Short / avoid package: yes, the package helps on win rate.** When you treat the OHLCV warnings (+ warnspike) as a same-day short/avoid basket:
- Full universe package, 20d: basket win **55.2%** vs singles **50.9%** (+4.3pp). Resid ~−1.1% (lags matches). Vol of the package is ~32% of single-stock vol.
- Top-5 by strength, 20d: basket win **63.8%** vs singles **58.9%** (+4.9pp). Resid ~−4.1%.
- Same pattern on OHLCV6 alone and on warnspike top-5/10.

So: **packaging does not invent a buy edge, but it does make the existing short/avoid edge win more often day-by-day**, because a few losers inside the day get averaged out. Mean residual for top-N is the same as the singles of those same names (equal-weight math); the gain is in **date-level win rate and lower day-to-day noise**.

## Key numbers
### A. MIX_ANY buy (what Cyrus asked first)
| variant | hold | # baskets | mean names | basket resid | basket win | single win | beat win | vol ratio | years |
|---|---|---|---|---|---|---|---|---|---|
| all / min3 / min5 | 5d | 1,238 | 1,224 | −0.05% | 43.0% | 42.1% | +0.9pp | 0.31 | ++--- |
| top5 | 5d | 1,238 | 5 | −1.30% | 38.5% | 38.4% | +0.1pp | 0.48 | +++-- |
| all | 20d | 1,223 | 1,218 | −0.36% | 45.4% | 43.7% | +1.7pp | 0.36 | -+--- |
| top5 | 20d | 1,223 | 5 | −3.96% | 34.5% | 37.7% | −3.2pp | 0.53 | -+--- |

None pass. Buying the mix of bullish+bearish signals is like buying a bag of mixed fruit and spoiled fruit.

### B. LONG_ONLY buy
| variant | hold | basket resid | basket win | single win | beat win | years | pass |
|---|---|---|---|---|---|---|---|
| all | 5d | +0.18% | 44.3% | 42.2% | +2.2pp | +++++ | no (win&lt;50%, fee) |
| all | 20d | +0.20% | 46.4% | 44.0% | +2.4pp | +++-- | no |
| top5 | 5d | −0.34% | 40.4% | 39.2% | +1.1pp | +++-- | no |

### C. SHORT_PKG (OHLCV6 + warnspike) — where the package helps
| variant | hold | basket resid | basket win | single win | beat win | vol ratio | years | pass |
|---|---|---|---|---|---|---|---|---|
| all | 5d | −0.40% | 46.4% | 47.9% | −1.5pp | 0.25 | ----- | no |
| top5 | 5d | −1.58% | **58.0%** | 54.7% | **+3.3pp** | 0.49 | --+-- | YES |
| top10 | 5d | −1.61% | **57.7%** | 55.1% | **+2.5pp** | 0.39 | ----- | YES |
| all | 20d | −1.09% | **55.2%** | 50.9% | **+4.3pp** | 0.32 | ----- | YES |
| top5 | 20d | −4.09% | **63.8%** | 58.9% | **+4.9pp** | 0.53 | -+--- | YES |
| top10 | 20d | −3.56% | **63.9%** | 59.0% | **+4.9pp** | 0.44 | -+--- | YES |

### D. 00051 alone as a basket
Rarely a real basket (mean **1.4 names** per lit day; only 48 days with ≥3). Resid +0.9%/+1.9% at 5d/20d, win after fee 48–54%. Packaging changes almost nothing vs singles because most “baskets” are one stock.

## How to read “beat”
- **Mean residual:** for top-N with a fixed N, basket resid ≈ single resid of the same names (equal-weight average). Packaging does not change the average edge.
- **Win after fee:** date-level (did today’s package make money?) vs stock-level (did each name make money?). This is where the package wins — especially on the short/avoid side at 20d and on top-5/10.
- **Vol ratio:** std(basket raw) / std(single raw). Packages are 0.25–0.53× as noisy day-to-day.

## BH / pass count
70 tested trials. BH survivors 60. Full pass 24 — all of them short/avoid packages (SHORT_PKG, OHLCV6_ONLY, WARN_ONLY top-N or 20d-all). **Zero buy-side passes.**

## Caveats
Survivors-only (long bias). Overlapping 5d/20d holds. MIX_ANY deliberately mixes short-edge and long-edge names into one buy, which dilutes both. Oversold “long candidates” cleared BH+CI as singles but never cleared win&gt;50% after the 0.6% fee — packaging does not fix that. 00051 is sparse. Borrow cost not in the short package. 2025–26 sealed data not touched.

## Files
- `baskets/score_baskets.py`
- `baskets/2020_24_basket_score.csv`
- `baskets/2020_24_basket_dates_MIX_h5.csv`
- `baskets/signal_coverage.csv`

# Lens definitions V1

Authority: James/Cyrus01926ea (2026-10-30 01:24 HKT), superseding the seven-lens
working set. Apply **all applicable** lenses; publish an explicit reason for an
inapplicable lens and flag each question type with fewer than six distinct
implemented readings. A missing implementation/data source is pending work,
not a semantic inapplicability reason.

In the concrete definitions below, t is the last completed native candle
available before setup-date open; every required historical value must be known.
Offsets are native slots on the shared calendar, not a compressed list of
available stock bars. Missing required slots/values yield NOT_EVALUABLE. An
actual generated row must expand X, units, settings, counterpart, dates and every
numeric parameter; examples are not replacements for registered source grids.
The examples use daily values unless a resolution is explicitly shown.

| Lens | Strict definition, with a concrete numeric instance |
|---|---|
| absolute | Compare a measured scalar in its declared units to a literal level: RSI14(t)>70. Raw dollar levels require nominal PIT prices. |
| relative | Compare the same quantity, units and intervals to an explicitly identified PIT reference: (C(t)/C(t−20)−1)−(SPY(t)/SPY(t−20)−1)>0.05, with both21-close windows aligned. |
| position | Compare location relative to a stated earlier range: (X(t)−min(X(t−20..t−1)))/(max(X(t−20..t−1))−min(X(t−20..t−1)))>0.8; current value is excluded from that range. |
| threshold | Compare the scalar to one rung of an explicit fixed ladder, e.g. RSI14(t)>70; this is identical to the absolute example and receives one semantic predicate ID, not two. |
| divergence | Select the two latest p in t−17..t−2 satisfying C(p)=min(C(p−2..p+2)); require newer C<older C AND newer RSI14−older RSI14>=5 points; these are inclusive five-candle lows confirmed at p+2, and no qualifying pair means NO once required inputs are known. |
| outlier | Compare standardized surprise to a literal cutoff: abs((X(t)−mean(X(t−60..t−1)))/sample_std_ddof1(X(t−60..t−1)))>=2. |
| path | Compare aggregates from specified parts of the route: mean(X(t−5..t))−mean(X(t−19..t−14))>0; only the first6 and last6 observations of the20-slot window contribute. |
| streak | Require an uninterrupted condition for a stated length: all(RSI14(s)>70 for s=t−4..t), equivalent to a true streak of at least5; equality breaks the streak. |
| cross | Require a strict side change: RSI14(t−1)<70 AND RSI14(t)>70; equality on either side is not a crossing, following core C16. |
| change since last | Compare two explicit offsets: RSI14(t)−RSI14(t−5)>0; this uses the endpoint difference, not a mean of the intervening values. |
| rank (vs market/sector) | Rank among the full named PIT peer set, excluding self: 100*count(peer X(t)<stock X(t))/peer_count>=90; ties do not count below, an empty/unknown peer set is NOT_EVALUABLE. |
| percentile | Rank against own earlier observations: 100*count(X(s)<X(t), s=t−250..t−1)/250>=80; ties do not count below, and all250 preceding values are required(core C25). |
| extreme vs own history | Test a strict record: X(t)>max(X(s),s=t−20..t−1) on daily values; also instantiate the60/252-session and10-calendar-year baselines, labeling any separately registered native-candle baseline distinctly and preserving its endpoints. |
| timeframe | Compare independently computed native resolutions at the same setup cutoff: RSI14(latest completed1d)−RSI14(latest completed5d)>0; show both actual candle-end dates and never resample daily RSI as five-day RSI. |

No raw value or threshold is epsilon-shifted or clipped. For the explicitly
written ratios above, nonzero/zero keeps its signed infinity;0/0 is unavailable.
This does not silently change an existing recipe's separately specified edge
rule. A ten-year baseline means calendar years, excluding the current point,
with a February29 lower endpoint clamped to February28 when needed; it is not
automatically2520 native observations. A source row that defines another
boundary(e.g. a touch-counting high including current,250 vs252 values, or a
first-match bucket priority) retains that rule and a distinct semantic identity.

## Semantic aliases and applicability

Absolute and fixed-threshold readings are aliases **only** when their expanded
feature, units, timeframe, lookback, comparator and cutoff are equal. Keep both
requested labels in coverage metadata but count the predicate once. Relative,
cross-sectional rank and own-history percentile remain separate: their reference
populations differ. Streak, cross, path and endpoint change remain separate:
their observations and logical conditions differ. No other lens is merged by
name or by a high observed correlation.

For categorical source states, use a fixed named indicator or a declared
count/proportion, never a mean/rank of arbitrary category codes. A market-global
series compared with itself across stocks has no meaningful cross-stock rank;
record that exact inapplicability instead of generating a constant. Raw ontology
controls and unavailable schemas need their own applicability review. A missing
renderer, PIT peer set, source component or parameter binding must be named as
missing; it does not certify a lens.

These definitions do not claim that the full master or lens implementations are
complete. The canonical plan currently implements the threshold predicates for
two price families and flags all remaining lens work. Per-item DEFINE→CHART→
DERIVE YES/NO→MINE and Step6b full leak/PIT eligibility gates still apply.

<!-- INVENTORY_COVERAGE:BEGIN -->
## Inventory coverage — 258 items (generated by ci/lenses_coverage.py)

Kimi, 2026-10-30 (22:45 assignment item 3). One row per inventory item from
`dictionary/DATA_SOURCES.csv`. Applicability follows the measurement-class
rule table below. This is **CLASS_APPLICABILITY_ONLY**, not measured
implemented coverage. Missing named references/pairings are CONDITIONAL,
not semantic inapplicability. Every exclusion still names its reason.
`potential_lens_count` counts planning labels after the declared candidate
`absolute`/`threshold` alias; actual expanded-predicate equality is unmeasured.
For every measurable item, implemented count is unknown, implementation is
**UNMEASURED**, and the minimum-six gate is **NOT_PROVEN**. Ontology/dropped
items are NOT_APPLICABLE. No YES/NO rows or completed lens readings are
certified here. Full table: `docs/LENSES_COVERAGE_V1.csv`.

### Measurement-class rule table

| Class | Items | Eligible labels | Conditional (prerequisite) | Inapplicable (reason) |
|---|---:|---|---|---|
| STOCK_SCALAR | 167 | 14 of 14 | — | — |
| EVENT_COUNT | 64 | 14 of 14 | — | — |
| SPARSE_NUMERIC | 7 | 14 of 14 | — | — |
| MARKET_GLOBAL | 5 | 13 of 14 | — | rank (market-global series: identical across stocks, no cross-stock rank) |
| EVENT_FACT | 4 | 12 of 14 | divergence (needs a declared numeric pairing (e.g. vs price) before it certifies), relative (needs a named PIT benchmark/peer set before it certifies) | — |
| CATEGORICAL_STATE | 4 | 10 of 14 | divergence (needs a declared numeric pairing (e.g. vs price) before it certifies), relative (needs a named PIT benchmark/peer set before it certifies) | absolute (raw state code has no units), position (categorical/boolean has no ordered magnitude) |
| BOOLEAN_STATE | 2 | 11 of 14 | divergence (needs a declared numeric pairing (e.g. vs price) before it certifies), relative (needs a named PIT benchmark/peer set before it certifies) | position (categorical/boolean has no ordered magnitude) |
| MIXED_SNAPSHOT | 2 | 14 of 14 | — | — |
| NO_QUESTIONS | 2 | 0 of 14 | — | all 14 (ONTOLOGY: rule control, not a measurement) |
| NO_QUESTIONS_DROPPED | 1 | 0 of 14 | — | all 14 (DROPPED: GDELT news stays dropped, 2026-10-28) |

Reason codes: RANK_GLOBAL: market-global series: identical across stocks, no cross-stock rank; POS_CAT: categorical/boolean has no ordered magnitude; use the declared share reading; ABS_CAT: raw state code has no units; use a named-state indicator or declared share; REL_NAMED: needs a named PIT benchmark/peer set before it certifies; DIV_PAIR: needs a declared numeric pairing (e.g. vs price) before it certifies; ONTOLOGY: ontology/rule control, not a measurement: no lens readings; DROPPED: item dropped (GDELT news stays dropped, 2026-10-28): no lens readings

### Per-item coverage (258 rows)

| id | item | class | potential lenses | implementation | minimum 6 | conditional | inapplicable | flags |
|---|---|---|---:|---|---|---|---|---|
| C01 | Bar | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C02 | Window W(x,N) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C03 | High (window high) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C04 | High (fixed-block high) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C05 | Low (window low) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C06 | Low (fixed-block low) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C07 | Close-based high/low | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C08 | Swing high/low: strict fractal pivot | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C09 | Swing high/low: inclusive pivot | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C10 | Swing (zigzag): ATR-reversal pivot | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C11 | Last K swing highs / lows | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C12 | Average swing line (support/resistance level) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C13 | Trend line through last K swings | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C14 | Divergence (price vs indicator), pivot-based | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C15 | Divergence (price vs indicator), half-window | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C16 | Crosses vs is above | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| C17 | Breakout (channel) | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| C18 | Gap | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| C19 | Leg | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| C20 | Range / base | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| C21 | New 52-week high / low | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| C22 | Volume spike | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| C23 | ATR-normalised distance | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C24 | Trend test (t-stat slope) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C25 | Own-history percentile | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| C26 | Sector membership as of D-1 | CATEGORICAL_STATE | 12 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | absolute=raw state code has no units; use a named-state indicator or declared share; position=categorical/boolean has no ordered magnitude; use the declared share reading | readings use named-state indicators or declared shares, never mean/rank of codes; divergence: CONDITIONAL - native declared pairings only (e.g. stage vs price); rank: CONDITIONAL - cross-stock on the declared share |
| C27 | Tradeable filter | BOOLEAN_STATE | 12 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | position=categorical/boolean has no ordered magnitude; use the declared share reading | readings use the declared share/count of TRUE, never the raw code; rank: CONDITIONAL - cross-stock on the declared share |
| C28 | Bucket/threshold boundary rule | NO_QUESTIONS | 0 | NOT_APPLICABLE | NOT_APPLICABLE | — | ontology/rule control, not a measurement: no lens readings | — |
| C29 | Leak / point-in-time rule | NO_QUESTIONS | 0 | NOT_APPLICABLE | NOT_APPLICABLE | — | ontology/rule control, not a measurement: no lens readings | — |
| C30 | Finviz snapshot fields | MIXED_SNAPSHOT | 13 | UNMEASURED | NOT_PROVEN | — | — | per-field split: numeric fields -> STOCK_SCALAR set, categorical -> CATEGORICAL_STATE set; PIT_MISSING: snapshot publication-time proof required before any reading certifies; PIT_MISSING: Finviz snapshot publication-time proof required |
| I001 | SMA5 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I002 | SMA10 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I003 | SMA20 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I004 | SMA30 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I005 | SMA50 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I006 | SMA100 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I007 | SMA200 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I008 | EMA21 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I009 | EMA20 (Keltner mid) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I010 | WMA(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I011 | SMMA/RMA(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I012 | DEMA(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I013 | TEMA(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I014 | HMA(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I015 | ALMA(n,offset=0.85,sigma=6) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I016 | KAMA(n,2,30) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I017 | LSMA(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I018 | VWMA(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I019 | McGinley(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I020 | Median(n) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I021 | MA_group stack | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I022 | Weekly MA proxy | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I023 | MA Ribbon / MA Cross / 2-line cross | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I024 | RSI(6) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I025 | RSI(12) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I026 | RSI(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I027 | RSI(24) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I028 | Stochastic(14,3,3) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I029 | Williams %R(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I030 | MACD(12,26,9) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I031 | ROC(5) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I032 | ROC(20) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I033 | ROC(60) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I034 | ADX(14) / +DI / -DI | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I035 | Ichimoku(9,26,52) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I036 | CCI(20) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I037 | CMO(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I038 | Awesome Osc(5,34) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I039 | BOP | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I040 | Bull Bear Power(13) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I041 | Aroon(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I042 | DPO(21) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I043 | Fisher(9) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I044 | KST | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I045 | Coppock(10,14,11) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I046 | PPO(12,26,9) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I047 | Momentum(10) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I048 | RVI(10) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I049 | Relative Volatility Index(10,14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I050 | SMI Ergodic(5,20,5) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I051 | SMI(10,3,3) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I052 | StochRSI(14,14,3,3) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I053 | TRIX(18) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I054 | TSI(25,13) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I055 | Ultimate Osc(7,14,28) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I056 | Connors RSI(3,2,100) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I057 | Chande Kroll Stop(10,1,9) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I058 | Choppiness(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I059 | Mass Index(9,25) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I060 | Vortex(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I061 | Parabolic SAR(0.02,0.2) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I062 | Supertrend(10,3) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I063 | Chandelier Exit(22,3) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I064 | Volatility Stop(20,2) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I065 | Williams Alligator(13,8,5) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I066 | Williams Fractal(2) | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I067 | Zigzag(5%) | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I068 | Linear Regression(100) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I069 | Correlation(20) vs SPY | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I070 | Historical Volatility(20) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I071 | Ulcer Index(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I072 | ADR(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I073 | Performance (1W..1Y) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I074 | Pivot Points Standard | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I075 | Pivot Points High Low(10,10) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I076 | Auto Fib Retracement | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I077 | Auto key levels | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I078 | Fibonacci_swing | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I079 | Volume | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I080 | RVOL20 | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I081 | Dollar volume | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I082 | OBV | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I083 | A/D line | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I084 | MFI(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I085 | Up/Down volume | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I086 | Anchored VWAP (window start) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I087 | Volume profile (POC/VA) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I088 | CMF(20) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I089 | Chaikin Osc(3,10) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I090 | EOM(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I091 | EFI(13) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I092 | Klinger(34,55,13) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I093 | NVI/PVI | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I094 | Net Volume | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I095 | PVO(12,26,9) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I096 | PVT | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I097 | ATR(14) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I098 | Bollinger(20,2) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I099 | Keltner(20,1.5) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I100 | Squeeze (BB inside KC) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I101 | Donchian(20) | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I102 | HiLo window | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I103 | 52w range | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I104 | Drawdown | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I105 | BBW / %b standalone | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I106 | Candles OHLC facets | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I107 | Inside/outside bar | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I108 | Candle patterns (61 TA-Lib CDL*) | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I109 | Tweezer top/bottom | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I110 | Rising/Falling window | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I111 | Chart patterns (flag, wedge, triangle, double top/bottom, H&S, rectangle) | CATEGORICAL_STATE | 12 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | absolute=raw state code has no units; use a named-state indicator or declared share; position=categorical/boolean has no ordered magnitude; use the declared share reading | readings use named-state indicators or declared shares, never mean/rank of codes; divergence: CONDITIONAL - native declared pairings only (e.g. stage vs price); rank: CONDITIONAL - cross-stock on the declared share |
| I112 | 3ATR legs / phases | CATEGORICAL_STATE | 12 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | absolute=raw state code has no units; use a named-state indicator or declared share; position=categorical/boolean has no ordered magnitude; use the declared share reading | readings use named-state indicators or declared shares, never mean/rank of codes; divergence: CONDITIONAL - native declared pairings only (e.g. stage vs price); rank: CONDITIONAL - cross-stock on the declared share |
| I113 | Prior pivots levels | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I114 | Unfilled gaps (multi) | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I115 | Old ranges / breakdowns | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I116 | Round numbers | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I117 | Heikin Ashi / Renko / Kagi / P&F / Line break / Range bars | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe); timeframe lens = comparison across registered native bar definitions (HA/Renko/Kagi/P&F/...), never daily-relabel |
| I118 | Abandoned Baby - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I119 | Abandoned Baby - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I120 | Dark Cloud Cover - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I121 | Doji | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I122 | Doji Star - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I123 | Doji Star - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I124 | Downside Tasuki Gap - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I125 | Dragonfly Doji - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I126 | Engulfing - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I127 | Engulfing - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I128 | Evening Doji Star - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I129 | Evening Star - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I130 | Falling Three Methods - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I131 | Falling Window - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I132 | Gravestone Doji - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I133 | Hammer - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I134 | Hanging Man - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I135 | Harami - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I136 | Harami - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I137 | Harami Cross - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I138 | Harami Cross - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I139 | Inverted Hammer - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I140 | Kicking - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I141 | Kicking - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I142 | Long Lower Shadow - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I143 | Long Upper Shadow - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I144 | Marubozu Black - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I145 | Marubozu White - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I146 | Morning Doji Star - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I147 | Morning Star - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I148 | On Neck - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I149 | Piercing - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I150 | Rising Three Methods - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I151 | Rising Window - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I152 | Shooting Star - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I153 | Spinning Top Black | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I154 | Spinning Top White | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I155 | Three Black Crows - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I156 | Three White Soldiers - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I157 | Tri Star - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I158 | Tri Star - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I159 | Tweezer Bottom - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I160 | Tweezer Top - Bearish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I161 | Upside Tasuki Gap - Bullish | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I162 | RS vs SPY | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I163 | RS vs QQQ | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I164 | RS vs IWM | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I165 | RS vs XLK | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I166 | RS vs XLF | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I167 | RS vs XLV | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I168 | RS vs XLY | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I169 | RS vs XLP | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I170 | RS vs XLE | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I171 | RS vs XLI | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I172 | RS vs XLB | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I173 | RS vs XLU | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I174 | RS vs XLRE | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I175 | RS vs XLC | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I176 | RS vs theme peers | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe); PIT_MISSING: theme membership history (dated theme map) required for peer sets |
| I177 | RS vs sector peers | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe); PIT_MISSING: PIT sector peer set required (SEC SIC as filed + dated ETF map) |
| I178 | VIX level | MARKET_GLOBAL | 12 | UNMEASURED | NOT_PROVEN | — | rank=market-global series: identical across stocks, no cross-stock rank | own-history readings use vintage-corrected history (ALFRED for FRED) |
| I179 | Market breadth %>SMA50 | MARKET_GLOBAL | 12 | UNMEASURED | NOT_PROVEN | — | rank=market-global series: identical across stocks, no cross-stock rank | own-history readings use vintage-corrected history (ALFRED for FRED) |
| I180 | A/D line, A/D ratio, new highs-lows (market) | MARKET_GLOBAL | 12 | UNMEASURED | NOT_PROVEN | — | rank=market-global series: identical across stocks, no cross-stock rank | own-history readings use vintage-corrected history (ALFRED for FRED) |
| I181 | SPY trend | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I182 | Beta | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I183 | Calendar context | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I184 | Earnings: date & timing | EVENT_FACT | 13 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | — | CONCRETE fields per 0b 00:40: event_date + days_since + direction + change |
| I185 | Earnings: surprise | SPARSE_NUMERIC | 13 | UNMEASURED | NOT_PROVEN | — | — | timeframe: registered native resolutions only (q vs y), never daily-relabel; streak/cross: consecutive native observations (quarterly), not sessions |
| I186 | Earnings: gap reaction / drift | SPARSE_NUMERIC | 13 | UNMEASURED | NOT_PROVEN | — | — | timeframe: registered native resolutions only (q vs y), never daily-relabel; streak/cross: consecutive native observations (quarterly), not sessions |
| I187 | Form 4 insider trades | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I188 | FINRA short interest | SPARSE_NUMERIC | 13 | UNMEASURED | NOT_PROVEN | — | — | timeframe: registered native resolutions only (q vs y), never daily-relabel; streak/cross: consecutive native observations (quarterly), not sessions |
| I189 | FINRA daily short volume | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I190 | Reg SHO threshold list | BOOLEAN_STATE | 12 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | position=categorical/boolean has no ordered magnitude; use the declared share reading | readings use the declared share/count of TRUE, never the raw code; rank: CONDITIONAL - cross-stock on the declared share |
| I191 | Trading halts | EVENT_FACT | 13 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | — | CONCRETE fields per 0b 00:40: event_date + days_since + direction + change |
| I192 | SEC XBRL fundamentals | SPARSE_NUMERIC | 13 | UNMEASURED | NOT_PROVEN | — | — | timeframe: registered native resolutions only (q vs y), never daily-relabel; streak/cross: consecutive native observations (quarterly), not sessions |
| I193 | Shares outstanding / float | SPARSE_NUMERIC | 13 | UNMEASURED | NOT_PROVEN | — | — | timeframe: registered native resolutions only (q vs y), never daily-relabel; streak/cross: consecutive native observations (quarterly), not sessions |
| I194 | Altman Z / Piotroski F / Beneish M | SPARSE_NUMERIC | 13 | UNMEASURED | NOT_PROVEN | — | — | timeframe: registered native resolutions only (q vs y), never daily-relabel; streak/cross: consecutive native observations (quarterly), not sessions |
| I195 | FRED macro | MARKET_GLOBAL | 12 | UNMEASURED | NOT_PROVEN | — | rank=market-global series: identical across stocks, no cross-stock rank | own-history readings use vintage-corrected history (ALFRED for FRED) |
| I196 | Dividends / splits | EVENT_FACT | 13 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | — | CONCRETE fields per 0b 00:40: event_date + days_since + direction + change |
| I197 | Analyst actions | EVENT_FACT | 13 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | — | CONCRETE fields per 0b 00:40: event_date + days_since + direction + change |
| I198 | Finviz snapshot fields (all) | MIXED_SNAPSHOT | 13 | UNMEASURED | NOT_PROVEN | — | — | per-field split: numeric fields -> STOCK_SCALAR set, categorical -> CATEGORICAL_STATE set; PIT_MISSING: snapshot publication-time proof required before any reading certifies; PIT_MISSING: Finviz snapshot publication-time proof required |
| I199 | 13F holdings | SPARSE_NUMERIC | 13 | UNMEASURED | NOT_PROVEN | — | — | timeframe: registered native resolutions only (q vs y), never daily-relabel; streak/cross: consecutive native observations (quarterly), not sessions |
| I200 | GDELT news | NO_QUESTIONS_DROPPED | 0 | NOT_APPLICABLE | NOT_APPLICABLE | — | item dropped (GDELT news stays dropped, 2026-10-28): no lens readings | — |
| I201 | CBOE market-wide options | MARKET_GLOBAL | 12 | UNMEASURED | NOT_PROVEN | — | rank=market-global series: identical across stocks, no cross-stock rank | own-history readings use vintage-corrected history (ALFRED for FRED) |
| I202 | Single-stock options | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe); SOURCE_MISSING: no free full-universe single-stock options source confirmed (hunt V1: DoltHub IV/chain partial, no OI) |
| I203 | Checklist score path | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I204 | Universe relative-strength percentile | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I205 | Mansfield relative strength | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I206 | Normalized ATR | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I207 | Price z-score | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I208 | Up and down streaks | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I209 | Historical volatility expanded | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I210 | Short over long volatility ratio | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I211 | Gap size in ATR | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I212 | Gap-fill rate | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I213 | Rolling return skewness | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I214 | Rolling excess kurtosis | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I215 | Rolling lag-one autocorrelation | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I216 | Rolling rescaled-range Hurst estimate | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I217 | Linear-regression R-squared | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I218 | Correlation to SPY and sector | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I219 | Beta to SPY and sector | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I220 | Chaikin Volatility | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I221 | Elder Impulse | CATEGORICAL_STATE | 12 | UNMEASURED | NOT_PROVEN | divergence=needs a declared numeric pairing (e.g. vs price) before it certifies; relative=needs a named PIT benchmark/peer set before it certifies | absolute=raw state code has no units; use a named-state indicator or declared share; position=categorical/boolean has no ordered magnitude; use the declared share reading | readings use named-state indicators or declared shares, never mean/rank of codes; divergence: CONDITIONAL - native declared pairings only (e.g. stage vs price); rank: CONDITIONAL - cross-stock on the declared share |
| I222 | Twiggs Money Flow | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I223 | STARC bands | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I224 | Linear-regression slope intercept and errors | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I225 | Stock-versus-stock peer correlation | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe); PIT_MISSING: named peer set required |
| I226 | Schaff Trend Cycle | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe) |
| I227 | Historical close-shape matches and known K-session outcomes | EVENT_COUNT | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required |
| I228 | Identical-window normalized close comparison to literal benchmark or PIT peer | STOCK_SCALAR | 13 | UNMEASURED | NOT_PROVEN | — | — | rank: named PIT peer set required (default = filtered universe); REL_NAMED: literal benchmark or PIT peer must be named per reading |
<!-- INVENTORY_COVERAGE:END -->

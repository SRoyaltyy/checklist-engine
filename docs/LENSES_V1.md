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

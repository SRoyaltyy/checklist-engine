# Registered Stochastic K in master predicates

The handwritten Stoch14_3 smoother can miss a strict downward midline cross.
With 100 closes at 100, then a close at 99, and constant highs/lows 110/90,
the preceding handwritten K is 49.99999999999999. The registered native K is
exactly 50. The final native K is 48.333333333333336, so the registered
`B|overbought_oversold|Stoch14_3|cross_event|1x10` answer is DOWN=YES.
The previous adapter reports NONE=YES. No epsilon can substitute for using
the registered field.

The adapter now calls TA-Lib STOCH with fast-K 14, slow-K 3/SMA and slow-D
3/SMA, exactly as frozen `world_timeframes.parameter_variants` produces
`STOCH14_3_3_k` and `world_indicator_settings` produces `I028_default_k`.
The facet still compares K with its declared constant (50 or 20/80), not D.
It retains the native K warmup, including the initial slow-D lookback.
Full supplied completed-candle history initializes native running arithmetic;
the facet then reads exactly its last N values, plus a cross anchor if needed.

The explicit undefined-range rule is preserved independently of native
numbers: a zero high-low range makes raw K unknown, and each of the
three slow-K values that consumes that raw K is unknown. Native values are
never rewritten; TA-Lib's known numeric zero is not used as a missing-value
test. Unknown bars invalidate only evidence that uses them. A later fully
defined window can recover after a flat prefix. This is the same per-bar
knowability contract introduced for native RSI/MACD in PR #189.

Tests authenticate and execute frozen native source at
`7dcaa48680daeac9a6025c09f9e4d138f5fcbda5`, SHA-256
`a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95`.
They compare exact K bits at every candle size 1–21 and earlier cuts with
future input supplied, reproduce the missed strict cross, check native warmup,
and test zero-range masks and unavailable history.

No question identity, cutoff, frozen producer or registered numeric value
changes. The 61,941-row canonical CSV keeps SHA-256
`d0376513b367c6e989f62d5ac101a6f3a5b644124ec96b564919b1789eaeda77`.
Only its implementation fingerprint changes. These bounded reference tests
do not establish real DERIVE coverage, global PIT proof, chart acceptance or
scoring approval. Other indicator parity and deferred semantic rulings retain
their separate review requirements.

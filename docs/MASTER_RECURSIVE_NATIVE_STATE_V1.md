# Native RSI and MACD initialization

The scalar master adapter reseeded RSI and MACD from a bounded facet window.
That lost the registered field's earlier state. Its handwritten arithmetic
also differed from the native TA-Lib operation order and MACD initialization.

Two bounded synthetic cases reproduce answer errors on the prior integrated
head `0fc86ed9ac066486409fd990f9e177d42ae62219`:

- RSI14 `time_in_zone`, 1x10: 70 closes at 1000, 25 at 100, then
  101/102/103. The old window seed is flat and returns NOT_EVALUABLE for
  every outcome. The registered last ten RSI values are defined, below 30,
  and the `mostly_low` answer is YES. A defined all-loss RSI of zero is known.
- MACD12_26_9 `cross_event`, 1x10: 160 supplied closes
  `100 + 10*sin(i/7) + 0.02*i`, queried at slot 45. The old adapter says
  `none=YES`; registered native MACD says `up=YES`. The supplied suffix
  after slot 45 must have no effect on that answer.

The adapter now computes native RSI/MACD from the complete supplied prefix
of completed native candles before selecting the facet window. RSI uses
`talib.RSI`; MACD uses the registered `talib.MACD` call and signal series.
This applies to RSI/MACD oscillator facets, RSI floor/ceiling, and the
RSI6/12/24 check at a higher-low-base breakout. Pattern rules and its existing
30-prior-candle requirement remain unchanged. Only cross facets include the
prior anchor in their evidence; floor/ceiling, zone, swing and extreme-position
facets use exactly their last N values.

Native values remain unchanged. A separate per-bar mask tracks native warmup
and RSI's exact undefined zero-gain/zero-loss state. No epsilon is added.
An initially flat seed can become defined after movement; unknown bars before
the required evidence window do not invalidate later defined observations.
An unknown bar inside the evidence window or cross anchor is NOT_EVALUABLE.
The RSI mask tracks Wilder gain/loss state only to identify exact 0/0; it
does not supply replacement numeric RSI values.

The shared native-history helper is renamed to cover MA and recursive
oscillators. Its fixed shared-calendar grouping, IPO/halt partial-group
omission, raw-bar validation, availability checks and cutoff behavior are
unchanged. Callers must supply the complete source prefix. This scalar
reference adapter is not a production performance claim.

Tests authenticate frozen registered source `7dcaa48680daeac9a6025c09f9e4d138f5fcbda5`
by SHA-256 and execute its RSI and configured MACD paths. Exact float64 bits
are compared for RSI6/12/14/24 and MACD line/signal at every candle size
1–21, including earlier cuts with supplied future data. Other regressions
cover the two answer errors, native warmup, defined zero, flat-state masks,
very small nonzero state, N-only extrema and unavailable history.

No question identities, definitions, cutoffs, frozen price producer or
registered numeric values change. The canonical batch14 CSV remains
61,941 rows with SHA-256
`d0376513b367c6e989f62d5ac101a6f3a5b644124ec96b564919b1789eaeda77`.
Only its implementation fingerprint changes. This does not establish broader
Stochastic/ROC parity, real answer-layer coverage, global PIT proof, chart
approval or permission to score; their existing gates remain in place.

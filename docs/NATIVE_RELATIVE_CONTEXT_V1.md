# Native literal ETF comparisons

`world_relative_context.native_comparisons` computes one stock, one literal
registered ETF and one native timeframe on demand. It keeps the complete
calendar grid, including unavailable intervals, before evaluating lookbacks.
Every source OHLCV session must exist and be finite. Missing intervals are
never compressed, forward-filled, cast to true, or replaced with false.

All 1d–21d sizes and monthly use complete candles. Monthly availability is
the actual following exchange session. Day-D OHLCV is excluded before any
calculation. The global timeframe implementation and protected world recipe
are unchanged. A self-comparison has explicit missing outcomes.

The existing Cursor59 formulas at `7f94f13` are adopted with their original
daily defaults. The native API also exposes the registered ten-bar return
and correlation settings; windows count native candles. Registered
Mansfield, relative-change, correlation and beta statistics retain float64
in this API; existing callers keep their original float32 default. Ratio
`_inf` and `_blank` variants preserve their distinct zero rules.

This API compares literal ETFs. It does not pick a stock's historical sector
or industry. That requires independently dated membership. The older bulk
comparison writer is not adopted: casting missing boolean outcomes to bool
would turn unknown observations into true answers.

The single-runner proof uses the same MAN/MNTS/EYE and SPY raw files as the
accepted exact-recomputation sample, authenticated by its public proof and
individual SHA256s. Each of the 66 native frames is stored, reopened and
independently regenerated bit for bit. Two actual source cutoffs check every
column on all grids (132 comparisons). The resulting public report binds
code, inputs, runtime, values and date hashes. Native matrices are temporary
references; raw inputs and code are the recomputation dependencies.

The 39 API/statistics/reader/controller tests pass locally and on actual Linux
PR run40790401871 (8.79 seconds). After integrating verified breadth main2921fa6,
all78 combined native-comparison/breadth/statistics/reader/storage/readback tests
pass locally (41.64 seconds). Producer code remains unchanged from119c08e.
Actual sample run40790389592/job123173883370 also passed39 Linux tests and
completed the real-input proof. All66 native frames (34228 rows per stock
across22 TF,4107360 numeric cells including explicit unknowns) reopen and
regenerate exactly; all132 cutoff checks pass. The temporary persisted
references total15974053 bytes, versus457284 original stock-source bytes
and264535 shared SPY bytes. MAN/MNTS/EYE full proof times are25.89/20.14/20.22s.

The public report at `relative-native-sample-v1-40790389592-1` was independently
downloaded and authenticated:458736 bytes, SHA256
`fa224c6e68b6a0c531460e5c6d3472987dc0c31c71ecfacca224ff163089a3aa`.
Every66-frame/132-cutoff receipt and all12 code hashes were inspected against
the exact119c08e Git blobs; the request matches the committed raw-input pins.
See `RELATIVE_NATIVE_MEASURED_V1.json` and
`RELATIVE_NATIVE_PUBLIC_READBACK_V1.json` for the actual evidence.
This is a three-stock component sample; it establishes no full-universe
coverage, historical eligibility, complete question state or 100GB world
budget. No checklist box or full-world/scoring gate is closed here.

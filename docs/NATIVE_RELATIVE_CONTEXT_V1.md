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

The proof is pending until an actual Actions run and public readback succeed.
This is a three-stock component sample; it establishes no full-universe
coverage, historical eligibility, complete question state or 100GB world
budget. No checklist box or full-world/scoring gate is closed here.

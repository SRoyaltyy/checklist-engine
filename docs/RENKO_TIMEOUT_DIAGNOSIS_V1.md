# Non-terminating Renko float step

The isolated EQLT recovery job123182745752 completed with an explicit
`STOCK_TIMEOUT` after1800 seconds. It recovered no answers. The public final
ledger SHA256 is `ce3ab760a20a402031602e5575ee53e163b92813151f167917df760ea0b581a6`
in `compact-world-build-v1-40792865480-1-000`; its checkpoints remain unchanged.
Periodic traces repeatedly identify `facets_world.compute_tv_extra` lines340–344
in the frozen7dcaa486 recipe, inside the M217 Renko loops.

Fresh readback verified the original archive SHA and EQLT bar member
`dbd611516c31830e5104975d2369fa90e4d42a3c8f632eb9cecbb3f713c295ad`
(74948 bytes,3186 rows). A bounded exact probe reaches2021-01-04 after616
brick steps, then observes close=last_brick=37.0 and ATR14
3.3759803938514623e-15. The float spacing at37 is7.105427357601002e-15.
Adding that positive brick rounds back to37.0. The condition
`close >= last_brick + box` remains true, and the body never advances its
price state. Increasing the timeout cannot make this loop terminate.

The probe stops at the first nonadvancing addition and produces no replacement
indicator or answer. Actual metadata and ledger are retained in
`RENKO_EQLT_INPUT_DIAGNOSIS_V1.json` and `EQLT_RENKO_TIMEOUT_LEDGER_V1.json`.
`python -m ci.renko_diagnostic --bars <authenticated-bars.parquet> --output <report.json>`
reproduces the bounded diagnosis. Three local tests cover decaying-positive ATR,
exact-zero ATR and an explicit advancing-loop probe limit.

A correction needs a new immutable recipe and exact validation against the
terminating legacy domain. A finite zero-distance step can make no new brick;
other nonadvancing cases need an explicit numeric-domain decision. This report
does not alter protected40621517496, current recovery40792865480, original
source bars, registered parameters or any published value. No recovery,
full-world, storage, quality or scoring gate is accepted here.

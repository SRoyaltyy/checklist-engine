# Numeric runtime trace V2

V1(run41065814230) retained all166 counterexamples but could execute164 through
the frozen bar-statistics component. The two explicit unsupported selectors are
`I070_default_per_candle_sigma:rising1__1d`, on NKTR and ABX. V1 reports and source
commits remain immutable; V2 has separate release names and output files.

V2 adds the original frozen `world_indicator_settings.configured_indicators`
calculation, selecting the whole I070 item with **all** its frozen settings.
No setting/period, arithmetic, missing rule or production output is changed.
Only unrelated item calculations are omitted from this diagnostic. The same
baseline repeats, optional NumPy dispatch experiment and prefix schedule run on
all8 mismatch stocks plus2 controls. Any unsupported selector now makes the
diagnostic incomplete and fails after publishing its evidence.

The worker also records NumPy's `opt_func_info` selected log/sqrt/divide targets.
Hardware-capability flags do not by themselves identify the active ufunc kernel.
Separate component-tagged operand/log hashes and exact prefix comparisons are
kept for bar statistics and every I070 setting. This can locate a numerical
dependency; it does not select a production CPU policy, reconstruct all original
numeric values, satisfy full P4/eligibility or open scoring.

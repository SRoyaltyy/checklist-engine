# Williams %R native values and oscillator range execution

The Williams %R adapter used a positive-sign range formula even though its
registered comparison line is -50 and its zones are -20/-80. Execution also
failed before measurement: both Williams %R and Stochastic called NumPy array
`max`/`min` with an unsupported `dtype` argument.

Williams %R now calls the same TA-Lib `WILLR(..., timeperiod=14)` function as
the frozen named `WILLR14` field in `world_timeframes.parameter_variants`.
This preserves the negative-valued field and native float64 operation order.
For a declining synthetic sequence the last value is -93.33333333333333,
matching the registered function bit for bit and falling below -50.

The existing explicit zero-range policy is retained: an undefined range is
NOT_EVALUABLE, never a guessed NO or a known zero. Stochastic's range checks
use the already-float64 arrays' normal extrema API; its declared smoothing
recipe is otherwise unchanged. This does not establish broader Stochastic,
RSI or MACD native/history parity.

Tests load the unchanged frozen source at
`7dcaa48680daeac9a6025c09f9e4d138f5fcbda5` (file SHA
`a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95`).
They compare exact Williams %R bits on rising, falling and oscillating inputs,
check a truncated evidence window against the full native field, exercise
registered negative-midline crosses and zone classifications, and retain
unknown results for zero-range input. A Stochastic zone question also executes
through the corrected range check.

No definitions, thresholds, aliases or frozen producer values are changed.
The master CSV and its canonical hash remain the current batch14 export;
only the implementation fingerprint changes. Real chart/derive/mining and
full-world/PIT acceptance retain their existing gates.

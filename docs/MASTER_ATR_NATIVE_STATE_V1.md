# Registered ATR14 in master predicates

Five master recipes used a simple moving average of true range under the
ATR14 name. The frozen registered field uses TA-Lib ATR14, including its
native Wilder state and operation order. A bounded reseed also loses earlier
state. The price producer itself is unchanged by this correction.

The run-size regression has 70 earlier high/low ranges of 150/50, followed by
28 quiet bars with high100.1/low98.9 and closes100. The last20 bodies are1.
The old ratio is0.8333333333333413 (NORMAL=YES). Registered native endpoint
ATR14 is13.604686992378044, giving ratio0.07350407992188611 (SMALL=YES).
Earlier bodies outside those20 bars cannot participate in the longest run.

MASTER_ATR_NATIVE_COUNTEREXAMPLES_V1.json records bounded before/after
answers for all five consumers against the authenticated prior adapter and
native source. The segment example reverses from EXPANDED to CONTRACTED;
wick, absorption and capitulation examples also change their selected outcome.

The adapter now consumes native ATR14 over the complete supplied completed
candle prefix, before selecting these existing evidence windows:

| Recipe | Evidence using native ATR14 |
| --- | --- |
| run_biggest_move_ratio | Largest body in the longest run inside N, divided by endpoint ATR14 |
| maxvol_wick | First maximum-volume bar inside N, compared with endpoint ATR14 |
| segment_atr_compare | Mean native ATR14 of each leg inside N, pivot in both legs |
| absorption_day | Existing tiny-move/spike/direction/age rules, per-window-bar native ATR14 |
| capitulation_bar | Existing spike/range/shape/size/age rules, per-window-bar native ATR14 |

Full price history initializes native ATR. It does not expand the event
window, maximum-volume search, volume baseline or return leg. Absorption and
capitulation still require their original N+49 contiguous native candles for
the50-bar volume medians. Missing volume before that baseline is irrelevant
to price-only ATR initialization. Missing required volume remains unknown.

The native field needs14 prior changes; NaN warmup is NOT_EVALUABLE. A short
facet window can be evaluated once the supplied native ATR state is known:
the old N<14 shortcut permanently hid valid short-window run/wick questions.
Zero ATR retains each recipe's declared behavior, including undefined0/0
and the existing signed-infinity ratio convention. No epsilon or replacement
native numeric values are introduced.

Tests authenticate frozen source7dcaa48680daeac9a6025c09f9e4d138f5fcbda5,
world_timeframes.py SHA-256
a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95.
Exact native ATR bits are compared across all21 candle sizes and earlier
cuts with future bars supplied. Independent native-field regressions cover
all five consumers, N-only runs/events/leg means, declared volume baselines,
short facet windows, missing data, warmup and zero states.

This is a scalar reference correction. Callers must provide the complete
source prefix. Definitions, cutoffs, question identities and the frozen
producer remain unchanged. The canonical61,941-row CSV keeps SHA-256
d0376513b367c6e989f62d5ac101a6f3a5b644124ec96b564919b1789eaeda77.
The implementation fingerprint and report's warmup prose change. This does
not prove real DERIVE coverage, global PIT, chart acceptance or scoring.

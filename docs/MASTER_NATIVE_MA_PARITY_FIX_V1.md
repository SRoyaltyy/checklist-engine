# Native moving-average state in master predicates

The EMA21 counterexample in `MASTER_EMA_HISTORY_PARITY_AUDIT_V2.json` arises
because the adapter initialized a new EMA inside each facet window. Supplying
98 bars still used only 24 for a three-bar fresh-cross question. That reported
UP=YES where the registered native EMA21 reports NONE=YES. The manual EMA
formula also differs from the registered TA-Lib value by four ULPs on this
example, even when given all 98 bars.

The master adapter now uses the same TA-Lib SMA/EMA calls as frozen
`world_timeframes.parameter_variants` at
`7dcaa48680daeac9a6025c09f9e4d138f5fcbda5`. The reference source file hash is
`a1790bd7eaf7ba747d0dfb3bbea782f58a7977df71f1033e5f3a75eea2973d95`.
The existing requirement already pins TA-Lib 0.8.2.

All six MA-backed recipes use supplied source history for initialization:
fresh cross, cross count, slope, full-stack streak, SMA30-side streak and
weekly stack. Cross/count inspect only the final N bars plus their prior
anchor. Slope and full-stack streak inspect N bars. The SMA30 record comparison
uses exactly its baked H prior bars plus N window bars; older initialization
history does not expand that comparison horizon. Weekly stack reads its
registered fast/slow SMA endpoints.

`evaluate_master` must receive the complete supplied source prefix rather than
a frame trimmed to the facet window. Shared slot//k boundaries remain fixed.
Partial IPO/halt groups are omitted from initialization in the same way as the
frozen native resampler. Required facet/history groups must be present. A
present but invalid or unavailable history bar cannot become known MA state.
Future slots and the current incomplete bucket are excluded.

The frozen producer and its math files are unchanged. This corrects the master
reference adapter; it does not run real derivation, authorize mining, select
new cutoffs, or establish parity for RSI/MACD and other separate recipes.

Regression checks compare float64 bits to the unchanged registered native
function, not a second handwritten MA formula. They cover SMA/EMA on all 21
candle sizes, earlier cuts with a supplied future suffix, IPO/halt partial
groups, the 98-bar answer regression, native SMA stack ingredients, bounded
prior-history comparisons, missing/late input and NumPy integral slot keys.
The existing adapter tests and full master CSV regeneration remain required.

# Literal mirror-ratio intervals, revision 2

This revision fixes the boundary defect reported in Kimi's behaviour audit 4.
It changes the definition contract explicitly; the preceding package remains
available at commit `6dcfced3263533afc13f518258d5eec24451db96`, CSV SHA256
`6b011355c911f4ec4c13d03da73a76aa6ff4d5d8fa553a394fc19768d467e116`.
No previously computed answers or results are rewritten.

For registered upper rung `hi`, the lower literal remains the existing
28-significant-digit decimal `1/hi`. The outer questions remain `ratio > hi`
and `ratio < lo`. The middle question is now
`min(ratio - lo, hi - ratio) >= 0`, using those same literal bounds converted
to binary64. Both endpoints belong to the middle bucket. There is no reciprocal
of the measured ratio, epsilon, edited cutoff, or altered input value.

The old middle formula `min(ratio, 1/ratio) >= lo` failed at a real, reachable
endpoint: five up bars with volume 13 and five down bars with volume 10 give
ratio `1.3`. Binary64 `1/1.3` is `0.7692307692307692`; the existing decimal lower
literal converts to `0.7692307692307693`. Both outer questions and the old middle
question answer NO. The revised interval answers `even=YES`.

All nine bound mirror-band recipes use `ratio_band_contract=
LITERAL_CLOSED_INTERVAL_V2` and carry their two exact bound strings in the
feature. The middle transform is `closed_band_margin`. This changes semantic
question and feature IDs for all 2,994 affected definitions. Historical
`mirror_min` definitions still have their historical evaluator behavior.
Signed non-ratio bands, native indicators, source prices and all other
definitions retain their existing contracts.

The registered grids also contain upper rungs below 1: `0.625`, `0.65`, `0.75`,
`0.938`, and `0.975`. These imply `lo > hi`: their outer predicates overlap and
there is no middle interval. All 888 such definitions remain in the inventory
and return `NOT_EVALUABLE` with reason `INVERTED_LITERAL_RATIO_BAND`. Cutoffs are
not swapped, clamped, deleted, or given an invented precedence. Making these
variants usable needs an explicit domain/ruling decision; this correction does
not claim full question quality or coverage. The build report exposes their
count and rung list. This guard applies only to the new versioned contract.

Validation includes every registered OAT variant for every mirror recipe at
both literal edges and their immediately adjacent binary64 values, finite
interior/exterior probes, zero, infinity, missing values, and independent
bull/bear slots. An unmocked native-bar test covers the 13:10 counterexample.
An authenticated comparison against the previous package requires all 62,558
unaffected rows (59,882 BOUND plus 2,676 ladders) to match exactly, every affected
source variant/outcome to remain present with a new ID, all outer cutoff strings
to remain identical, and feature changes to be limited to the interval contract.

The complete package still has 65,552 rows: 62,876 BOUND and 2,676 canonical
ladders, with four reviewed aliases covering the unchanged 2,680-row source.
CHART, DERIVE, real answer generation and mining remain pending.

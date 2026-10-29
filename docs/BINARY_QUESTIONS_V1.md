# Binary question contract V1

Authority: James/Cyrus §0b at22:51/22:53 HKT on2026-10-29, main
`8cd843f80b05b9bad4df24f4f6ab7d75657127a7` (initial rule `b7add7b`). Every final
question is a measurement plus a literal comparator and numerical cutoff.
Evaluable answers are exactly **NO** and **YES**. `1ac06eb` requires the per-item
order DEFINE → CHART → DERIVE YES/NO → MINE. The subsequent `9e545e9` GO permits
FIRST_SLICE_PRICE_ONLY on `world-2020-26-v2` without waiting for full-world
coverage. It retains that four-step order, excludes NOT_EVALUABLE, holds out
2025–26 and does not turn first-slice evidence into full-world completion.
The full-world quality/leak/eligibility requirements remain separate.

## Executable predicate

`red_count=5, green_count=0` is a measurement; `red_count > 4` is a question.
`red_count - green_count > 0` expresses red majority with a literal threshold.
Doji count in neither colour. `3 > 3` is NO; `3 >= 3` is YES. No epsilon.

`world_binary_questions.evaluate_binary` compares an already computed feature.
Use `answer` or `evaluable` explicitly; implicit truth testing raises.
`known=False`, None and NaN yield NOT_EVALUABLE with a reason, never NO.
Known zero remains evaluable; known signed infinity remains a continuous value.
Adapters must flag unavailable inputs even when storage has a numeric placeholder.
Invalid definitions and unsupported measurement types raise instead of coercing.

Continuous comparisons retain binary64 semantics. Integer measurements compare
to the exact decimal literal; integral cutoffs retain all bits beyond2^53.
Nonintegral continuous cutoffs must fit finite nonzero binary64. The helper
does not compute features, authenticate source data, establish PIT availability,
alter stored precision, or draw charts. The adapter must establish availability
at setup-date open and use candles ending before that date, with exact quantity,
units, warm-up, window, tie and anchor-confirmation rules.

## Definition and identity

The v3 CSV adds `feature_id`, `feature_expression`, `feature_kind`, `feature_unit`,
`comparator`, `comparison_threshold` and conditional `feature_categories`.
The expression fully expands the measurement and its registered settings.
Kinds are continuous, integer_count, category_code and boolean. Units are
explicit: candle counts differ from sums of candle-body sizes.

Comparators are exactly `>`, `>=`, `=`, `!=`, `<=`, `<`. The comparison threshold
is a literal number, never `ATR * 0.5` or `q80`; expose normalized distance as the
feature to compare it with literal0.5. `formula` must be exactly
`(<feature_expression>) <comparator> <comparison_threshold>` on one line.
The fixed `answer_set` is `["NO","YES"]`.

Ladder rungs/opposite predicates can share a feature ID. Reusing that ID for a
different expression/input/PIT rule/kind/unit/codebook fails. Numerically equal
cutoff spellings such as0 and0.0 cannot inflate the question count.

A legacy bull_div/bear_div/none result is a categorical **feature**. It needs an
explicit JSON codebook, e.g. `{"0":"none","1":"bull_div","2":"bear_div"}`,
then separate binary predicates `state_code = 1`, `state_code = 2`.
Codes and names must be unique. Unordered categories/Booleans permit only `=`
or `!=`, using a literal code in their codebook. Boolean codes are0=FALSE,1=TRUE.
Legacy missing code−1 must be marked unknown, never treated as a category or NO.
This contract does not automatically invent codebooks or rewrite old answers.

## Registered ladders and evidence

The existing CSV `threshold` / registry `thresholds` field remains the registered
feature threshold/settings axis. The new `comparison_threshold` is separate.
Three internal settings can share one Boolean cutoff; a measurement can have
multiple registered binary rungs. Each independent variable-registry entry adds
`binary_predicates`, keyed by every declared direction, for example:

```json
{"above":[{"comparator":">","comparison_threshold":"0"},
          {"comparator":">=","comparison_threshold":"1"}],
 "below":[{"comparator":"<","comparison_threshold":"0"}]}
```

The complete lookback×feature-setting×direction×binary-rung product is required
at every applicable candle size. Missing or duplicate numeric rungs fail.
No three-threshold requirement is invented for a Boolean feature.

The sample manifest adds `answer_semantics="STRICT_BINARY_V1"` and
`binary_predicate_code_sha256` for the exact helper file, alongside existing
tree/tally/variable/input/stock-day fingerprints. Tallies contain `n_total`,
`n_evaluable`, `n_not_evaluable` and `answer_counts`. Evaluable equals summed
NO/YES counts; excluded equals total−evaluable. Outcome keys include their JSON
quotes, e.g. `{"\"NO\"":230,"\"YES\"":360}` with590 evaluable/10 excluded/600 total.
NOT_EVALUABLE is excluded, never an outcome. Counts must reconcile. Constant
and >99%-blank questions still fail. Legacy receipts do not inherit a PASS.
The summary fingerprints both the gate and helper code.

The gate does not execute arbitrary feature prose or authenticate upstream
producer inputs. Regression samples are synthetic. Complete template conversion,
full generated v3 CSV, exact drawable bindings, real200-stock2020–22 measurement
and full P4 proof remain unfinished. Kimi owns gallery YES/NO/NOT_EVALUABLE
readouts beside each measurement. Untested definitions/drawings stay disabled.
No scoring result or checklist completion is claimed by this contract.

## BINARY_LADDERS_V1 (2026-10-30 ~00:15 HKT, James)
`docs/BINARY_LADDERS_V1.csv` = strict YES/NO threshold ladders for the 130 items that had 1 setting in `docs/UNDERREPRESENTED_ITEMS_V1.csv`; 10–11 questions per item (1,322 total; MAs have 11). Each row: feature + comparator + explicit threshold, YES condition, NOT_EVALUABLE condition (excluded, never NO), purple viewport drawing (no circles), PIT rule (D-1 completed candle; D open = execution only). Templates by group: MAs (distance ladder, slope, multi-timeframe, count-above); candle patterns (6 timeframes, 20-bar occurrence counts, trend context); all others (252-bar percentile ladder, 5/20-bar change, 5d vs 1d side-by-side, 60-bar z-score). GPT reviews definitions per item and computes answers; Kimi adds readouts.

### Batch 2 (2026-10-30 ~00:30 HKT)
+1,358 questions for the 126 items at 2–8 settings (≥10 each; ids `Ixxx-Lnn`), using each item's dictionary settings (short/default/long or N lists) as rungs. Families: zone oscillators (item-specific oversold/overbought per setting, midline, 5-bar change, cross-up), zero-line oscillators (zero line per setting, rising, signal cross, zero cross), trailing stops (side per setting, ATR cushion 0.5/1/2/3, flip), bands (%B >1/<0 per setting, 0.2/0.5/0.8, squeeze, expansion), RS vs ETF (N=10/20/60, -5/5/10% relative return, RS 60-bar high, outperform-day count). Others: per-setting median and 5-bar change, percentile ladder, 5d vs 1d. **Total V1: 2,680 questions, 256 items.**

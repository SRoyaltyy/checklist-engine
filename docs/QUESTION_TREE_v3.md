# QUESTION_TREE_v3 — implementation contract

Status: specification / gate implementation. The full generated tree and the
200-stock measured quality report are NOT complete. No Step A rerun is permitted
until all world coverage, P3b, and full-tree leak gates pass.
Exception: James/Cyrus `9e545e9` authorizes FIRST_SLICE_PRICE_ONLY without waiting
for full-world coverage, subject to `1ac06eb`'s per-item DEFINE → CHART →
DERIVE YES/NO → MINE sequence. This is not a full-world Step A acceptance.

Authority: METHODOLOGY main, §0b 2026-10-25 23:35 and 23:40 (69bd010, b58906f).
James/Cyrus's22:51/22:53 HKT2026-10-29 update (`8cd843f`) additionally requires
strict binary questions before probability mining. See [BINARY_QUESTIONS_V1.md](BINARY_QUESTIONS_V1.md).

## Construction axes

Data item → candle size k → lookback in completed k-session candles → derivative
and indicator setting → facet → fixed answer set. History questions extend the
same path. k is EVERY integer 1–21; calendar-month candles are an extra separately
named output, never a replacement for the integer grid. Every numeric definition
has its registered range/default. Never silently substitute a default SMA/RSI
period for a differently named dictionary setting.

Every item×facet×derivative×k cell contains at least three lookbacks and three
thresholds/settings, with opposite directions. The total count is a lower bound,
not a ceiling: expanding these axes may produce far more than 26,000 rows.

## Required CSV row

question_id, item_id, block, derivative, facet, candle_days, lookback, threshold,
direction, formula, inputs, pit_rule, answer_set, feature_id, feature_expression,
feature_kind, feature_unit, comparator, comparison_threshold, feature_categories.

formula is the exact expanded expression including the item, numeric parameters,
completed-candle definition and direction. inputs lists actual source columns and
any benchmark columns. `answer_set` is exactly `["NO","YES"]`; unavailable rows
are NOT_EVALUABLE and excluded, never silently NO. A multi-state history output
is a feature requiring codebook-bound binary predicates. The formula is exactly
`(<feature_expression>) <comparator> <comparison_threshold>` with a literal
numeric cutoff. Rows that merely rename the same formula are rejected.
Canonical aliases can share a question ID via an explicit alias/coverage table;
they cannot inflate unique question counts.

## Core facets

- absolute: level in its declared units compared to a registered threshold;
- own_history: percentile/z-score or relative level against earlier values;
- peer_relative: the same item against PIT peers/sector/market in comparable units;
- position: location in a range/band, distance from the high/low/average;
- direction: signed change, slope and acceleration;
- crossing: crossing a level/another line, with an exact within-N rule;
- extremes: new N-high/N-low against earlier completed candles;
- divergence: confirmed price/item pivots, using dictionary confirmation and last-K rules;
- persistence: exact condition and its count/streak over N native candles;
- state_change: explicitly defined previous/current buckets and flip direction.

History: same-state retest counts and subsequent reactions available before D.
Events additionally need recency/count/direction facets; time-until is permitted
only when the schedule's original publication was already known before D.

Zero cells require a semantic type-specific reason. Missing upstream data is a
blocker, not a semantic exemption. Non-price blocks must reach at least 50% of the
price/volume median depth; the depth check includes items with zero questions.

## Empirical quality gate

ci/question_quality.py accepts the full active-item catalog, generated tree CSV
parts, per-question answer-count tallies, a provenance-bound sample manifest, and
optional item/facet exemptions. It writes QUESTION_QUALITY.csv and facet counts.

The gate also requires `--variables VARIABLE_GRID.json` and `--sample-rows
SAMPLE_STOCK_DAYS.csv`. The variable registry is declared independently of the
generated rows: one record per item/facet/derivative with `item_id`, `facet`,
`derivative`, `lookbacks` (positive integer list), `thresholds` (canonical string
list), and `directions` (string list containing an opposite pair). Lists are
unique and every applicable cell has at least three lookbacks and thresholds.
The generator must expand the complete registered ranges, not infer them from
whatever questions happened to be produced. For every integer candle size 1–21,
the gate requires the full Cartesian product of each declared window, threshold
and direction. Three separate marginal counts cannot prove that product. A
registered fourth setting cannot disappear just because three others remain.
Duplicate parameter combinations cannot inflate depth, even under different IDs.
Every registry entry additionally declares a `binary_predicates` ladder for
each direction. The complete product includes every rung, independently of the
existing feature threshold/settings axis. Missing/duplicate numeric rungs fail.

The sample contains at least 200 deterministic stocks and years 2020,2021,2022.
The manifest binds the tallies to the exact tree digest and input manifest.
It now also contains `tallies_sha256`, `sample_rows_sha256` and
`variable_grid_sha256`, `answer_semantics="STRICT_BINARY_V1"` and the exact
`binary_predicate_code_sha256`. File digests use `ci.question_quality.tree_digest` (raw
bytes concatenated in sorted path order); the variable digest uses
`variable_digest` (the supplied JSON list serialized with sorted object keys and
compact separators). The stock-day CSV contains `ticker,date`; canonical ISO
dates, unique stock-day keys, ticker membership, year membership and actual row
count must agree with the sample manifest. Input provenance must be a 64-digit
SHA-256. These checks bind evidence; the source producer must still independently
verify that the sample rows and input manifest came from the released world.

Tally `answer_counts` keys are canonical JSON encodings of NO and YES strings,
including their JSON quotes. `n_evaluable` equals their summed count;
`n_not_evaluable` equals `n_total - n_evaluable`. Excluded rows never enter NO.
Counts are nonnegative integers, never coerced
booleans or fractions. Unknown outcomes, duplicate JSON keys, orphan tallies,
catalog/block mismatches and malformed fixed answer sets fail. Null remains
missing, not a declared answer. Legacy sample summaries without bound files and
a declared variable registry fail rather than inheriting a historical PASS.
Constant questions and >99%-blank questions fail. A structural count alone can
never produce PASS. The answer evaluator and full-tree leak verifier must cover
the same IDs and formulas before this gate is treated as complete.
The gate does not itself execute arbitrary formula prose or authenticate upstream
source files. Its regression fixtures are synthetic test inputs, not a real
200-stock quality measurement. Full generated coverage, real sample tallies and
full-world leak proof remain pending; this change supplies no P3b completion claim.
The summary records the exact gate-code, sample-manifest, stock-day, tree,
tally and variable-registry fingerprints alongside its explicit PASS/FAIL status,
including on an empty-catalog failure.

All generation/empirical evaluation on real inputs runs on GitHub runners.
Persist tree parts and tally checkpoints; merge counts instead of materializing
all questions×stock-days in RAM. Publish the full generated CSV as versioned
release parts if it exceeds GitHub's per-file limit, with its digest/index here.

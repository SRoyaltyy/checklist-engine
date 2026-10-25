# QUESTION_TREE_v3 — implementation contract

Status: specification / gate implementation. The full generated tree and the
200-stock measured quality report are NOT complete. No Step A rerun is permitted
until all world coverage, P3b, and full-tree leak gates pass.

Authority: METHODOLOGY main, §0b 2026-10-25 23:35 and 23:40 (69bd010, b58906f).

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
direction, formula, inputs, pit_rule, answer_set.

formula is the exact expanded expression including the item, numeric parameters,
completed-candle definition and direction. inputs lists actual source columns and
any benchmark columns. answer_set enumerates all permitted outcomes; blank is
unavailable, not a no answer. Rows that merely rename the same formula are rejected.
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

The sample contains at least 200 deterministic stocks and years 2020,2021,2022.
The manifest binds the tallies to the exact tree digest and input manifest.
Constant questions and >99%-blank questions fail. A structural count alone can
never produce PASS. The answer evaluator and full-tree leak verifier must cover
the same IDs and formulas before this gate is treated as complete.

All generation/empirical evaluation on real inputs runs on GitHub runners.
Persist tree parts and tally checkpoints; merge counts instead of materializing
all questions×stock-days in RAM. Publish the full generated CSV as versioned
release parts if it exceeds GitHub's per-file limit, with its digest/index here.

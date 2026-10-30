# Canonical binary conversion plan

The authoritative source is the15,093-row v2.7.2.2 question-cutoff table and
v2.7.1 tree. `world_question_grid.CanonicalGrid` validates exact question
membership, source IDs, defaults, all232 registered numeric cutoff grids,
per-question cutoff counts and both declared expansion counts.

The denominator reconciliation is:

| Count | Meaning |
|---:|---|
|232|Unique cutoff definitions in CUTOFF_GRID.|
|35,647|Question-to-cutoff associations across15,093 questions; a shared cutoff is counted once for each question using it.|
|154,667|All one-at-a-time source variants, including one default vector per question:1+sum(grid_size−1).|

This does not substitute a full Cartesian product for the registered OAT plan.
The full-cross counts are validated separately. Every source question and
registered rung survives; numerical spellings are canonicalized exactly using
Decimal, without float conversion or decimal-context rounding. Ordered variant
identity digest:5d01e4094af9dab4f5016690458fbded66e0eadfdee5ffbd8170ad29045ccdc5.

`python -m ci.binary_canonical_plan --out <directory>` emits the complete gzipped
variant plan, bound definitions, source-alias ledger, unbound-family ledger,
per-question14-lens coverage and source/code/output hashes. CI publishes these
as an artifact. It is **not** the completed `BINARY_MASTER_V1.csv`; all unbound
families and the later BINARY_LADDERS add-on remain required conversion work.
No incomplete semantic key is used to declare two unbound questions duplicates.

## Explicitly bound initial price definitions

The initial reference adapters bind all registered variants of the canonical
OHLC intraday_change and interday_change families:38 source questions,
190 OAT variants and570 distinct binary definitions, retaining570 source aliases.
The remaining154,477 OAT variants are explicitly unbound.

Intraday change is the binary64 mean of per-candle(C−O)/O, preserving operation
order. Interday change is last close/first close−1 across N closes, spanning
N−1 intervals. Up and down use the signed literal percent converted exactly
to a fraction; flat uses abs(value)<=cutoff, preserving endpoint equality.
IDs use the expanded feature recipe, native timeframe/lookback, price basis,
numeric contract, transform, comparator and exact cutoff. Labels do not define
semantic identity. These are price predicates, not raw measurements sent to mining.

Callers must supply trusted native candles on the fixed shared session calendar,
PIT split-adjusted compatible OHLC and a known-before-open date contract. The
reference interface rejects missing/out-of-order slots, missing or nonpositive
prices, unavailable inputs and setup-date candles, and never searches backward
to replace a missing slot or reads future prices. It does not independently
certify the caller's calendar, price adjustment lineage or release binding.
Compared with the old NaN-only checks, the strictly positive-price domain is
explicit. These native definitions do not overwrite legacy rolling-offset arrays.

Every bound row remains `expression=NOT_YET`, with the missing tested renderer
and released-source binding named; CHART/DERIVE/MINE stay PENDING. Synthetic
predicate execution is not a real-data answer or chart-gate claim. All15,093
questions remain flagged below six implemented lenses. Absolute/threshold
aliases receive one reading credit, and every other requested lens is named
as pending rather than declared inapplicable. See `LENSES_V1.md`.

The remaining conversion must resolve exact scalar/categorical quantities,
internal cutoff bindings, first-match priorities, coupled thresholds and source
edge rules. For example, the old OHLC green/red family uses counts/max(red,1),
not body-size sums; its low boundary and high-boundary coupling need explicit
binding. Old wick recipes include a denominator epsilon; that cannot silently
be carried into the newer no-epsilon contract. Full source families, history
definitions, all applicable lenses and reviewed add-on ladders remain in scope.

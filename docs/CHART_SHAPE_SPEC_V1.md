# Chart shape and side-by-side contract v1

Authority: James158(`0439ef96e263eb12a44eddf370a1a46a645dc607`), approved by
Cyrus; READY-order159(`15e3bae29c7d8837949360b18019698e267cf3ff`). GPT owns
this grid/definition; Kimi owns the renderer. The machine-readable contract is
`dictionary/CHART_SHAPE_REGISTRY_V1.json`; reference arithmetic and outcome
cutoff handling are in `world_chart_shape.py`.

This registers two raw inventory items, not a completed universe search or a
claim that their v3 question facets/quality gate are implemented. All scored
use remains subject to the complete world, question, PIT and eligibility gates.

## Fixed grid

| Axis | Registered values | Default | Unit |
|---|---|---|---|
| N |10,20,60|20|completed native candles|
| Y |every1d–21d plus calendar monthly|1d|genuine non-overlapping candles|
| K |every integer1–21|5|daily market trading sessions, even when Y is monthly|

The N values preserve the existing short/default/long10/20/60 lookbacks.
Y preserves the full22-frame world grid. K explicitly spans every session
through about one trading month. These are complete finite ranges; do not
replace the integer Y/K grids with just5/10/20. N×Y has66 cells; N×Y×K has1386.
These are parameter cells, not counts of distinct questions. Similarity is
strictly greater than0.90, fixed by James158; no threshold tuning grid is added.

## Shared window and price definition

S is an actual market session's setup-date open. Take the last N consecutive
native grid intervals at Y, inclusive of the latest interval whose source end
is < S and availability <= S. Prices are each interval's completed close.
All N prices must be finite and positive. Missing intervals remain in their
positions and invalidate the window; do not compress gaps, interpolate, select
an older fully known window or include day-S OHLCV. Monthly price candles
become available at the actual next market session. Retain the common frozen
calendar anchor rather than resetting it at2020 or at a ticker's IPO.

For each window independently, from oldest to newest:
`z_i=(C_i-min(C))/(max(C)-min(C))`. A constant range is unknown. Every tied
minimum maps to0 and every tied maximum to1; no unique anchor bar is selected.
Doji are included via their close. Red/green counts, body size, high/low wicks,
volume, swing/pivot detection and chronological extrema tie selection do not
enter this definition.

Pearson rho uses centered normalized close vectors of equal N with no time
warping, lag search or offset optimization. The reference uses binary64 and
`math.fsum` for the means and centered product sums, then divides by the square
root of the two square sums. Only final roundoff outside[-1,1] is clamped.
The decision is exactly `rho > 0.90`; no epsilon or display rounding is applied
before comparison. Unknown correlation is unknown, not NO. Positive-affine
normalization does not create a second distinct Pearson formula: normalized
and raw-close correlations must not inflate question counts.

## I227: historical close-shape matches

Scan every distinct window of the authenticated approved universe over all
available source history, with candle end < S and availability <= S. Windows
use the same N/Y but may end on different historical dates. No hidden history
cap, chosen ticker subset, preselected shortlist or approximate-neighbor filter
can support a full-pool claim. A safe search acceleration must prove that it
excluded no possible strict match.

Candidate identity is `(ticker,Y,candle_start,candle_end)`. Repeated identities
are an error. Exclude the identical target window. Other overlapping windows,
including same-ticker overlaps, remain in the pool and are labelled; counts
are window counts, not independent observations. Do not silently deduplicate
them into one match per ticker. Publish pool membership, valid/unknown windows,
eligibility exclusions and source/recipe hashes with any measured result.

Apply the standing historical tradeable/>=$100M policy at S for the target
and at each candidate's native availability for historical candidates, with
raw nominal price and shares known then. Adjusted shape prices do not prove
nominal size or eligibility. Unknown eligibility/source coverage cannot be
silently treated as false or removed from a full-pool claim. Keep survivor and
instrument-class scope explicit in the authenticated universe manifest; do
not rename the accepted source universe as every historical US listing.

The K-session outcome starts from the candidate window's closing price.
Locate its end in the actual daily session calendar, then advance exactly K
sessions and use that session's close:
`R_K=C_end+K/C_end-1`. This is a descriptive close return, not a simulated
next-open trade or net profit. For monthly Y, K=5 still means five daily market
sessions, not five months. Both endpoint prices must be finite and positive,
and the outcome endpoint must be strictly < S. Day-S open/close or any later
price is never used. A missing endpoint stays unknown; do not jump to a later
available price. An unmatched/unmatured result is not a negative return.

| Output | Definition | Empty/unknown rule |
|---|---|---|
|match_count(N,Y)|number of eligible strict matches in the complete pool|0 only after a valid complete scan; invalid target/pool = unknown|
|matured_count(N,Y,K)|matches with known exact K-session outcome before S|0 when no outcomes are known in a complete valid scan|
|up_pct(N,Y,K)|100×number with R_K>0 / matured_count|blank if denominator0; zero returns are not up|
|median_return(N,Y,K)|exact median of known R_K, midpoint of the two central values when even|blank if denominator0; no approximate quantile|

match_count does not depend on K and has one canonical formula per N/Y.
Return summaries use the known-outcome denominator, never every match. Their
overlapping samples and up percentages are descriptive historical features;
they do not establish independent statistical evidence, a reliable forecast
or P(net profit>0). Existing full-data/quality/leak/scoring gates still apply.

Rank all matches by rho descending, end date descending, ticker UTF-8 bytes
ascending, then start date ascending. The first up to5 are the viewport matches.
This ranking is independent of K. If a shown match has no known K outcome,
show its shape and dates without fabricating a return. Top5 geometry is a
receipt/drawing output, not five additional scored scalar questions.

## I228: side-by-side normalized close lines

Use the exact same N/Y interval keys for target and comparator. Draw each
window's own0–1 normalized close series on those absolute candle dates.
The numeric shape correlation uses the same close-vector formula above;
it is distinct from I069/I218/I225 correlation of native-candle **returns**.
There is no K axis and no forward outcome in this comparison.

Allowed roles are literal SPY, a sector ETF, or a literal theme peer. Select
sector/theme identity using dated membership known strictly before S and
effective as of S. Use that one literal comparator through the entire window;
do not splice ETFs inside the window, average peers, backfill from today's map
or substitute SPY for an unknown sector/theme. Expand one view per explicit
peer; source/membership evidence must name it. Self-comparison is excluded.
Missing membership, prices or matching intervals makes the answer unknown.

## Exact viewport contract

For I227, recolour exactly the N target native candles purple (bodies+wicks).
Show a pane with the current normalized close line in purple and the top up to5
match lines at relative candle indices0..N-1. Each historical line/mini-chart
names its ticker, actual dates, rho and overlap status. Show S as the cutoff;
no candle at or after S is highlighted or used. Show match count and the
K-specific known-return denominator. Only known historical K endpoints receive
endpoint markers and return labels. No rings or guessed swing anchors.

For I228, recolour the target N candles purple and overlay target/comparator
normalized lines on identical absolute native dates. Label both literal
identities, membership-as-of date for a mapped role, N/Y, rho and S. A missing
comparison is unavailable rather than a made-up line. Candle colour and doji
do not affect which closes enter the comparison.

Kimi can replace the unspecified-grid blocker with this exact definition.
This commit does not enable an unimplemented global search or invent match
payloads in the gallery. Rendering still requires a tested binding to these
inputs/outputs. `world_chart_shape.py` supplies pure reference normalization,
correlation, strict match and known-outcome primitives; it performs no universe
search, peer selection or eligibility inference. No real-data coverage,
complete v3 facet tree, empirical quality, full PIT eligibility or scoring
acceptance is claimed by publishing this contract.

## Catalog integrity

While adding I227/I228, registration found that the pre-existing I204–I226
definitions were missing from DATA_SOURCES, world_coverage_map and the master
dictionary coverage grid. All25 derived IDs now have explicit source/field
registrations and550 PENDING item×timeframe rows. Existing measured rows are
preserved; these additions do not claim values, coverage or a source fetch.

`ci.audit_inventory_catalog` requires every dictionary item in the source/map
catalogs and every one of its22 coverage rows, with no duplicate identities.
New derived PENDING registrations require reasons. The audit separately reports
legacy PENDING rows that still have no reason, rather than calling them valid
world evidence. It does not replace the full WORLD_COVERAGE gate, which remains
failed until actual source values and complete measured bindings are supplied.

## Binary-question addendum (James/Cyrus8cd843f)

Normalized curves, correlation, match counts and outcome aggregates are features.
Each final question needs its own literal comparator/cutoff and strict YES/NO
answer. The existing strict Pearson>0.90 match predicate already has that form;
other measurement readouts do not automatically become approved questions.
Use [BINARY_QUESTIONS_V1.md](BINARY_QUESTIONS_V1.md) for typed predicates and
NOT_EVALUABLE exclusions. No unregistered threshold ladder, active renderer or
probability mining is enabled by this addendum.

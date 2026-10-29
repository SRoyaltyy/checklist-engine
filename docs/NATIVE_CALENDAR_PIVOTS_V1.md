# Registered I074 calendar pivots

`world_calendar_pivots.native_calendar_pivots` supplies the missing existing
I074 settings: short=week, default=month, long=quarter. Each produces P, R1,
S1, R2 and S2 in float64. The formulas are exactly the dictionary formulas:
P=(H+L+C)/3; R1=2P-L; S1=2P-H; R2=P+(H-L); S2=P-(H-L).
No new item, setting range, question identity or threshold is registered.

An anchor is a calendar week (Monday–Sunday), month or quarter. Its HLC is
aggregated from every expected market session in the frozen calendar, using
daily source rows. A missing session, nonfinite HLC, nonpositive low or
inconsistent high/close/low makes that entire anchor unknown. An IPO midway
through an anchor cannot produce a partial-period pivot. The calendar's first
anchor is conservatively unknown because its left boundary cannot be certified.

At each genuine native row's `available_from`, the immediately preceding
calendar period supplies the levels. A missing prior period stays unknown;
an older valid period is never carried across it. The complete query-day row
is excluded. Current partial weeks/months/quarters are never included. Monthly
native availability is the actual next market session, including holiday gaps.
The raw calendar anchor is independent of candle size: a native candle crossing
an anchor boundary cannot supply a substitute HLC. The levels are sampled at
native availability and can be attached with the existing row-view join.
They may remain identical across timeframes because the definition fixes the
calendar anchor. This is explicit calendar context, not a rolling N-bar proxy.

These values do not infer current-bar availability, historical tradeability,
market cap, or nominal-price correctness. A known prior-period pivot does not
prove that the stock is tradeable at D. The input/source calendar must be
authenticated by its caller. All expected native rows, including missing and
pre-IPO intervals, remain in the output grid.

This adapter is separate from `configured_indicators`, whose native-array-only
API lacks complete daily calendar anchors. The old recipe audit deliberately
continues to report that integration missing; published recipe fingerprints
and output values remain untouched. Full-universe integration and measured
WORLD_COVERAGE rows are still required before any checklist claim.

The precommitted `ci/CALENDAR_PIVOT_REQUEST.json` retains the original
MAN/MNTS/EYE+SPY source bytes and two cutoffs. The GitHub proof requires all
three registered anchors/five levels on all22 real grids (88 frames), exact
Parquet persistence and regeneration, and176 independently truncated raw and
calendar rebuilds. A separate scalar daily-record oracle checks every numeric
cell, including unknowns, independently of the production aggregation. Local checks cover literal HLC calculations, holiday and
quarter boundaries, incomplete anchors, missing periods, source identity and
every native grid. No local dependency installation or world computation.

Actual GitHub measurement is pending. This proof does not establish full
universe coverage, v3/history quality, comprehensive leakage/PIT eligibility,
portable exactness, the full dependency budget or scoring. No checkbox is
claimed.

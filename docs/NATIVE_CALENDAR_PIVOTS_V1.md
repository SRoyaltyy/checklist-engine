# Registered I074 calendar pivots

`world_calendar_pivots.native_calendar_pivots` supplies the missing existing
I074 settings: short=week, default=month, long=quarter. Each produces P, R1,
S1, R2 and S2 in float64. The formulas are exactly the dictionary formulas:
P=(H+L+C)/3; R1=2P-L; S1=2P-H; R2=P+(H-L); S2=P-(H-L).
No new item, setting range, question identity or threshold is registered.

Definition details under James155: H is the maximum daily high wick, L the
minimum daily low wick, and C the final session's close in the anchor. All
sessions in that anchor are included. Equal high/low values give the same
numeric level; the adapter selects no unique extreme-bar index. Any drawing
requiring a single tied extreme's location must mark that choice AMBIGUOUS
until its definition supplies a tie rule. Colour, doji and body size do not
enter these formulas. All five outputs are continuous price levels in the
authenticated source's price units and adjustment basis; no unit conversion
or nominal-price/PIT claim is made. Calendar quarters are Jan–Mar, Apr–Jun,
Jul–Sep and Oct–Dec.

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

Actual run40856073326 at4f6d8c9 passed53 Linux tests6.90s and all88 native
frames, with176 raw/calendar cutoff rebuilds. All2,053,680 numeric cells were
checked against the independent scalar oracle and exact persisted regeneration;
1,194,285 were known, and6,840,295 bytes of temporary native references were
written. Every mismatch count is0. Each sample retains34,228 native grid rows,
including pre2020/pre-IPO history; this is not a2020–26 universe fill rate.
MAN/MNTS/EYE/SPY calculation times were12.17/11.22/11.34/12.11 seconds.

The public299,701B `CALENDAR_PIVOT_MEASURED_V1.json` has SHA256
`a0959e6a40ca31bf9c6db89fcf4b980f0905f3cf55ecbc38277a821394a484a8`.
`CALENDAR_PIVOT_PUBLIC_READBACK_V1.json` authenticates the public bytes, all17
code/registry hashes, original source pins and every reported schema, grid,
scalar, persistence and cutoff receipt. Native reference files were temporary
runner files, not independently downloaded numeric bodies in this readback.

Full-universe integration, measured WORLD_COVERAGE, v3/history quality,
comprehensive leakage/PIT eligibility, portable exactness, the full dependency
budget and scoring remain unproved. No checkbox is claimed.

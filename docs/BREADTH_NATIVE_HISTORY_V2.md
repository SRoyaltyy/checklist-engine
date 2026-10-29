# Complete native breadth history, version 2

Status: full-name V2 measurement and V3 availability correction passed.
Native and measured component claims require James's independent sign-off.

Actual V3 run40789973576 passed51 Linux tests, inherited44 raw input cutoff
checks and performed44 additional availability-prefix checks. Independent
public readback authenticated all28 assets /6,918,925 bytes, all22 factors
/3,779,577 bytes,9271 daily and34229 native rows. All330 column/timeframe
coverage measurements were independently recomputed on12,364,370 actual
approved stock-days:100%, first2020-01-02 through2026-10-23. Every factor's
numeric Arrow field carries the survivors-only label. All known numeric bits
and interval keys remain unchanged; only unavailable warmup is made missing.
See `BREADTH_V3_INDEPENDENT_READBACK_V1.json`, `BREADTH_WARMUP_MEASURED_V3.json`
and `BREADTH_FACTOR_STORE_V3.json`. Full-world, historical eligibility and
complete dependency-budget/scoring gates remain open.

Actual run40718683563 passed46 Linux tests, all8316 source names and44 raw
cutoff checks. It published9271 daily rows (7559 before2020),34229 native rows,
all22 factor files /3,759,569 bytes,330 weighted coverage rows and a successful
public-factor readback. V1 daily/complete-native values reconstruct exactly
with the285,222 pre2020 A/D offset. All28 public assets /6,883,267 bytes were
independently downloaded and authenticated.

Independent readback also found an availability defect before promotion:
251 initial sessions have zero eligible52-week histories, but observed-hit
counters are zero. One initial session has no previous-close movement votes.
These counters are not usable known market outcomes. V3 retains the original
V2 counter file and its raw-source proof, exposes those unknown fields as
missing, and requires every daily flow value inside a native bucket. It also
enforces I179's more-than100 eligible SMA names. Known values, all interval
keys and all data within the2020–2026 measured window must remain unchanged.
The correction reads only the completed public V2 release; it does not repeat
the full raw-source build. It gets its own immutable V3 release and public
readback after fresh51-test/cutoff verification.

The verified V1 files remain immutable. Their aggregate starts on 2020-01-02
inside the calendar's anchored integer buckets, producing twenty partial
opening candles. The V2 producer reads the same authenticated, approved
8,316-name raw archives and retains aggregate sessions from the frozen calendar
origin, 1990-01-02. It preserves all 22 existing timeframes, with no new data
type or question.

Each native bucket must contain exactly its complete, ordered calendar session
set, including its start and end. An interior missing session, partial opening
bucket or incomplete month cannot become a completed candle. Availability is
the next session after the source candle end, including calendar monthly.
The shared `world_timeframes.py` and protected price build are unchanged.

Flow counts/volume are summed within the complete bucket; fractions and the
cumulative A/D line are the last session's levels. Ratios and NH-NL are rebuilt
from the sums. These are native aggregates of the registered daily breadth
series, not price indicators with renamed candle sizes. SMA20/50/200 keep their
registered daily-session meanings.

The A/D line's origin changes explicitly with the retained full history. V2
cumulates from the frozen calendar origin. V1 cumulates from 2020-01-02. V2
records the exact pre2020 net total, and subtracting it reconstructs every
original post2020 V1 line value. The producer verifies every V1 daily field and
every complete V1 native field exactly; twenty partial V1 rows remain preserved
in the original release and are excluded from native certification. No
retrospective offset is applied to early V2 values: they remain causal.

All storage is reopened and compared, including float64 NaN payloads and signed
zeros. Count conversion must be exactly reversible, never tolerance rounding
or integer truncation. Full raw recomputations at the two registered cutoffs
test every column on all22 grids (44 comparisons), in addition to daily prefix
readback. Stock-day coverage uses the authenticated 12,364,370-row denominator.

The single-runner workflow publishes a new versioned release only after these
checks. It publishes daily/native panels, all22 flat-named factor files, actual
stock-day coverage, the factor manifest and measured proof, then finalizes the
draft. It downloads each published factor again and runs the actual release
binding audit; that readback report is also published. The manifest binds the
transformed assets in their own actual release, not the original source paths.

Only existing GitHub archives are read. There is no vendor/SEC/news fetch,
local dependency installation, protected-world restart or source selection
change. Outputs are a breadth component: historical universe/eligibility,
remaining world types, complete question state, comprehensive world leak proof
and the complete dependency budget remain separate open requirements.

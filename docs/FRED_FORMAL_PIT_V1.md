# Formal PIT proof for the published ALFRED factors

This proof targets James's15:15 order and the open formal FRED input check,
including box1.185. It uses all21 series in the existing float64
`shared-context-v2-40636949344-1` factors, including all eight16:35 additions.
Both raw source archives, their exact Parquet members, the original calendar,
all22 factor files and the existing producer math are authenticated before
any check. No new vendor request, source replacement or value rewrite occurs.

The precommitted request is `ci/FRED_PIT_REQUEST.json`; implementation is
`ci/fred_pit_measure.py`. The actual GitHub result is pending. No checkbox
is claimed before reviewing its measured public evidence.

Initial40860076559 atbd091d1 passed25 Linux tests but the harness required a
BAMLH0A0HYM2 timeline before that series had a source vintage. The historical
cutoff correctly had none, so the run failed without accepting a result.
Version2 preserves all168 expected columns while treating any not-yet-available
timeline as explicit NaN. It still requires exact equality to every released
prefix; no series, field or cutoff is excluded from the comparison. Synthetic
coverage includes a series first appearing after an earlier cutoff. Progress
and failure JSON are retained on the runner if a subsequent check fails.

Request2 actual40860927415 passed25 Linux tests1.69s,5,750,304 native cells,
6,327,552 reader-projection cells and176 fresh-prefix checks, all exact.
The public report SHA256 is
`3baf11951ad5b2ef0410f63e4aafdb7e95c545bb45a9238b697b77c6aa1c4742`.
Before claiming the checklist's explicit real-time-period requirement,
request3 additionally uses a complete per-observation active-version ledger
and records the revision-interval witness for every known oracle value.
A missing revision withdraws its observation in this independent ledger;
it cannot silently retain that observation's prior value. Any difference
from the existing producer fails the proof. Production code is unchanged.

## Exact definitions

For an availability cutoff A, only source records with `vintage_date < A`
are visible. An observation dated after its own vintage is ignored, as is a
missing value. The latest level is the latest-known value for the greatest
valid observation date. Revising an older observation cannot replace that
latest observation. `first_release` is the first valid known value for the
same observation, retained through later revisions. The requested sticky-CPI
identifier uses official STICKCPIM159SFRBATL via the existing explicit alias.
Levels and first releases retain each source series' published units; no
percentage, annualization, interpolation or unit conversion is added.

`_odays` counts calendar days from the selected observation to A.
`_vintage_days` counts calendar days from the most recent processed vintage
of that series to A. The latter date advances even when a vintage revises
only an older observation; it does not mean the age of the last numerical
change. Both are represented as float64 calendar-day counts, blank when
unavailable. `_change20`/`_change60` are x(t)-x(t-N) in the same source units,
on native samples, for both levels and first-release values. They are not
percentage changes. Unknown operands remain unknown. Age fields have no
change variants. These are eight existing fields per series,168 per factor.

The exact published1d–21d grids retain their1990 calendar anchor. Calendar
months use the published next-calendar-month boundary, which may be a
nontrading day; this proof retains that existing conservative sampling rule.
The stock-day reader attaches only factors with source candle end < D and
availability <= D. It never makes a query-day vintage visible. Candle colour,
body/wick rules and extreme-price tie selection do not apply to these macro
values. Conflicting values at one series/observation/vintage fail explicitly.

## Independent and fresh rebuild evidence

An independent scalar online oracle processes the raw vintages in chronological
groups. At every distinct native availability across all22 grids, it consumes
only groups strictly before that cutoff. It never calls the production
timeline compiler, FRED column function, as-of join or factor builder. Every
existing native numeric cell, including unknowns and float64 bits, is compared
against this independent state and independently calculated native changes.

The production compiler independently reproduces every released FRED field
from the original raw inputs. At every2020–26 market query session, the real
factored reader is also checked against a separate binary-search projection
of the independently rebuilt native values, for every timeframe and column.
This projects the shared date factor once per date, not a sampled subset of
stocks; stock eligibility and denominators are separate requirements.

In addition, eight fresh compiler invocations receive physically filtered
raw tables with vintage_date < cutoff and a truncated calendar preserving its
original anchor. The cutoffs are the first actual session in every year2020–26
and the final2026-10-23 session. Each rebuild compares the complete earlier
prefix on all22 grids, not just the most recent row. The exhaustive online
oracle is distinct from these eight fresh-from-scratch prefix rebuilds; the
proof does not describe eight rebuilds as one rebuild per market day.

All checks are exact and fail on discrepancies. Real source computation runs
only on GitHub. Local tests use synthetic inputs; no onboarding or dependency
installation is performed. This verifies the existing FRED source/factor and
reader surface, not full v3 question/history leakage, price look-ahead,
historical tradeability/$100M eligibility, the full world/storage gate or any
scoring result. Those gates remain open.

# UNBLOCK_RESULTS_V1 — free-data unblock of the Taskforce master ideas (2020-24, survivors only)
Pre-registration: unblock/UNBLOCK_V1.md (committed before results). Per-idea verdicts: unblock/unblock_coverage_v2.csv. Full numbers: unblock/unblock_results_v1.csv.

## Headline: 0 of 99 features pass (both exits, both periods).
- Population: 2,408,833 buyable stock-days (story_q panel, drop_list_v2, <=2024-12-31). No 2025-26 data opened.
- Method identical to history10y: Exit A (+20% target / day-15 close), Exit B (10-day hold), 0.6% round-trip fees, excess vs same-date mean, 500x date-clustered bootstrap, BH.
- BH family as pre-registered: 6,802 prior + 396 new = 7,198. Re-checked against the newer cumulative base ~13,300 (stricter): still 0 pass.
- Fixed answers: none of my built ids is in James's fix2023_v1 SHARED set (d0cc82a) or its missing-as-NO list; every answer here was built from its own source.

## Coverage (297 ideas I own)
| group | built+tested | buildable, not built | blocked | timing fail |
|---|---|---|---|---|
| 272 free-source ideas | 93 | 48 | 131 | - |
| 11 earnings ideas | 6 | 0 | 5 | - |
| 13 fails-09:25 ideas | - | - | - | 12 redefine, 1 drop (EVT-NB-005) |
| 10-year history | tested earlier (history10y, 0 pass) | | | |

Earnings blocked: ERN-NB-002, EVT-TR-002 (2020-24 Nasdaq rows have no before/after-open time), ERN-NB-005 (no revenue), ERN-NB-006/007 (no fixed-label guidance).
CAL-JA-032 earnings-peak week: 0 YES rows under the pre-registered 1,500/week threshold (Nasdaq calendar max ~1,300), so untestable; not re-tuned after the fact.
New since registration: SEC share counts (New Bot Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4) make FND-NB-001, SUP-NB-004 and the %-of-market-cap version of PV-TF-452/455/458 buildable; marked, not built.

## Closest misses (stock-level; win >55% and beat average in both periods, but failed q)
- PERF_W30 exit A: wins [56.0, 55.4], q [0.149, 0.753]

## Market/calendar features
These are the same for every stock on a date, so they cannot beat the same-date average (excess = 0 by construction); none can pass the bar. Descriptively, days that had >55% Exit-A wins and beat all-days in both periods: ELECTION, STLFSI_JUMP, WTI_LO252. Small samples of dates; not evidence.

## Caution
Survivors only: stocks that died or delisted in 2020-24 are missing, which flatters every long idea. A pass here would still need a non-survivor check; with 0 passes, the honest read is that none of these free-data checklist items picks better-than-average stocks on its own.

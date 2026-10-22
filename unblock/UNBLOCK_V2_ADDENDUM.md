# UNBLOCK_V2 addendum (pre-registration, written before any wave-2 result)
Registered 2026-10-23 ~03:10 HKT, after UNBLOCK_V2.md (24e45c9). Source of the change: James master list v1.2 (commit 227223e, coverage_v1_2/).

## Test-count base (replaces the base in UNBLOCK_V2.md)
Cumulative luck-correction base = **13,851** prior tests (room figure; includes wave 1). Family n = 13,851 + every wave-2 p-value (features x 2 exits x 2 periods). BH as before: wave-2 p-values ranked among themselves with that n (prior tests treated as p = 1; strictest).

## v1.2 check
The 40 ideas v1.1 called built that v1.2 moved to BLOCKED: **none** is in my 48 (checked id overlap = empty). Nothing skipped for that reason.

## Added to wave 2 (13 ids)
| feature | id | YES if |
|---|---|---|
| SMA20_SLOPE_UP | PV-TF-159 | SMA20 at close D-1 > SMA20 at close D-6 (no ported text found on box for master_pv.py; this definition is fixed here) |
| GAPD1_UP1 / GAPD1_DN1 | PV-TF-082/083 | v1.2 rewrite: open(D-1)/close(D-2) - 1 >= +1% / <= -1% |
| GAPD1_UP2 / GAPD1_DN2 | PV-TF-084/085 | same, 2% |
| GAPD1_UP4 / GAPD1_DN4 | PV-TF-086/087 | same, 4% |
| GAPD1_UP8 / GAPD1_DN8 | PV-TF-088/089 | same, 8% |
| FTD_01 | PV-TF-446 | SEC fails-to-deliver: sum of fails in the latest half-month file available before D / SEC shares outstanding (cleaned; float not available -> shares outstanding) >= 0.1% |
| FTD_05 | PV-TF-447 | same >= 0.5% |
| FTD_SPIKE | PV-TF-448 | latest available file sum / previous file sum >= 3 (previous > 0) |
| FTD_T35 | PV-TF-449 | D is 33-37 calendar days after any settlement date of the ticker in a FTD_SPIKE file available before D |
FTD availability rule: a half-month file (a = 1st-15th, b = 16th-month end) is usable from period end + 15 calendar days (SEC publishes about two weeks after). Files 2019-01..2024-12 from sec.gov (144 files).

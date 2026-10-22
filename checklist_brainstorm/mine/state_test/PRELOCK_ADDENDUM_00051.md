# PRELOCK ADDENDUM: OWN-TR-00051-C pre-registered test (for the joint lock Fri 2026-10-23 23:00 HKT)
Written 2026-10-22 ~16:35 HKT. PRELOCK_2025_26.md is already sealed (LOCKED 2026-10-22 ~13:45 HKT) and is left unchanged. This is a separate addendum. No 2025–26 data has been opened. No further tuning is allowed.

## Rule (one test only)
Signal on stock-day D, all three must hold:
1. OWN-TR-00051-C event start: answer YES (2) on D and not YES on the ticker's previous session. Ready rows only (answer 1 or 2).
2. Earnings report in the last 30 sessions, counting only reports public by D's close: a New Bot earn-calendar report on any of the ticker's sessions D-29..D-1, any timing. In code: nbx-EARN-POST1 = YES on any of sessions D-28..D, since POST1 on session t means a report on t-1. A report on D itself is excluded whatever its timing. The chunks can't tell BMO from unknown on D (TODAY-BMOUNK mixes them), and an AMC report on D isn't public by the close, so dropping all signal-day reports is the conservative reading. For the first sessions of a year, the lookback uses the prior year's EARN chunks (calendar only, no outcomes).
3. Close on D >= $5.

Trade: entry at the open of D+1, exit at the open of D+6 (5-day hold), dividends added, 30bp per side.
Control: on the same date, ready-NO (answer 1) 00051-C stock-days in the same price quintile × ATR% quintile (20-day ATR / close) × prior-1-day return decile. Bins are cut on that date's ready rows. Residual = signal return minus the control cell mean.
CI: 95%, clustered by date.
**PASS = matched win rate > 50% AND matched mean residual > 0 AND 95% CI lower bound > 0.** Judged once on 2025-01-01..2026-06-30 (to match the primary lock window). Any other result = FAIL/DROP.
Report alongside: n events, distinct dates, distinct tickers, per-year sign.

## Pins
- F4TR tags (Theme Radar): 201f39f300f39428fe44a1e7cce5af17f1bb9f52523b8efc3ee7a75c78a2fe02
- F4TR chunks 2025-26 (Theme Radar sealed set, posted 2026-10-22): **use this tar, NOT the 2025/2026 F4TR files in engine/universe/chunks/**. Tar sha256 d8ed17c3da40680831ea24e2a67d655e1e94e11e588a09550ed02c64f099b628 · [Drive](https://drive.google.com/file/d/1WAKjsY9SWnKFw61fFAuprs-7Mpy0gEWh/view). Builder f4tr_2526.py 50f93385…6c4f from James 2f90114c… / eb10c6fd…; COVER_END=2026-03-31. See v5 note.
- Earn calendar tags (New Bot nbx-EARN): 08f1507923fd2e5289bd0d427c737168b543687306bee82f7e6fe2b80ebe42cc
- Earn calendar 2020-24 tar: 57929f30ab53586d9b9c5511a8c2898965285ff5bd8af68519c53b4b9416d3f0 (the 2025-26 chunks must come from the same builder; record their sha before scoring)
- Six-bucket map: engine/universe/six_bucket_map.csv f10a31036aa158d43ac27ed83d895091adac43ab9ae9211a2705ebfe63b6d382
- Scorer: state_test/prelock/prelock_00051_earn30_px5.py 885da90bb010579ce9d8c3dba6f93864539bae56c8dba4b32cb80c9adb1c49ac (v5 2026-10-22 ~17:10 HKT: sealed F4TR path + sha checks + early-run guards; no rule change. Prior v2 sha 24d417c8b0875aab41db51a994f3d6dc11df191ac037aedccff1382c99f4afef)
  (derived from state_test/f4tr/o51b.py d08fd4f5cc80427cbf7724d120790f436afb98f6daf560e5ed8dee99fb6441bb)
- Chunks (2020-24 dry run): engine/universe/chunks/{y}__F4TR__<sector>.parquet, {y}__EARN__<sector>.parquet (2-bit packed: 0 NR, 1 NO, 2 YES). For 2025-26 F4TR: sealed tar only (above).

## Running it on 2025-26 (only changes allowed)
Set PRELOCK_YEARS=2025,2026. Point the price file and the multi-horizon return file (same build as state_test/multi_h_rets.py / ret_nbv2.py) at 2025-26 data: in the price read, change the date filter to start 2024-11-01 (for ATR and prior-day warm-up) and end before 2026-07-01. Nothing else may change: rule, bins, fees and pass bar stay as written.

## Training basis (2020–24, already burned; not a pass)
Closest checks that were looked at: 00051-C 5d with report in last 30 sessions, all events: +1.64% [+0.81, +2.46], win 56.3%, n 455. Close >= $5, all events: +1.14%, win 54.5%. The exact three-way combination was NOT scored on 2020–24. It was chosen from a 96-trial family, so the selection bias is known.

## v2 note (2026-10-22 ~16:45 HKT, before any 2025-26 read)
The v1 script and stress check (k) used a rolling 30 sessions of (TODAY-BMOUNK or POST1). That counted BMO/unknown reports on the signal day, and AMC reports on D-30 through POST1 on D-29. I checked the 2020-24 event-start counts only, with no returns scored: (k)-style flag 457, v2 flag 448. The 9 dropped are 5 signal-day reports and 4 D-30 reports; none were added. Under the locked rule with close >= $5: 424 -> 416. Only the lookback definition changed. Rule, bins, fees and pass bar are unchanged.

## v3 note (2026-10-22 16:34 HKT)
2025-26 earn manifest sha256 ee6e836aca7df3601c50f58d9483425f2889bd54360387cf5e67b976b075915d; Drive tar https://drive.google.com/file/d/15whNbyvIE8Q_3QV_B92EuyadbRnEcP-N/view (not downloaded or opened). Earn tags unchanged: 08f1507923fd2e5289bd0d427c737168b543687306bee82f7e6fe2b80ebe42cc. Scorer unchanged: 24d417c8b0875aab41db51a994f3d6dc11df191ac037aedccff1382c99f4afef.

## v4 note (2026-10-22 16:38 HKT, Manager decision; no 2025-26 data opened)
The judging window is cut to **signal dates 2025-01-01..2026-03-31**. This replaces 2025-01-01..2026-06-30 in the Pass line and in the run instructions above. Reason: 2026Q2 DERA is not published, Apr-Jun 2026 F4TR is NR, and there is no substitute source. Exit prices for 5d holds may run into April 2026, so the price and return data must extend through at least 2026-04-10 (the price-file end filter is "before 2026-07-01" or any later date that covers those exits). Signals dated after 2026-03-31 must be excluded; with NR they produce no ready rows anyway. The scorer has no hard-coded 2026-06-30 end, so it is UNCHANGED (sha 24d417c8b0875aab41db51a994f3d6dc11df191ac037aedccff1382c99f4afef).

## v5 note (2026-10-22 ~17:10 HKT, Manager decision; no 2025-26 data opened)
Pin Theme Radar's sealed F4TR 2025-26 chunks. **Use this tar only, NOT the 2025/2026 F4TR files already in engine/universe/chunks/ (those are older builds).** No contents were extracted or opened; tar sha verified only.
- Tar f4tr_chunks_2025_26.tar sha256: d8ed17c3da40680831ea24e2a67d655e1e94e11e588a09550ed02c64f099b628 · [Drive](https://drive.google.com/file/d/1WAKjsY9SWnKFw61fFAuprs-7Mpy0gEWh/view). Downloaded read-only to /workspace/data/f4tr/sealed_2025_26/ (sha verified; NOT extracted).
- Builder f4tr_2526.py sha 50f93385…6c4f, built from James's Form4 files 2f90114c… and eb10c6fd… (both fingerprints checked by Theme Radar). Tags unchanged: 201f39f300f39428fe44a1e7cce5af17f1bb9f52523b8efc3ee7a75c78a2fe02. COVER_END=2026-03-31 (everything after is NR).
- Scorer v5 (sealed F4TR path + sha checks + early-run guards; no rule change): see Pins. For 2025-26 it refuses an F4TRDIR override, checks the tar sha, extracts to sealed_2025_26/extracted/ only after the Fri 2026-10-23 23:00 HKT lock, then reads F4TR from that folder. Any mismatch = hard fail. EARN / JA paths unchanged from prior pins. Price window auto-applies the documented sealed change (warm-up 2024-11-01, end before 2026-07-01).

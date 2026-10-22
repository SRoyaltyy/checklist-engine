# Six-question (+7) bucket map — LOCKED 2026-10-22 HKT, before any bucket results were viewed
Built only from the existing locked tag files (meaning + lens + indicator name). No returns, labels or 2025–26 files were read. grok_tags.csv untouched (sha256 505f452c…8ad7). Survivors-only universe. Builder: build_six_bucket_map.py.

## The questions in plain words
1. **trend_continue**: is the trend likely to keep going? Bullish YESes from trend lenses: streak, cross, change since last, rank vs market/sector, timeframe, relative change, and bullish divergence.
2. **reversal_weighted**: are reversal signs strong enough to flip the call? Every loud_bearish YES, plus the live asterisk count (`b2_ctx_opp`: contrary context votes worked out at count time, never tagged).
3. **extreme_over_under**: is the stock extremely stretched? Bullish YESes from position, threshold, percentile and extreme lenses. That includes Theme Radar's extreme vs own history, fixed threshold and own 20/60/252-day range rows (rule b).
4. **momentum_confluence**: is momentum running out? Every quiet_warning YES: divergence, fade, volume dry-up, failed breakout. The FRESH qw_fresh and qw_jump_z columns read this bucket.
5. **extreme_outliers**: are there outliers that challenge the read? Bullish YESes from outlier lenses: Theme Radar's 4 outlier-candle lenses, rare vs own record, James's Outlier location/gap/follow-up, and New Bot's outlier lens.
6. **assumption_hold**: derived, not tagged. Inputs are b1 (lean) and b2, b4 and b5. Strong b1 lean plus a b4 jump (or b2/b5 lit) means lean toward "what goes up must come down". Strong b1 with no spike means the rally assumption stands. The locked −0.29% spike test is the first instance.
7. **squeeze_takeprofit**: secondary flag only and never a primary bucket. Covers indicators matching MFI/money flow, short volume, Reg SHO/SSR, options, IV or squeeze, plus every FINRA and options row.

## Assignment rules, in this order (the room's final rules)
- (a) Meaning wins over lens: quiet_warning → 4, loud_bearish → 2.
- (f) context/neutral → no bucket. An asterisk row is treated as context, the same way counts_v2 treats it. It reaches bucket 2 only through the live ctx_opp count.
- New Bot's 36 excluded inference rows ($1 compliance risk/regained, IPO age) → excluded.
- Bullish rows: outlier / rare-vs-own-record lens → 5; else extreme / percentile / position / quartile / decile / threshold / level / range lens → 3; else → 1.
- (d) Each row has exactly one primary bucket. b7 is a separate yes/blank column.

## Pending / not in engine
- FINRA short-volume (New Bot, NBX chunks): mapped and counted. **FINRA short interest itself is pending under New Bot. It has no history in the engine.**
- Grok options/IV (6 GK-OPX rows): mapped, with counts pending the DoltHub IV build. The fuller chain set is not tagged yet.
- New Bot's 650 rows: mapped. Counts exist in COUNTS2_NB.

## Counts files (2020–24 only; 2025–26 deliberately unbuilt)
chunks/{y}__BUCKETS7_{STK,TR,NB,NBX}__{sector}.parquet: ticker, date, b{1,2,3,4,5,7}_{yes,ready,frac}, b2_ctx_opp. Each one is the sum of that COUNTS2 file's stk group columns. Every (source, lens, meaning) group maps to exactly one bucket (0 ambiguous groups, 0 unmapped). Files are kept separate per source, so add them across STK+TR+NB+NBX on (ticker, date) if you need one total. Builder: bucket_counts.py.


## v2 changes (2026-10-22, pre-lock, room-agreed)
- Halt in last day (nb4-PDS-NB-039-W0-EVT and its BUT twin): primary 2 (reversal), no Q7 flag.
- Reg SHO new listing (nb4-BRW-NB-056-W0-EVT and its BUT twin): primary 4, Q7 flag removed.
- Reg SHO 20-day count (nb4-BRW-NB-056-T20-CNT and its BUT twin): excluded, dropped from lock (zero inside top bullish fifth).
- Added 14 New Bot nbx-SI-* rows (source new-bot-si, counted per row from chunks/{y}__SI__<sector>), all with the Q7 flag; primary buckets by rules a-f:
  - nbx-SI-ABS-DTC-HI (loud_bearish, short-interest level): 2
  - nbx-SI-ABS-DTC-LO (bullish, short-interest level): 3
  - nbx-SI-REL-RANK-HI (loud_bearish, short-interest rank): 2
  - nbx-SI-REL-RANK-LO (bullish, short-interest rank): 1
  - nbx-SI-EXT-HI (loud_bearish, short-interest outlier): 2
  - nbx-SI-EXT-HI-BUT (bullish, short-interest outlier (BUT)): 5
  - nbx-SI-DIV-ADD-INTO-RALLY (context, short-interest divergence): none
  - nbx-SI-DIV-COVER-RALLY (quiet_warning, short-interest divergence): 4
  - nbx-SI-THR-UP20 (loud_bearish, short-interest threshold): 2
  - nbx-SI-THR-DN20 (bullish, short-interest threshold): 3
  - nbx-SI-POS-HI (loud_bearish, short-interest position 252d): 2
  - nbx-SI-POS-LO (bullish, short-interest position 252d): 3
  - nbx-SI-B7-SQZ-FUEL (context, short-interest squeeze flag): none
  - nbx-SI-B7-TP-FUEL (quiet_warning, short-interest take-profit flag): 4
- Pending, not mapped yet (await owners' tags): Taskforce PV-TFC-0921..0960, Theme Radar Short Ratio / POS-TR-F0121..F0127 (plus OWN-TR-*|1 ids in SI chunks). Their SI-chunk answers are skipped.
- v1 kept read-only as six_bucket_map_v1.csv / .md.


## v3 changes (2026-10-22, Theme Radar locked short-ratio tags before returns)
- Verified theme-radar_si_tags.csv sha256 578aec512da9ed8e7d294e971cb8b74645f2ebdb4c0eb1476a36943af4f1a167 (34 rows).
- Added 34 Theme Radar SI rows (source theme-radar-si) using Theme Radar's own primary bucket and Q7 flags from the tag file (blank primary -> none). Counted from chunks/{y}__SI__<sector> (ids may carry |N window suffix; lookup strips it).
  - OWN-TR-00793-C: primary 3, Q7 yes
  - OWN-TR-00794-BUT-C: primary none, Q7 yes
  - OWN-TR-00805-C: primary 3, Q7 yes
  - OWN-TR-00806-BUT-C: primary none, Q7 yes
  - OWN-TR-00817-C: primary 4, Q7 yes
  - OWN-TR-00818-BUT-C: primary 1, Q7 yes
  - OWN-TR-00829-C: primary 4, Q7 yes
  - OWN-TR-00830-BUT-C: primary none, Q7 yes
  - OWN-TR-00841-C: primary 4, Q7 yes
  - OWN-TR-00842-BUT-C: primary 1, Q7 yes
  - OWN-TR-00853-C: primary 2, Q7 yes
  - OWN-TR-00854-BUT-C: primary 1, Q7 yes
  - OWN-TR-00865-C: primary 4, Q7 yes
  - OWN-TR-00866-BUT-C: primary 1, Q7 yes
  - OWN-TR-00877-C: primary 1, Q7 yes
  - OWN-TR-00878-BUT-C: primary none, Q7 yes
  - OWN-TR-00889-C: primary 1, Q7 yes
  - OWN-TR-00890-BUT-C: primary none, Q7 yes
  - OWN-TR-00913-C: primary 1, Q7 yes
  - OWN-TR-00914-BUT-C: primary none, Q7 yes
  - POS-TR-F0121-C: primary 3, Q7 yes
  - POS-TR-F0121-BUT-C: primary none, Q7 yes
  - POS-TR-F0122-C: primary 3, Q7 yes
  - POS-TR-F0122-BUT-C: primary none, Q7 yes
  - POS-TR-F0123-C: primary 3, Q7 yes
  - POS-TR-F0123-BUT-C: primary none, Q7 yes
  - POS-TR-F0124-C: primary 3, Q7 yes
  - POS-TR-F0124-BUT-C: primary none, Q7 yes
  - POS-TR-F0125-C: primary 3, Q7 yes
  - POS-TR-F0125-BUT-C: primary none, Q7 yes
  - POS-TR-F0126-C: primary 3, Q7 yes
  - POS-TR-F0126-BUT-C: primary none, Q7 yes
  - POS-TR-F0127-C: primary 3, Q7 yes
  - POS-TR-F0127-BUT-C: primary none, Q7 yes
- Pending answers (tags locked, no answers yet): Theme Radar Wikipedia/attention tags (attention_tags.csv sha 5ae130fb…bdf9a, 10 rows tr-attn-*). Not in map yet — no existing map rows needed those tags. List only; do not invent map entries until answers land.
- Still pending owners' tags: Taskforce PV-TFC-0921..0960.
- v2 kept read-only as six_bucket_map_v2.csv / .md.
- New Bot correction (same v3): nbx-SI-THR-UP20 primary bucket 2 -> 4 (Q7 kept). DIV-ADD-INTO-RALLY and B7-SQZ-FUEL stay Q7-only (primary none).


## v4 changes (2026-10-22, Theme Radar Wikipedia attention tags locked before answers)
- Verified attention_tags.csv sha256 5ae130fb854880bfac91755e78771ceaf87986361cab681bb42032f0b4bbdf9a (10 rows).
- Added 10 theme-radar-attn rows using Theme Radar's own primary bucket and Q7 from the tag file (blank primary -> none). Counted from chunks/{y}__ATTN__{sector} (wide int8 columns theme-radar-attn|<id>, codes 0=NR 1=NO 2=YES).
  - tr-attn-01-SPIKE15: primary 3, Q7 no
  - tr-attn-02-SPIKE30: primary 3, Q7 no
  - tr-attn-03-SURGE3D: primary 1, Q7 no
  - tr-attn-04-RISESTREAK: primary 1, Q7 no
  - tr-attn-05-PCTL252: primary 3, Q7 no
  - tr-attn-06-FADE-PRICEUP: primary 4, Q7 no
  - tr-attn-07-FADE-POSTSPIKE: primary 4, Q7 no
  - tr-attn-08-SPIKE-PRICEDN: primary 2, Q7 no
  - tr-attn-09-DORMANT: primary none, Q7 no
  - tr-attn-10-LOUD10K: primary none, Q7 no
- Pending answers still: none for Wikipedia (now mapped). Still pending owners' tags: Taskforce PV-TFC-0921..0960.
- v3 kept read-only as six_bucket_map_v3.csv / .md (csv sha 44a9f043…f158).


## v5 changes (2026-10-22, Taskforce chart-picture / story gates for ARQT lookalike fix)
- Source of truth: FROZEN_RECIPE.md sha256 bf8a2d79001cef5476d8caa9d13a87bc3dcb1ce81ec9f9b8b5d2d4c2fa304ef6; PRELOCK_ADDENDUM_CHART_PICTURE.md sha256 9a5e6b89a529095d3953f279e001e7ff54c9ffe2d074240ff8af44fa58b93d0c; gate chart_picture_gate.py sha256 2059efb613c62fe178c5f91c6ddbc9c7d49fc6651db86e126f5cf3c9a2c774e8.
- Added 7 taskforce-chart-picture rows (source taskforce-chart-picture). HARD gates 1–6 are same-setup vetoes (any mismatch → not the same setup). Gate 7 is soft warn only and does not veto. `lower_highs10` stays continuous (not mapped; no invented cutoff).
- in_engine_counts=no for all 7 until answer chunks exist; do not invent answers.
  - cp_mid_slope_up: primary 1, Q7 no (HARD; mid_slope_up / slope20>0)
  - cp_gr_body20_ge_0p9: primary 1, Q7 no (HARD; gr_body20>=0.9)
  - cp_pctB_ge_0p12: primary 3, Q7 no (HARD; pctB>=0.12; position lens)
  - cp_dip_atr_le_4p2: primary 1, Q7 no (HARD; dip_atr<=4.2)
  - cp_days_since_h20_in_5_18: primary 1, Q7 no (HARD; 5<=days_since_h20<=18)
  - cp_dd_vs_run_ge_0p5: primary 1, Q7 no (HARD; dd_vs_run>=0.5)
  - cp_redgreen_vol10_gt_1: primary 4, Q7 no (SOFT warn; redgreen_vol10>1.0; quiet_warning → 4)
- Same-setup rule (for twin search, not for single-flag scoring): HARD answers 1–6 must match on both stock-days before any other checklist answers count.
- 2020–24 ARQT twin outcome numbers stay HINT only; 2025–26 sealed until Fri 23:00 HKT lock.
- v4 kept read-only as six_bucket_map_v4.csv / .md (csv sha f10a31036aa158d43ac27ed83d895091adac43ab9ae9211a2705ebfe63b6d382).
- This v5 csv sha256 8a9b8fbcff25f6a596f256f97514f6eeed60c0b1ea76edc5ed69d5b17460890c (row_ids aligned to Taskforce NB tag names).

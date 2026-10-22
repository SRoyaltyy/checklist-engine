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

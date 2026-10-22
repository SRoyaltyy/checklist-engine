# Theme Radar WIRE50 V1 — rules (written and committed BEFORE any result was computed)
Owner: Theme Radar. Written Fri 2026-10-23 ~02:10 HKT. 2020–24 practice data ONLY; no bar or tag dated after 2024-12-31 is read (asserted in code). 2025–26 sealed until joint lock Fri 2026-10-23 23:00 HKT.

## Rows (50)
- 34 `theme-radar-si` rows (OWN-TR-008xx/009xx, POS-TR-F012x; short ratio / days-to-cover, FINRA) from `tr_si_frame.parquet` (sha 4fe7bfcd…7a22, built from SI chunks).
- 10 `theme-radar-attn` rows (tr-attn-01..10, English Wikipedia pageviews) from `attn_frame.parquet` (sha e6895ee2…76ef, ATTN chunks).
- 6 `grok-options` rows GK-OPX-IVR-HI/LO, IVHV-HI/LO, IVCHG-UP/DN from DoltHub options IV v2 chunks (Drive README 1YIraOFciAQ70dLMu1yOi83EW_CjazLvd; tar shas bc7cb074…, 50ca946c…, ed4b9764…, c0021bb2…, 507f2260… all verified).
Signal = row answer YES (code 2). NO (1) and NOT_READY (0) are not signals.

## Timing
- SI and ATTN: answer dated D -> entry at OPEN of next session D+1 (same convention as earlier tr_si/attn scoring).
- OPT: chunk date S is already point-in-time for the 09:25 ET decision (README rule) -> entry at OPEN of S.
- Trade needs 21 bars from entry, all <= 2024-12-31.

## Exits (two, both fixed; no others tried)
- E1 = EXIT_RULE_V1 cell: take profit +20% (fill max(open,target)), no stop, else close of day 15 (day 1 = entry day).
- E2 = plain 10-day hold: close of day 10.
- Fees 30bp each way (0.6% round trip) subtracted. Win = net > 0.

## Universe / filters
- pricehist `universe_2020_survivors.parquet` (survivors only — every result is labelled SURVIVORS-ONLY; delisted names are missing).
- Buyable filter v2: every (ticker,entry date) in `drop_list_v2.csv` (sha 5a6cb756…6239) removed from cases AND from the control.
- Control = all buyable stock-days in the same universe with the same entry date and same exit; excess = trade net − control mean net on that entry date.

## Runs
- Consecutive YES days for the same ticker (no gap of a non-YES trading day in that row's frame) count as ONE trade, entered on the first YES day.

## Periods and pass bar
- Discover 2020–22, confirm 2023–24 (by entry date).
- A row×exit PASSES only if in BOTH periods: trades >= 30, win rate > 55% after fees, and mean excess > 0. Long side only.
- Reported regardless: trades, win%, mean net, median net, mean excess, per period. 100 tests (50 rows × 2 exits) added to the luck-correction count.
- Nothing here is promoted to the sealed 2025–26 check unless it passes; any pass is written into a lock-index add-only section by Manager Bot, not by this run.

# Grok options question set (DoltHub post-no-preference/options) — SURVIVORS-ONLY, 2020-2024 ONLY

**2025-26 were never pulled or read** (blind holdout for the joint lock).

## Survivor bias
- Answers exist only for tickers in the current survivor universe (New Bot 2024 sector files, 5,423 non-fund names). Delisted
  DoltHub symbols are dropped (~400/yr unmatched).
- The DoltHub repo was created **2021-04-20**. Every row dated before that is a one-day backfill: values are end-of-day quotes,
  but *which names are included* was decided in 2021, so 2020 to 2021-04 carries extra survivor bias. Treat 2020/early-2021 results with care.

## Point-in-time rule
- A row dated D (end-of-day; DoltHub commits ~02:35 ET the next day) is usable for the 09:25 ET decision of the **first trading session after D**.
- For session S we use the latest reading with D < S, i.e. always the last close before that morning's 09:25 ET.

## Gap / stale rule (Manager Bot final rule, 2026-10-22)
- 2020 to ~Oct 2024 DoltHub has Mon/Wed/Fri only (Tue/Thu missing), so Wed and Fri sessions usually have no reading from the prior close.
- lag = trading sessions since the reading first became usable. lag 0 -> fresh, `stale=0`.
- lag 1 or 2 -> last reading carried forward, `stale=1` (column `stale`, plus `lag`).
- lag > 2 or no reading -> **NOT_READY** for every question (never carried further).
- COUNTS2_OPT has both all-rows (`|yes|ready|frac`) and fresh-only (`|yes_fresh|ready_fresh|frac_fresh`) columns so spike / z-score work can exclude stale rows.

## Questions (volatility_history set; tags in engine/out/tags/options_tags.csv, priors untested)
| id | YES when |
|---|---|
| GK-OPX-IVR-HI | IV rank = (iv - iv_year_low)/(iv_year_high - iv_year_low) >= 0.80 (top 20% of own 1y range) |
| GK-OPX-IVR-LO | IV rank <= 0.20 |
| GK-OPX-IVHV-HI | iv_current/hv_current > 1.3 |
| GK-OPX-IVHV-LO | iv_current/hv_current < 0.8 |
| GK-OPX-IVCHG-UP | iv vs the ticker's previous DoltHub reading (<=7 calendar days back) >= +15% |
| GK-OPX-IVCHG-DN | same change <= -15% |
Missing fields -> NOT_READY for that question only.

## Files
- raw/vh_{y}.parquet (volatility_history only, pulled one date at a time via the SQL API; no clone)
- chunks/{y}__OPT__<sector>.parquet: ticker, date, packed (2-bit 0=NR 1=NO 2=YES, 4/byte along ids, nb_year.pack), stale, lag; .json sidecar has ids/defs
- chunks/{y}__COUNTS2_OPT__<sector>.parquet; coverage_{y}.json
- Scripts: pull_vh.py, build_opt.py, counts_opt.py, chain_feats.py (chain set; code tested on a 5-ticker sample, to be run on the cloud agent's option_chain Drive output)

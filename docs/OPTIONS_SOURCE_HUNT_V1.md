# OPTIONS_SOURCE_HUNT_V1

Box-tested 2026-10-30 HKT (James / Grok Bot). Inventory FINAL; this hunt is download/source status only. Questions still open.

## Goal fields
Market-wide put/call volume + OI (I201); single-stock chains / IV / OI / skew / max pain (I202 and related). Need 2020–present, point-in-time, live-replicable, free.

## Source table

| Source | Coverage | Dates | Fields | OI | PIT | Live-replicable | Status 2026-10-30 |
|---|---|---|---|---|---|---|---|
| CBOE daily market stats JSON | Market-wide groups: total/index/etp/equity/vix/spx | 2019-10-07 → 2026-10-28 on main (`data/cboe_putcall/`); 2026-10-29 CDN returns 403 (not published yet) | call/put/total volume, published ratio, call/put/total OI | Yes | Day D usable next session (`available_from_not_before`) | Yes (`scripts/fetch_cboe_putcall.py`) | **DOWNLOADED** on main |
| CBOE bulk CSV era | Same 6 groups | Through 2019-10-04 | volume + ratio (no OI in tidy) | No | Same | Yes (`--csv-era`) | **DOWNLOADED** on main |
| CBOE index histories CDN | VIX, VIX9D, VIX3M, VVIX, SKEW, OVX, GVZ | Through 2026-10-28/29 (series-dependent) | OHLC or close | n/a | Date D close next session | Yes (`scripts/fetch_cboe_indices.py`) | **DOWNLOADED** this run → `data/cboe_indices/` |
| DoltHub `post-no-preference/options` | `volatility_history` ~1.5k symbols/day; `option_chain` ~2.3k symbols | **2019-02-09 → 2026-10-28** (cloned) | vol_history: IV/HV levels; option_chain: bid/ask/IV (`vol`)/greeks; **no OI column in either table** | No | Snapshot dates present; PIT rules still UNVERIFIED | `dolt clone` works from box (CLI v2.6.1); SQL API still broken | **CLONED on box** `/workspace/options_moneyflow_dl/dolt/options` (8.3G). Coverage log still required before features. |
| Yahoo Finance options API | Live chain snapshot | Live only | Expiries, strikes, IV, volume, OI (when not rate-limited) | Yes (live) | Live only | HTTP 429 from box this run | **LIVE-ONLY**; cannot backfill 2020+ |
| Stooq | Equity prices historically; **no options product** | n/a | n/a | n/a | n/a | Daily CSV/zip currently JS-challenge / zip 404 from box | **N/A for options** |
| CBOE delayed single-stock quotes | Live | Live only | Delayed quotes | Live | Live | Prior fetch_tests exist for AAPL/MSFT/TSLA | **LIVE-ONLY** |
| Futubull / moomoo OpenAPI | Unknown until account test | Unknown (likely live / short history) | OI/IV/volume/greeks (vendor claim) | Likely | Unknown | Needs Cyrus account / API key — **not tested this run** (no login scraping) | **AUTH REQUIRED** — skip until 1:1 auth |
| Webull | Unknown | Unknown | Options chain fields (vendor claim) | Likely | Unknown | Practice account exists; needs sign-in — **not tested this run** | **AUTH REQUIRED** — skip until 1:1 auth |
| Finviz Elite options | Today's snapshot | Live only | Chain + OI + IV + greeks CSV | Yes | Live | Confirmed 2026-10-26: no history | **LIVE-ONLY** (already logged) |
| Paid options vendors | Full | Full | Full | Yes | Vendor | Paid | **Blocked** without Cyrus |

## Definition breaks (I201)
1. **2019-10-07:** CSV era = Cboe Options Exchange only, spx=SPX only; JSON era = all Cboe exchanges, SPX+SPXW. Do not concatenate for percentiles without an era split.
2. **Post-2022 0DTE:** SPXW same-day volume inflates total/index/SPX. Prefer **equity-only** ratio for many questions.

## What was done this run
- Confirmed put/call JSON through **2026-10-28** (1776 sessions/group); re-probed 2026-10-29 → 403 AccessDenied.
- Refreshed CBOE index CSVs into `data/cboe_indices/` (VIX last 10/28; VIX9D/VIX3M/VVIX/OVX/GVZ last 10/29).
- Added `scripts/fetch_cboe_indices.py`.
- Cloned DoltHub `post-no-preference/options`: volatility_history 1,981,258 rows / 2342 syms; option_chain 121,294,318 rows / 2333 syms; both through 2026-10-28.

## Remaining gaps
- Single-stock IV/OI history 2020–26 (I202): **no free full daily universe source proven**.
- DoltHub cloned on box (8.3G). Still need universe-overlap coverage log before any feature use; **no OI** in schema.
- Futubull/Webull history depth unknown pending auth in a 1:1 session.

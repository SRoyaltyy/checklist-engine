# OPTIONS_SOURCE_HUNT_V2 — single-stock OI focus

Gantt: **[1 Data / Options + money-flow source hunt (#165)]**

Box-tested **2026-11-01 ~10:15 HKT** (James / Grok Bot). Continues V1 (`docs/OPTIONS_SOURCE_HUNT_V1.md`). Inventory FINAL; this is download/source status only.

## Verdict (explicit)

**NO — no free, live-replicable per-stock open interest (OI) history covering 2020–present was proven from the box on this hunt.**

What *does* exist free today:

- **Market-wide** put/call OI (CBOE daily JSON on main `data/cboe_putcall/`) — already counted in V1.
- **Market-wide** OCC daily open interest aggregates (Equity/Index/Debt/Futures totals) — free CSV, **not per underlying**.
- **Live** single-stock chains with OI: CBOE delayed JSON, Nasdaq option-chain API, yfinance — **snapshot only**, no 2020–26 backfill.

DoltHub `post-no-preference/options` (coverage V6 on main): IV/greeks history for ~21% of retained names; **no OI column** (`docs/DOLT_OPTIONS_COVERAGE_V6.md`, `5f281a9`).

## Goal fields (unchanged)

Single-stock chains / IV / **OI** / skew / max pain (I202 and related). Need **2020–present**, point-in-time, live-replicable, free. Market-wide I201 already on main.

## Source table (2026-11-01 box tests)

| Source | Coverage | Dates | Fields | OI | PIT | Live-replicable free | Status 2026-11-01 |
|---|---|---|---|---|---|---|---|
| CBOE put/call market stats | Market-wide groups | 2019-10-07→2026-10-28 on main | volume + OI | Yes (market) | Day D next session | Yes | **DOWNLOADED** (V1; unchanged) |
| CBOE delayed equity options JSON | Per-symbol live chain | Live only (`timestamp` ~2026-10-31); `?date=` ignored | bid/ask/IV/greeks/**open_interest**/volume | Yes (live) | Live | Yes HTTP 200 | **LIVE-ONLY** — AAPL proof 3230 contracts, OI sum 4,679,184; SHA `docs/oi_hunt_v2_proofs/proof_cboe_delayed_AAPL_oi.json` = `83da0ce15ce0bd80dbf966b8abf30e470a8c7a31c85a7ee5d3637acb3b71cb4d` |
| Nasdaq option-chain API | Per-symbol live chain | Live; past `fromdate`/`todate` → rCode 400 "Month should be >= current month" | c_Openinterest / p_Openinterest + quote fields | Yes (live) | Live | Yes HTTP 200 | **LIVE-ONLY** — proof SHA `ceb58bbe6043f47153c2ba40a4a1290b379a9218085f04e5c6fe83b6d606942f` |
| yfinance `Ticker.option_chain` | Per-symbol live chain | Live only; no historical options method | openInterest, volume, IV | Yes (live) | Live | Yes (when Yahoo allows) | **LIVE-ONLY** — AAPL 4 near expiries sampled; proof SHA `94df7d11ac23f8f61d1bf266092d51f4bfbbe9b538e7cf83d2990bccaf46381e` |
| Yahoo v7 options HTTP | Same as yfinance backend | Live | chain | Yes | Live | HTTP **401** Invalid Crumb without cookie/crumb | **LIVE-ONLY / crumb-gated** from raw HTTP |
| OCC daily open interest CSV | **Market-wide** Equity/Index/Debt/Futures call/put totals | Month files HTTP 200 for 2020–2026 samples | Aggregate OI only | Market-wide only | Publication date | Yes | **NOT PER-STOCK** — Oct-2026 sample SHA `5eec28a0da5ef31d2e9c8abc867debdf8c5cb4585ec4cf1977c0a53a83e5f692`; URL `marketdata.theocc.com/daily-open-interest?reportDate=MM/DD/YYYY&action=download&format=csv` |
| OCC volume / OI-by-underlying guessed endpoints | Unknown | n/a | n/a | n/a | n/a | Timeout / 503 from box | **UNUSABLE** this run |
| DoltHub post-no-preference/options | ~1.6–1.7k sym/year vs retained 8439 | 2019-02-09→2026-10-28 | IV/HV + chain greeks | **No** | UNVERIFIED | `dolt clone` | **CLONED**; coverage V6 on main — **no OI** |
| Alpha Vantage `HISTORICAL_OPTIONS` | Claims EOD chains w/ `open_interest` + `date` | Docs: multi-year with `date=`; **demo** returns latest session only (IBM date=2026-10-30) | full chain + OI + IV + greeks | Yes (vendor) | Vendor | **Premium** (non-demo key → premium paywall in box test) | **PAID / not free** — not usable without Cyrus premium key |
| Polygon / Tradier / ORATS / Unusual Whales / Tiingo options | Vendor | Vendor | Often include OI | Likely | Vendor | 401 without key | **AUTH / PAID** |
| EODHD / Twelve Data options | Vendor | Vendor | Unknown | Unknown | Vendor | 403 / 404 on demo | **FAIL / AUTH** |
| HuggingFace datasets search (`options chain`, `"open interest"`) | n/a | n/a | n/a | n/a | n/a | API 200 empty `[]` | **NONE FOUND** |
| GitHub repo search `options open interest historical dataset` | n/a | n/a | n/a | n/a | n/a | API total_count 0 | **NONE FOUND** |
| Kaggle datasets HTML search | Unknown | Unknown | Unknown | Unknown | Unknown | Page 200 but JS app shell; no authenticated dataset API this run | **UNPROVEN** (no free bulk OI panel identified) |
| historicaloptiondata.com / optiondata.org / Algoseek OI / CBOE DataShop | Commercial | Commercial | Full OI panels (vendor claim) | Yes | Vendor | Marketing pages 200; samples paid | **PAID** |
| Finviz Elite options | Live snapshot | Live | OI | Yes | Live | Confirmed prior | **LIVE-ONLY** (V1) |
| Futu / moomoo / Webull | Unknown history depth | Unknown | OI likely | Likely | Unknown | Needs Cyrus 1:1 login | **AUTH REQUIRED — not tested** |

Probe log (HTTP statuses): `docs/oi_hunt_v2_proofs/oi_probe_raw.json` SHA `6622eb86443afdc3843a16410c69dc983cb1b6d933ae9a8bba19222d1e7be5a8`.

## Money-flow gaps (short recheck, not a rabbit hole)

Recheck artifact: `docs/oi_hunt_v2_proofs/moneyflow_recheck.json` SHA `7ddf433c7ea8b76b6df5787341360f4c46f4e87b627c72a783601dbdc7299611`.

| Gap | Status 2026-11-01 |
|---|---|
| FINRA daily short volume | Still live — CNMS 2026-10-29 HTTP 200 from box |
| FINRA SI mid-Oct file | `shrt20261015.csv` still **403** (unpublished or gated) |
| Large vs small order flow | **No free history** |
| Block / dark-pool prints stock-day | **No free history**; NasdaqTrader ATS page 500 this run; FINRA OTC weeklySummary API still 200 (ATS flavor only) |
| ETF fund flows bulk | ETF.com / ICI pages **403** from box; no free bulk CSV proven |

## What this run did

1. Reconfirmed Dolt V6: no OI in schema; retained overlap ~21% any-row IV.
2. Box-tested 30+ candidate OI endpoints/datasets (Yahoo, Nasdaq, CBOE delayed, OCC, AV, Polygon, HF, GitHub, Kaggle shell, paid vendors).
3. Published bounded **live** OI proofs (CBOE / Nasdaq / yfinance) with SHAs — useful for forward capture only.
4. Proved OCC "Daily Open Interest" is market-wide aggregates, redundant with CBOE put/call for per-stock needs.
5. Recorded Alpha Vantage historical options as **premium**, not a free backfill path.

## Remaining blockers (next)

1. **Per-stock OI 2020–26:** still missing. Paths left: (a) Cyrus pays a vendor (AV premium / Algoseek / HistoricalOptionData / Polygon options), (b) Cyrus 1:1 Futu/Webull auth to measure history depth, (c) explicit inventory exclusion / NOT_AVAILABLE for single-stock OI until (a)/(b).
2. Forward-only capture from CBOE delayed / Nasdaq could start a *prospective* panel but **does not** fill 2020–present.
3. Money-flow: large/small + dark-pool + ETF flows still no free history.

## Gantt honesty

Row **[1 Data / Options + money-flow source hunt (#165)]** → **~10% amber** (was ~8% after Dolt V6). Delta = hunt completeness + live OI proofs + explicit negative on free historical OI. **Not green:** no usable per-stock OI panel on main.

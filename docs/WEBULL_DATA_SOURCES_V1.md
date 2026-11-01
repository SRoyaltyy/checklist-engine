# Webull MCP data sources v1 (#165 + SEC/analyst/sector row)

Probed 2026-11-01 (HKT) using only Webull MCP **read** tools. Tickers: AAPL (large cap), SOUN (small cap), QQQ (ETF). No order, account or watchlist tools were called. "Sub" means the call failed with `MARKET_DATA_NOT_SUBSCRIBED` on the current entitlement.

## Matrix

| Family | Tool(s) | Fields returned | Earliest reachable | Per-call limits | Unique vs CE (Dolt/FINRA/SEC) | Row fit |
|---|---|---|---|---|---|---|
| Option contracts | get_option_contracts | symbol, strike, expiry, style, multiplier, exchanges, ppind. **No IV/greeks/OI** | Live chain only. `status=DELISTING` → `[]` (AAPL, SOUN) | 1000/page, 20 underlyings | No (Dolt options has chains) | #165: low |
| Option bars / snapshot / tick | get_option_bars, get_option_snapshot, get_option_tick | Sub (US_OPTION) | n/a. Even with a sub, no expired contracts, so no backfill | bars 1200, ticks 1200, 20 symbols | Would give forward IV/OI only if subscribed | #165: blocked |
| Capital flow by order size | get_stock_capital_flow | date, large/medium/small in/out ($) | **5 trading days** (count 1..5, no date params) | 1 symbol | **Yes**, not in CE | #165: forward-collect only |
| Footprint (large-order intraday) | get_stock_footprint | Sub (FOOTPRINT) | n/a | 1200 bars, 20 symbols | Would be unique | #165: blocked |
| NOII imbalance | get_stock_noii_snapshot / _bars | paired/imbalance shares, side, ref/near/far price | Snapshot = last auction only. Bars returned `[]` on a weekend | 1 symbol | Yes (Nasdaq auction) | #165: forward-collect, minor |
| Stock tick / quotes | get_stock_tick, get_stock_quotes | ticks: time, price, vol, side "N". Quotes: L1 (empty off-hours) | Ticks: most recent ≤1000 | depth 1 on L1 | No (side unlabeled) | low |
| Stock bars | get_stock_bars(_single) | OHLCV | **Daily capped at 1825 days** (~2021-11) | 1200 bars | No (CE has longer) | none |
| Analyst rating | get_analyst_rating | counts strong_buy/buy/hold/under/sell, as-of date | Current only | 1 symbol | Partly (CE lacks consensus counts) | SEC/analyst: forward snapshot |
| Analyst target | get_analyst_target_price | mean/median/low/high, as-of | Current only | 1 symbol | Partly | same |
| Forecast EPS | get_stock_forecast_eps | per-quarter est vs actual | ~5 quarters (2025Q4..2026Q4 for AAPL) | fixed | Some value (est/actual surprise history), shallow | analyst: low-medium |
| Earnings calendar | get_stock_earnings_calendar | date, eps/rev est+actual | Last + next quarter | fixed | Marginal | calendar |
| Financial alert | get_financial_alert | next report date, eps/rev est vs LY | Current | fixed | Marginal | low |
| Financial indicators | get_financial_indicators (+ income/BS/CF) | ROE, ROA, net margin, EPS, BVPS, OCF/share, debt/assets | **20 quarters max** (2021Q4 for AAPL with count=100) | 20 periods | No (SEC companyfacts is deeper) | SEC: fallback for CIK-less names |
| Industry comparison | get_stock_industry_comparison | peer rank by EPS_TTM (etc.) | Current | fixed | Yes (Webull industry taxonomy) | sector: current mapping |
| Market sectors | get_market_sectors(_detail) | sector id/name, adv/decl/flat, change, mcap, constituents | Current. Periods D1/D5/MO1/MO3 | paged | Taxonomy is useful, no history | sector: map only |
| Rankings | get_most_active, get_gainers_losers, get_52_week_high_low, get_high_dividend | OHLC, chg, turnover rate, mcap | Current only | paged | No (derivable from bars) | none |
| SEC filings | get_stock_filings | title, EDGAR URL, publish_date | **~6 most recent** (SOUN back to 2025-05) | fixed | No (CE has EDGAR archives) | SEC: none (but carries CIK in title) |
| Fund holdings | get_fund_holdings (+ allocation, NAV, dividends) | holding symbol, pct, pct change, update_time | Current. NAV has a last_date cursor | fixed | Partly (13F gap while relay 403s) | sector/ETF: current only |

## Verdicts
1. **Per-stock OI history 2020-26 via Webull: NO.** Expired contracts aren't listed, option market data needs a US_OPTION subscription, and no endpoint we could reach returns OI.
2. **Money flow:** the order-size capital flow is unique but only goes 5 days back. It's worth a cheap daily cron (≈8.4k names × 1 call) to build history going forward. Footprint needs a sub.
3. **SEC/analyst/sector:** history is shallow (5–20 periods) and there are no point-in-time snapshots. The useful parts are (a) the **CIK embedded in filing titles**, which could fill some of the 4,419 CIK-less names, (b) the Webull sector/industry taxonomy, and (c) consensus rating/target counts that we'd need to snapshot forward.
4. The disk impact of forward crons is small (KB per name per day).

## Proposed next
- Add a forward-collector cron for capital_flow, analyst rating/target and NOII snapshot (opt-in).
- Probe get_stock_filings CIK extraction for the CIK-less names.
- Keep looking for OI history elsewhere: OCC/Cboe daily OI, polygon flat files, Futu OpenD, ORATS.

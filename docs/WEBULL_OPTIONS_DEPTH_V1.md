# Webull options / money-flow depth probe v1 (#165)

Probed 2026-11-01 (HKT) using the Webull MCP read-only tools. Tickers: AAPL (large cap) and SOUN (small cap). No orders were placed, and no account or watchlist tools were called.

| Tool | Result |
|---|---|
| get_option_contracts (LISTING) | OK. Contract metadata only (strike, expiry, exchanges). No OI or volume fields. |
| get_option_contracts (status=DELISTING) | `[]` for AAPL and SOUN. **Expired contracts can't be queried.** |
| get_option_bars (D, count 1200) | `MARKET_DATA_NOT_SUBSCRIBED: subscribe to US_OPTION` |
| get_option_snapshot | `MARKET_DATA_NOT_SUBSCRIBED: US_OPTION` |
| get_option_tick | `MARKET_DATA_NOT_SUBSCRIBED: US_OPTION` |
| get_stock_capital_flow | OK for AAPL and SOUN. Daily large/medium/small in/out. **count is capped at 1..5 and there are no date params**, so only the last 5 trading days (2026-10-26..10-30). |
| get_stock_footprint | `MARKET_DATA_NOT_SUBSCRIBED: FOOTPRINT` |

Schema limits even with a subscription: bars return at most 1200 per call (start/end_time params exist). Contracts are listing-only, and the API offers no way to reach expired series.

## Verdict
Webull **can't** provide per-stock open-interest history for 2020-26:
- It has no expired-contract universe.
- Option bars, snapshots and ticks are paywalled (US_OPTION subscription), and OI shows up in none of the responses we could get.
- At best, a subscription would give current-chain data going forward.

Capital flow is a rolling 5-day window. It's only useful as a forward-collected daily snapshot (cron) and can't be backfilled.

## Next
- Optional: start a forward cron for get_stock_capital_flow over the universe, 5-day overlap, cheap.
- For OI history, look at other sources: Futu OpenD, ORATS/CBOE DataShop, polygon options flat files, OCC/Cboe daily OI.

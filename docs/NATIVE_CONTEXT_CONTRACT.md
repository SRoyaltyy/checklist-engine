# Native shared context contract

This is Phase 1 implementation, not a completed world-coverage claim.

`world_context_native.py` builds shared ALFRED/CBOE, ETF and dated membership
inputs on the exact stock candle boundaries: each integer session size 1–21,
plus separate calendar months. `available_from` may equal buy day D; the source
candle end must be strictly earlier. Date-only macro vintages must be < D.

Native blocks can stay factored on disk. `attach_context` materializes requested
columns on a stock's actual query dates; it does not create a daily copy of every
benchmark indicator for every stock just to count coverage. A later stock-day
coverage proof must use the complete accepted stock-day denominator.

## Implemented behavior

- `native_intervals`: the same fixed calendar boundaries as completed stock
  candles. Partial final months and incomplete last session buckets are omitted.
- `fred_native`: first release and latest-known values from the ALFRED timeline;
  20/60 changes count native candles. Monthly observations stay stepwise known
  levels; no interpolation is performed.
- `index_native`: actual complete-interval OHLC where the source proves OHLC.
  Close-only VVIX/OVX/GVZ remain close-only. Any missing or nonfinite required
  session leaves the whole interval unavailable. Missing intervals are retained
  so an as-of attachment cannot silently replace them with older values.
- `price_native`: actual ETF OHLCV, native returns and 50/200 average distances,
  with an optional full-indicator builder. Partial IPO/halt buckets stay blank.
- `membership_at` and `attach_mapped_context`: sector/industry assignment from
  a knowledge date strictly < D; return the actual assignment lineage separately
  from numeric features. Unknown classifications stay blank. Current labels
  cannot be backfilled into earlier years.
- `relative_native`: registered log relative strength, native relative returns,
  Mansfield, beta and correlation using identical stock/benchmark intervals.
  Missing benchmark buckets are never forward-filled.

## Existing source audit

Checked before requesting new source data:

- `SRoyaltyy/fullscan/src/industry_etf.py`, blob
  `5005779387165771692311428aa1bae5d9092bcc`, contains an explicitly incomplete
  Finviz-industry proxy map intended for backtest grading. Some proxies are
  commodity or sector funds rather than pure industry funds. It does not prove
  a complete, historically dated stock-to-industry assignment.
- `SRoyaltyy/fullscan/src/industry_map.py`, blob
  `8d347dbd3c13ee4fad9584d089eb335cc322bf6b`, reads dated Finviz exports. Its
  fallback to the first file when no file predates the query would leak a future
  classification. That fallback is not used by this implementation.
- The fullscan export listing contains `finviz_2026-04-26.csv` and later 2026
  files; the theme-radar universe listing starts in August 2026. Inspected file
  listings do not establish 2020–2025 membership coverage. CSV contents and
  complete historical classification lineage have not yet been validated.

The industry/sector source boxes remain open. A current map or a date in a
filename alone is not evidence that a classification was known in 2020.

## Runner proof

`ci.shared_context_build` consumes only the already released, hash-bound sources:

- `fred-structured-v3-40266650669-1`
- `phase1-gap-fred-v2-40307954973-1`
- `phase1-gap-cboe-v1-40307220071-1`
- the market calendar from `native-price-inputs-v1-40336250454-1`

It verifies archive and member hashes, builds every timeframe, independently
rebuilds all columns after cuts at 2023-01-03 and 2025-01-02, then publishes native
parts, checksums, shared-session coverage and source receipts. Shared-session
coverage is explicitly not full stock-day world coverage. Existing missing
ALFRED vintage history remains unavailable; revised current values are not
substituted.

Local validation: **61 tests passed** across native contexts, source-bound
archive readers, FRED timelines and bar statistics. A stale FRED test stub was
updated to accept the existing timeframe argument. No local packages installed.
The full-world, stock-context attachment, historical tradeability and scoring
gates remain closed until their complete runner evidence exists.

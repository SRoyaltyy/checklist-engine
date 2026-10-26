# Full frozen-universe source acquisition v3

Scope: every ticker in the checksummed `data-2020-24-v1/universe_2020_survivors_le2024.parquet` asset (8,727 measured universe tickers; the separate frozen bar file contains 5,234). No automatic ticker exclusions. This is source acquisition, not a world-state or scoring pass.

The initial run is pinned through 2026-10-23, the latest completed US session when this version was prepared. Every shard uses the same New York end-date boundary. The original frozen bars are preserved. Vendor quote prices remain explicitly unverified as historical nominal prices; no market-cap or nominal-price cutoff is approved by these data.

Sixteen deterministic shards run with at most eight concurrent runners. Each fifty attempted tickers produces a release checkpoint with original parquet bytes, per-member SHA-256 and archive SHA-256. Files are never overwritten on a release. Failed jobs also upload short-retention recovery data. Share-class dots are converted to Yahoo's dash syntax while the canonical ticker is preserved and checked against the provider's reported symbol.

`PRICE_SOURCE_COVERAGE.csv` contains every requested ticker, including errors, unattempted names, stale last sessions and incomplete OHLCV. The summary fails any unresolved source coverage. A green source-acquisition summary would still not approve full world coverage, question quality, raw-price basis, leakage or scanner probabilities.

The full-universe build will consume only fingerprint-verified source archives and will reconcile each ticker against the frozen history. Missing sources or unverified identity changes remain explicit gaps.

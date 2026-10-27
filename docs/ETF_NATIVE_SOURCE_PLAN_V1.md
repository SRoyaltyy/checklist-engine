# ETF native baseline source

James's 12:20 instruction requests ETF baselines alongside native recovery. The existing shared-context release contains ALFRED/CBOE series only. This acquisition supplies ETF price baselines separately without another vendor fetch or a competing stock-price rebuild.

`ci/ETF_CONTEXT_SOURCE_REQUEST.json` pins the frozen input manifest SHA-256 and original compact prefix. All 25 requested market, sector, bond, currency, commodity and volatility ETF symbols exist in the accepted input manifest. Complete parts from compact shards 13–15 are usable before the whole shards complete. The same compact checkpoint validator rejects incomplete or incompatible manifests; archives and individual bar members must match their recorded hashes.

The runner downloads one compact archive at a time and reads only target bar members. It aggregates true OHLCV candles on the frozen exchange calendar for 1–21 sessions and calendar month. Native returns use 1/5/20 candles, and trend distances use 50/200 candles. Pre-IPO, missing-session and insufficient-history values remain blank. Every output column is rebuilt with future data cut off at 2023-01-03 and 2025-01-02, requiring exact equality of all available rows.

The immutable output has 22 Parquets, per-column shared-session coverage and source/member provenance. A missing target is recorded and causes failure after preserving any actual source evidence. No request-only release is published. Prices remain in the frozen reference units: nominal historical eligibility and market caps are not proven. The full indicator grid, stock-day joins/coverage, rolling peers and final world gates remain separate requirements. No checklist box is claimed from this baseline acquisition alone.

Validation: 80 local ETF/context/compact tests passed, including all-timeframe truncation, IPO/warmup blanks, incorrect member identity/dates, and missing targets in a partial compact shard. The workflow runs the same suite on Linux before acquisition. No local onboarding or dependency installation was performed.

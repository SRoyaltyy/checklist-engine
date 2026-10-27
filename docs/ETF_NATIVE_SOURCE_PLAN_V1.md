# ETF native baseline source

James's 12:20 instruction requests ETF baselines alongside native recovery. The existing shared-context release contains ALFRED/CBOE series only. This acquisition supplies ETF price baselines separately without another vendor fetch or a competing stock-price rebuild.

`ci/ETF_CONTEXT_SOURCE_REQUEST.json` pins the frozen input manifest SHA-256 and original compact prefix. All 25 requested market, sector, bond, currency, commodity and volatility ETF symbols exist in the accepted input manifest. Complete parts from compact shards 13–15 are usable before the whole shards complete. The same compact checkpoint validator rejects incomplete or incompatible manifests; archives and individual bar members must match their recorded hashes.

The runner downloads one compact archive at a time and reads only target bar members. It aggregates true OHLCV candles on the frozen exchange calendar for 1–21 sessions and calendar month. Native returns use 1/5/20 candles, and trend distances use 50/200 candles. Pre-IPO, missing-session and insufficient-history values remain blank. Every output column is rebuilt with future data cut off at 2023-01-03 and 2025-01-02, requiring exact equality of all available rows.

The immutable output has 22 Parquets, per-column shared-session coverage and source/member provenance. A missing target is recorded and causes failure after preserving any actual source evidence. No request-only release is published. Prices remain in the frozen reference units: nominal historical eligibility and market caps are not proven. The full indicator grid, stock-day joins/coverage, rolling peers and final world gates remain separate requirements. No checklist box is claimed from this baseline acquisition alone.

Validation: 80 local ETF/context/compact tests passed, including all-timeframe truncation, IPO/warmup blanks, incorrect member identity/dates, and missing targets in a partial compact shard. The workflow runs the same suite on Linux before acquisition. No local onboarding or dependency installation was performed.

## Actual acquisition and missing-XLI repair

Run 40478361979 published `etf-native-context-v1-40478361979-1` with 24 ETFs, 22 Parquets, 240 baseline columns per timeframe, and 44 exact prefix checks with zero mismatches. It then failed because XLI is not present in compact shard 14's durable parts. Coverage SHA-256 is `48fbfbc645d92105014b494f5e46c06902f36ce43038e1753e07486649460b46`; the release explicitly records the missing symbol and is preserved unchanged.

Request version 2 permits only XLI to use a missing-ETF fallback. It reads the prepared frozen shard and the already-published supplemental archive, verifies their hashes, and uses the exact same frozen reconciliation (60 overlap rows, original acceptance thresholds, unchanged old prices, complete latest session). It requires the original recipe fingerprint and accepted ETF classification. This does not launch another native-feature or compact-price matrix. The replacement release still requires all requested ETFs, all 22 timeframes and both complete prefix checks. New tests cover compatible reference-unit reconciliation, stale/incompatible sources and a changed-recipe rejection; the local suite now passes 82 tests.

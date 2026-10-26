# World-state evidence — provisional

The full world-state gate is FAIL. No Step A rerun, shortlist, combine or final probability result is ready.

Build source: [d8fa592](https://github.com/SRoyaltyy/checklist-engine/commit/d8fa592779e229bfdf779914aac2f7537d6d81f8). Runner: [40209615520](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40209615520).

The immutable [smoke release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/world-smoke-v2-40209615520-1) contains WORLD_COVERAGE.csv, WORLD_COVERAGE_SUMMARY.json, WORLD_COLUMN_MEASUREMENTS.json, WORLD_LEAK.json, and the parquet/manifest. These reports are measured over SIX stocks, not the full catalog.

Verified: 7,058 stock-day rows; 10,188 columns including ticker/date; every candle size 1–21 sessions plus calendar-month output; 61 candle patterns. Runner regressions: 24 passed. Full produced-column leak verification: 10,186 features, 115 cutoff points, 1,144,110 comparisons, zero mismatches. This does not certify absent sources or the unfinished v3 question tree. An earlier run found and then fixed 11 Kagi seed lookaheads.

Coverage: 11,638 item×timeframe rows, WIRED 1,367 / PENDING 8,269 / BLOCKED_SECRET 22 / EXCLUDED_LIVE_ONLY 22 / EXCLUDED_FREE_TEXT 1,716 / NOT_AVAILABLE_FREE 242. Some exclusions still lack tested-source proof. These are row counts, not distinct item counts. Snapshot price inputs end 2024-12-31.

Supplemental daily prices were independently fetched through 2026-10-23, including 454 sessions per pilot stock in 2025–2026. They are not yet integrated or reconciled. Vendor quote fields are not asserted to be historical nominal prices.

Companyfacts returns HTTP 403 on runners. Form 4 filing counts, 13F filing mentions, analyst-action counts and news counts do not satisfy all required trade/holdings/price-target/tone semantics. These remain blockers. The v3 generated tree and empirical 200-stock quality report are incomplete.


## Latest completed six-stock validation — 2026-10-26

Run [40213446937](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40213446937), main-based integration branch in draft [PR #8](https://github.com/SRoyaltyy/checklist-engine/pull/8): 36 tests passed. Snapshot: 9,782 rows, 10,408 columns (ticker/date included), data through 2026-10-23; candle sizes 1–21 trading sessions plus calendar month. FRED fetch passed with 38,038 observations across five series; all 20 stock/ETF price downloads passed.

Leak check of supplied features passed: 10,406 unique columns, 163 truncation cut points, 1,657,634 comparisons, zero mismatches. This is six-stock supplied-data proof, not a full-universe or v3-question leak pass.

Coverage gate FAILED: 11,638 item/timeframe rows; 1,408 WIRED, 8,250 PENDING, 22 EXCLUDED_LIVE_ONLY, 1,716 EXCLUDED_FREE_TEXT, 242 NOT_AVAILABLE_FREE. SEC companyfacts remains HTTP 403 after retries. The overall workflow FAILED. Complete reports and snapshot are in [world-smoke-v2-40213446937-1](https://github.com/SRoyaltyy/checklist-engine/releases/tag/world-smoke-v2-40213446937-1). Source inputs and checksums are preserved separately in [world-inputs-v2-40212948878](https://github.com/SRoyaltyy/checklist-engine/releases/tag/world-inputs-v2-40212948878).

James's PROJECT_CHECKLIST remains 0/224 checked. Full-universe world coverage, the generated v3 question CSV, 200-stock question-quality proof and full leak proof remain unfinished. Step A, exit grid, shortlist, combination search, confirmation and probability publication have not started under the new gates.

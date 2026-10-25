# World-state evidence — provisional

The full world-state gate is FAIL. No Step A rerun, shortlist, combine or final probability result is ready.

Build source: [d8fa592](https://github.com/SRoyaltyy/checklist-engine/commit/d8fa592779e229bfdf779914aac2f7537d6d81f8). Runner: [40209615520](https://github.com/SRoyaltyy/checklist-engine/actions/runs/40209615520).

The immutable [smoke release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/world-smoke-v2-40209615520-1) contains WORLD_COVERAGE.csv, WORLD_COVERAGE_SUMMARY.json, WORLD_COLUMN_MEASUREMENTS.json, WORLD_LEAK.json, and the parquet/manifest. These reports are measured over SIX stocks, not the full catalog.

Verified: 7,058 stock-day rows; 10,188 columns including ticker/date; every candle size 1–21 sessions plus calendar-month output; 61 candle patterns. Runner regressions: 24 passed. Full produced-column leak verification: 10,186 features, 115 cutoff points, 1,144,110 comparisons, zero mismatches. This does not certify absent sources or the unfinished v3 question tree. An earlier run found and then fixed 11 Kagi seed lookaheads.

Coverage: 11,638 item×timeframe rows, WIRED 1,367 / PENDING 8,269 / BLOCKED_SECRET 22 / EXCLUDED_LIVE_ONLY 22 / EXCLUDED_FREE_TEXT 1,716 / NOT_AVAILABLE_FREE 242. Some exclusions still lack tested-source proof. These are row counts, not distinct item counts. Snapshot price inputs end 2024-12-31.

Supplemental daily prices were independently fetched through 2026-10-23, including 454 sessions per pilot stock in 2025–2026. They are not yet integrated or reconciled. Vendor quote fields are not asserted to be historical nominal prices.

Companyfacts returns HTTP 403 on runners. Form 4 filing counts, 13F filing mentions, analyst-action counts and news counts do not satisfy all required trade/holdings/price-target/tone semantics. These remain blockers. The v3 generated tree and empirical 200-stock quality report are incomplete.

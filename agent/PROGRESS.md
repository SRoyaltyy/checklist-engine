# Progress - SEC and Options download pipelines

Lane owner: Venice. Branch: venice/sec-options-pipelines. Never push main.

## Where this lane sits

Four independent bulk sources for SEC filings and listed-options data, each behind its own
workflow, all feeding one retained identity map. Nothing merges to main without instruction.

## Items

| # | Item | State | Evidence |
|---|------|-------|----------|
| 1 | SEC tickers workflow | not started | - |
| 2 | Bulk submissions pipeline | not started | - |
| 3 | Options chain source | not started | - |
| 4 | Retained identity map wiring | not started | - |
| 5 | Source monitor and drift check | not started | - |

## Reading order on wake

1. docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md
2. docs/SEC_RETAINED_IDENTITY_MAP_V1.md (companion .md, never the 5.3MB json)
3. docs/CBOE_SOURCE_LOCATIONS_V1.json
4. docs/NO_AI_DATA_PIPELINES_V1.md

## Rules

- One item per wake. Tick the row and add evidence before stopping.
- METHODOLOGY.md is 587KB: grep it, never read it whole.
- No markers in committed files. PR to main only.

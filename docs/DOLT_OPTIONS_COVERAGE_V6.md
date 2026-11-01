# Dolt options coverage V6

Gantt: **[1 Data / Options + money-flow source hunt (#165)]**

Status: `SOURCE_COVERAGE_EVALUATION_ONLY` (not a world/PIT/scoring gate).

## Database

- Box path: `/workspace/options_moneyflow_dl/dolt/options` (~8.3G)
- Remote: `https://doltremoteapi.dolthub.com/post-no-preference/options`
- Head: `v0pv41betm39v1duuma05gjqjbtn4b7t` — volatility_history 2026-10-28 update
- Tables: `volatility_history`, `option_chain`
- Span: 2019-02-09 → 2026-10-28
- Rows: VH **1,981,258** / **2,342** symbols; chain **121,294,318** / **2,333** symbols

## Open interest

**No OI column** in either table. Chain columns are date, act_symbol, expiration, strike, call_put, bid, ask, vol (IV), delta, gamma, theta, vega, rho. Single-stock OI history remains missing.

## Retained universe

**8,439** names = `ACCEPTED_PRICE_INVENTORY_V6.csv` (8,447) minus `REPLAY_QUARANTINE_V1.csv` (ABX, AMTD, CATO, FEIM, HHS, JHI, NKTR, OCGN). Matches composed price receipt completed=8439 (run `41221028803`).

## Dense-enough rule (explicit)

Window: calendar years **2020–2026**.

- **volatility_history:** dense if ≥**100** session-rows in at least **4** of those 7 years.
- **option_chain:** dense if present (any row) in at least **4** of those 7 years.

## Overlap vs retained 8,439

| Metric | Count | % of 8439 |
|---|---:|---:|
| VH any row | 1808 | 21.4243% |
| option_chain any row | 1801 | 21.3414% |
| both tables | 1801 | 21.3414% |
| VH dense-enough | 1308 | 15.4995% |
| chain dense-enough | 1395 | 16.5304% |

### Per-year retained presence %

| Year | VH % | chain % | VH matched | chain matched |
|---:|---:|---:|---:|---:|
| 2020 | 15.5587 | 15.5587 | 1313 | 1313 |
| 2021 | 14.907 | 14.907 | 1258 | 1258 |
| 2022 | 15.5232 | 15.5232 | 1310 | 1310 |
| 2023 | 16.6844 | 16.6015 | 1408 | 1401 |
| 2024 | 17.1347 | 17.0399 | 1446 | 1438 |
| 2025 | 17.5021 | 17.4191 | 1477 | 1470 |
| 2026 | 18.4264 | 18.3434 | 1555 | 1548 |

## PIT

**UNVERIFIED.** No as-of / revision audit on this clone. Not safe to treat as PIT for answers or mining.

## Gaps / blockers

- Single-stock **OI history** still missing (schema has none).
- Source symbol set ~1.6k–1.7k/year → retained presence maxes ~**18%** in 2026.
- Order-flow / dark-pool / ETF flows not in this DB.
- CBOE index histories from merged #165 are separate from this Dolt clone.

Machine artifact: `docs/DOLT_OPTIONS_COVERAGE_V6.json`.

# DATA_SOURCES - where each world-snapshot item gets its data

Built 2026-10-25 HKT from: world_snapshot_dictionary.csv (233 items), the box fetch tests (checklist_brainstorm/fetch_tests/fetch_test_report.csv, 98 checks: 74 pass, 22 fail, 1 not tested), fetch_proof files (out_v3e, fetch_tests), data/ folders, and the live repo releases (data-2020-24-v1 has the 2020-24 inputs; world-2020-26-v1 exists but has NO assets yet; grid/combine releases hold results).

Words: **proven** = we actually pulled real rows in a test. **failed** = we tried and it broke. **untested** = nobody has pulled it yet. **in repo** = a file in a GitHub release or folder of SRoyaltyy/checklist-engine. Full per-item detail is in DATA_SOURCES.csv. No keys or passwords appear here.

## Per block

| block | what | items | proven | untested | in repo yes/partly/no |
|---|---|---|---|---|---|
| A | TA-Lib indicators + candles (own price/volume) | 194 | 193 | 0 | 192/0/2 |
| B | Sector/style ETFs | 16 | 16 | 0 | 15/1/0 |
| C | Theme peers | 1 | 0 | 1 | 0/1/0 |
| D | Earnings | 3 | 3 | 0 | 3/0/0 |
| E | SEC Form 4 | 1 | 1 | 0 | 1/0/0 |
| F | FINRA short interest + short volume | 2 | 2 | 0 | 0/0/2 |
| G | Halts + Reg SHO | 2 | 2 | 0 | 1/1/0 |
| H | SEC XBRL fundamentals | 3 | 1 | 2 | 1/0/2 |
| I | FRED macro | 2 | 1 | 1 | 1/1/0 |
| J | Dividends/splits | 1 | 1 | 0 | 0/0/1 |
| K | Market breadth | 2 | 2 | 0 | 2/0/0 |
| L | Analyst actions | 1 | 1 | 0 | 0/0/1 |
| M | 13F | 1 | 0 | 1 | 0/0/1 |
| N | Options | 2 | 1 | 1 | 0/0/2 |
| O | GDELT news | 1 | 0 | 1 | 0/0/1 |
| P | Finviz snapshot (live only) | 1 | 1 | 0 | 0/0/1 |

Note: "proven" counts include "proven (with fails)" for FINRA daily short volume and "proven (partial)" / "proven (live only)" for options and Finviz - see the CSV.

## Biggest gaps

- **2025-26 data is not in the repo for anything.** data-2020-24-v1 stops at 2024-12-31. Earnings, short interest, short volume, halts and Reg SHO for 2025-26 sit on the box only; prices for 2025-26 must be pulled again on a runner.
- **Not tested at all:** SEC XBRL fundamentals (H: I192, I194), ALFRED vintages for FRED macro beyond VIX (I195), 13F (M), GDELT (O), CBOE market-wide options (I201), theme-peer clusters (C).
- **Single-stock options (N) is still a gap:** CBOE live works but has no history; DoltHub IV history covers 2020 to about Oct-2024 only, Mon/Wed/Fri, survivors only.
- **Proven but box-only (not in repo):** FINRA short interest + daily short volume (F), dividends (J), analyst actions (L), NYSE Reg SHO list, raw halts. Kimi cannot read these until they are uploaded as a release.
- **Known failures:** Stooq (TLS closed), FINRA short-volume CDN for old dates (403), FINRA ATS weekly some weeks (204), Finviz public float fields (empty), iShares holdings (HTML not CSV), Yahoo 1-minute data older than 30 days (422), Finviz Elite export not tested (token lives only in Actions secrets).
- **Finviz snapshot (P)** starts 2026-08-06 and is live-check only; never scored.
- **Survivor bias:** universe, breadth, sector labels and DoltHub options are survivors-only.

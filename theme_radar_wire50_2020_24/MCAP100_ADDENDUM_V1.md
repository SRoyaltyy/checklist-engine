# Theme Radar MCAP100 addendum V1 — $100M market-cap filter (add-only; committed BEFORE any filtered result is computed)
Owner: Theme Radar. Written Fri 2026-10-23 HKT. Frozen files (RULES_V1.md, RULES_V1_ADDENDUM_A.md, RESULTS_V1.md, WIRE50_RESULTS_V1.csv, wire50_score.py; theme-radar research/casebook/*) are NOT edited. 2020–24 only; 2025–26 stays sealed and is not opened.

Scope: (a) the 110 WIRE50 tests (55 rows x E1/E2), exactly as RULES_V1.md + Addendum A; (b) the F4TR casebook (theme-radar PR #17, 2,154 buyable cases, build_cases.py) exactly as built.

## Share counts
Source: sec_shares_out_filed_le_2024.parquet in New Bot's nb_tags_v2.tar.gz (Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4, sha256 573fcea379b9525005d007ed1dd6d255b1dfcc6493039b4284aec1278a86ffb3; SEC dei shares outstanding, filed <= 2024-12-31). Matched by ticker.
Cleaning = Taskforce rule trajectory/MCAP100_CLEAN_ADDENDUM_V1.md (a9a1d2aa), unchanged: a filing row is invalid (removed) if val <= 0, val > 1e11, or val > 50x / < 1/50x that ticker's median val. Ties on filed date: latest `end`. Trade-level: implied mcap > $5T -> count treated as missing.

## Point-in-time market cap
For a trade/stock-day with entry session E and decision day D (= last price bar strictly before E; for SI/ATTN/casebook D is the signal day, for OPT rows entering at the open of S it is the prior bar):
mcap = close(D) x the latest valid share count whose `filed` date is strictly before E. No count -> NOCOUNT.

## Filter (applied BEFORE run collapsing/pairing/scoring, to cases AND to controls)
- MAIN: drop stock-days with known mcap < $100,000,000; keep NOCOUNT.
- WARNING: also drop NOCOUNT stock-days.
The filter is applied to the per-row YES stock-days before runs are collapsed (a run starts on the first YES day that survives the filter), and to every control stock-day (control mean for a date = mean over buyable stock-days that survive the same filter).
Everything else unchanged: buyable v2 filter, EXIT_RULE_V1 (E1: +20% TP else day-15 close) and 10-day hold (E2), 30bp each way, discover 2020–22 / confirm 2023–24, pass = in BOTH periods trades >= 30, win > 55%, mean excess > 0.

## Reported
Both versions; pass counts; trades/cases removed per version vs V1 (unfiltered); count of filing rows removed by cleaning. Casebook: filtered summary CSV (no edits to the frozen casebook CSV). No new tests are added to the luck-correction count beyond the 110 re-scored twice (flagged as robustness re-scores of the same rows).

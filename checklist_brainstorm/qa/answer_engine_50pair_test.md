# Answer engine 50-pair acceptance test

**Verdict: PASS**

- Tester: Manager Bot verifier
- When: 2026-10-22 Asia/Hong_Kong (re-run after YES/NO reason fix)
- Prior run: **FAIL** on empty YES/NO reasons (taskforce / grok-bot / new-bot)
- This run: `r2_after_reason_fix` — same seed `20261022` / same 50 pairs
- Command: `python3 /workspace/checklist_brainstorm/engine/answer.py --ticker T --date D`
- Sheet: `merged_draft_v8.1.csv` — **21,423** rows
- Readers: `grok.py`, `james.py`, `new-bot.py`, `theme_radar.py`, `trading-bot-taskforce.py`
- Setup note: identical duplicate `trading-bot-taskforce-v1.2-reasons.py` was renamed to `_trading-bot-taskforce-v1.2-reasons.py` (underscore = skipped by runner). Without that, every Taskforce id CONFLICT’d (8,513 rows). File kept as backup.
- CSVs: `engine/out/50pair_r2/`
- Elapsed (pair runs): 66 min

## Criteria

| # | Criterion | Result |
|---|-----------|--------|
| 1 | 50 pairs × 21,423 rows; YES/NO/NOT_READY only; zero blank answers | **PASS** (50/50) |
| 2 | EVERY row including YES/NO has non-empty reason | **PASS** — empty_reason_total = **0** |
| 3 | 5 reruns byte-identical | **PASS** (5/5) |
| 4 | Spot-check taskforce/grok/new-bot YES/NO reasons non-empty | **PASS** (see below) |

## Empty reasons by owner

Across all **1,071,150** answers (50 × 21,423):

| owner\|answer | empty reason count |
|---------------|-------------------:|
| *(none)* | **0** |

`empty_reason_by_owner_answer` = `{}`

## Spot-check (taskforce / grok-bot / new-bot)

| Ticker | Date | Owner | YES/NO rows | empty | Sample reasons |
|--------|------|-------|------------:|------:|----------------|
| AAPL | 2026-10-21 | taskforce | 6538 | 0 | 'Body % of range>=0.8'; 'BUT Body % of range<=0.1' |
| AAPL | 2026-10-21 | grok-bot | 652 | 0 | 'upgrades minus downgrades: net_Nd=-1 thr=+1'; 'upgrades minus downgrades: net_Nd=-1 thr=-1' |
| AAPL | 2026-10-21 | new-bot | 191 | 0 | 'X=0.0015_top_decile_of_last_5d'; 'X=0.0015_bottom_decile_of_last_5d' |
| CELH | 2024-06-12 | taskforce | 6538 | 0 | 'Body % of range>=0.8'; 'BUT Body % of range<=0.1' |
| CELH | 2024-06-12 | grok-bot | 652 | 0 | 'upgrades minus downgrades: net_Nd=+0 thr=+1'; 'upgrades minus downgrades: net_Nd=+0 thr=-1' |
| CELH | 2024-06-12 | new-bot | 163 | 0 | 'event_count_20d=2>=2'; 'event_count_20d=2' |
| TSLA | 2026-08-25 | taskforce | 6538 | 0 | 'Body % of range>=0.8'; 'BUT Body % of range<=0.1' |
| TSLA | 2026-08-25 | grok-bot | 652 | 0 | 'upgrades minus downgrades: net_Nd=+0 thr=+1'; 'upgrades minus downgrades: net_Nd=+0 thr=-1' |
| TSLA | 2026-08-25 | new-bot | 189 | 0 | 'X=-0.0028_top_decile_of_last_5d'; 'X=-0.0028_bottom_decile_of_last_5d' |

## Byte-identical reruns

| Ticker | Date | Identical | SHA256 prefix |
|--------|------|-----------|---------------|
| TSLA | 2026-08-25 | YES | `8f76d87bcb63aaee…` |
| KO | 2026-09-08 | YES | `c6c2158d3973590e…` |
| AMD | 2026-08-19 | YES | `a6eebecb8171e709…` |
| SPY | 2026-09-04 | YES | `4d1ef0eac790b4ce…` |
| C | 2026-10-01 | YES | `0b8a29fce5ef057a…` |

## Overall answer totals

| Answer | Count |
|--------|------:|
| YES | 105,432 |
| NO | 617,976 |
| NOT_READY | 347,742 |

## NOT_READY reason histogram (prefix before `:`)

| Reason prefix | Count | Share |
|---------------|------:|------:|
| `some_folded_timeframes_not_ready` | 108,110 | 31.1% |
| `no_snapshot_yet(first usable theme-radar snapshot is dated 2026-08-06, usable from 2026-08-07)` | 40,528 | 11.7% |
| `data_source_gap` | 37,272 | 10.7% |
| `held` | 33,100 | 9.5% |
| `finviz_snapshot_reader_not_built (theme-radar snapshots from 2026-08-06)` | 28,000 | 8.1% |
| `history_too_short` | 22,884 | 6.6% |
| `unsupported` | 18,810 | 5.4% |
| `missing_data` | 10,930 | 3.1% |
| `HOLD` | 10,400 | 3.0% |
| `no_universe_snapshot` | 9,282 | 2.7% |
| `held/to_cut_review` | 5,900 | 1.7% |
| `field_empty_in_window` | 5,140 | 1.5% |
| `insufficient_history` | 3,966 | 1.1% |
| `before_series_start` | 3,278 | 0.9% |
| `rule_ambiguous` | 2,816 | 0.8% |
| `needs_universe` | 2,400 | 0.7% |
| `no_evaluator` | 1,592 | 0.5% |
| `hold_finviz_shares` | 840 | 0.2% |
| `to_cut_v5.5f` | 700 | 0.2% |
| `degenerate` | 512 | 0.1% |

## Example — AAPL 2026-10-21 by owner

| Owner | YES | NO | NOT_READY | empty reasons |
|-------|----:|---:|----------:|--------------:|
| grok-bot | 80 | 572 | 1222 | 0 |
| james | 349 | 6536 | 909 | 0 |
| new-bot | 49 | 142 | 459 | 0 |
| taskforce | 1421 | 5117 | 1975 | 0 |
| theme-radar | 143 | 883 | 1566 | 0 |

## Pair results

| # | Ticker | Date | Era | Kind | YES | NO | NOT_READY | empty | Status |
|---|--------|------|-----|------|----:|---:|----------:|------:|--------|
| 1 | AAPL | 2026-10-21 | post_08-06 | liquid | 2042 | 13250 | 6131 | 0 | PASS |
| 2 | NVDA | 2026-10-21 | post_08-06 | liquid | 2208 | 13104 | 6111 | 0 | PASS |
| 3 | CRMT | 2026-10-21 | post_08-06 | small | 2260 | 12974 | 6189 | 0 | PASS |
| 4 | MSFT | 2024-01-02 | pre_08-06 | liquid | 1930 | 11780 | 7713 | 0 | PASS |
| 5 | CELH | 2024-06-12 | pre_08-06 | small | 2258 | 11470 | 7695 | 0 | PASS |
| 6 | SPY | 2025-04-07 | pre_08-06 | liquid | 2253 | 10671 | 8499 | 0 | PASS |
| 7 | AAPL | 2026-08-06 | post_08-06 | liquid | 2262 | 11454 | 7707 | 0 | PASS |
| 8 | IWM | 2026-08-07 | post_08-06 | liquid | 1905 | 11817 | 7701 | 0 | PASS |
| 9 | SOFI | 2024-01-04 | pre_08-06 | small | 2171 | 11527 | 7725 | 0 | PASS |
| 10 | RIOT | 2026-03-26 | pre_08-06 | small | 2074 | 11652 | 7697 | 0 | PASS |
| 11 | MARA | 2024-07-16 | pre_08-06 | small | 1948 | 11778 | 7697 | 0 | PASS |
| 12 | CLOV | 2024-03-28 | pre_08-06 | small | 2232 | 11476 | 7715 | 0 | PASS |
| 13 | NKLA | 2024-10-22 | pre_08-06 | small | 367 | 5801 | 15255 | 0 | PASS |
| 14 | SPCE | 2024-10-15 | pre_08-06 | small | 1970 | 11756 | 7697 | 0 | PASS |
| 15 | BYND | 2025-04-04 | pre_08-06 | small | 2323 | 11403 | 7697 | 0 | PASS |
| 16 | AAPL | 2026-07-20 | pre_08-06 | liquid | 2008 | 11700 | 7715 | 0 | PASS |
| 17 | MSFT | 2024-06-07 | pre_08-06 | liquid | 2075 | 11635 | 7713 | 0 | PASS |
| 18 | NVDA | 2024-10-15 | pre_08-06 | liquid | 1918 | 11806 | 7699 | 0 | PASS |
| 19 | AMZN | 2024-08-12 | pre_08-06 | liquid | 2511 | 11201 | 7711 | 0 | PASS |
| 20 | GOOGL | 2026-01-29 | pre_08-06 | liquid | 2218 | 11492 | 7713 | 0 | PASS |
| 21 | META | 2026-08-17 | post_08-06 | liquid | 2133 | 13073 | 6217 | 0 | PASS |
| 22 | TSLA | 2026-08-25 | post_08-06 | liquid | 2307 | 12905 | 6211 | 0 | PASS |
| 23 | JPM | 2026-09-29 | post_08-06 | liquid | 2313 | 13005 | 6105 | 0 | PASS |
| 24 | XOM | 2026-09-16 | post_08-06 | liquid | 1870 | 13432 | 6121 | 0 | PASS |
| 25 | JNJ | 2026-08-06 | post_08-06 | liquid | 2244 | 11474 | 7705 | 0 | PASS |
| 26 | UNH | 2026-09-29 | post_08-06 | liquid | 2176 | 13134 | 6113 | 0 | PASS |
| 27 | V | 2026-08-17 | post_08-06 | liquid | 1931 | 13267 | 6225 | 0 | PASS |
| 28 | MA | 2026-09-09 | post_08-06 | liquid | 2160 | 13130 | 6133 | 0 | PASS |
| 29 | HD | 2026-08-19 | post_08-06 | liquid | 2047 | 13061 | 6315 | 0 | PASS |
| 30 | PG | 2026-09-29 | post_08-06 | liquid | 2195 | 13081 | 6147 | 0 | PASS |
| 31 | KO | 2026-09-08 | post_08-06 | liquid | 1951 | 13337 | 6135 | 0 | PASS |
| 32 | PEP | 2026-09-18 | post_08-06 | liquid | 1936 | 13364 | 6123 | 0 | PASS |
| 33 | WMT | 2026-08-11 | post_08-06 | liquid | 2101 | 13003 | 6319 | 0 | PASS |
| 34 | COST | 2026-08-11 | post_08-06 | liquid | 2212 | 12878 | 6333 | 0 | PASS |
| 35 | AVGO | 2026-10-21 | post_08-06 | liquid | 2034 | 13282 | 6107 | 0 | PASS |
| 36 | AMD | 2026-08-19 | post_08-06 | liquid | 2211 | 13005 | 6207 | 0 | PASS |
| 37 | NFLX | 2026-08-19 | post_08-06 | liquid | 2223 | 12987 | 6213 | 0 | PASS |
| 38 | CRM | 2026-09-17 | post_08-06 | liquid | 2659 | 12683 | 6081 | 0 | PASS |
| 39 | ORCL | 2026-08-12 | post_08-06 | liquid | 2357 | 12845 | 6221 | 0 | PASS |
| 40 | INTC | 2026-08-14 | post_08-06 | liquid | 2109 | 13081 | 6233 | 0 | PASS |
| 41 | BA | 2026-09-28 | post_08-06 | liquid | 2125 | 13189 | 6109 | 0 | PASS |
| 42 | CAT | 2026-08-26 | post_08-06 | liquid | 2284 | 12918 | 6221 | 0 | PASS |
| 43 | GE | 2026-09-22 | post_08-06 | liquid | 2593 | 12711 | 6119 | 0 | PASS |
| 44 | DIS | 2026-09-22 | post_08-06 | liquid | 2466 | 12832 | 6125 | 0 | PASS |
| 45 | SPY | 2026-09-04 | post_08-06 | liquid | 1790 | 12406 | 7227 | 0 | PASS |
| 46 | QQQ | 2026-08-14 | post_08-06 | liquid | 1844 | 12322 | 7257 | 0 | PASS |
| 47 | IWM | 2026-10-21 | post_08-06 | liquid | 1894 | 12338 | 7191 | 0 | PASS |
| 48 | GS | 2026-08-21 | post_08-06 | liquid | 2002 | 13218 | 6203 | 0 | PASS |
| 49 | BAC | 2026-09-15 | post_08-06 | liquid | 2406 | 12898 | 6119 | 0 | PASS |
| 50 | C | 2026-10-01 | post_08-06 | liquid | 1926 | 13370 | 6127 | 0 | PASS |

## Artifacts

- This report: `/workspace/checklist_brainstorm/qa/answer_engine_50pair_test.md`
- Machine JSON: `qa/answer_engine_50pair/results_r2.json`, `pairs.json`
- CSVs: `engine/out/50pair_r2/answers_<T>_<D>.csv` (+ `.rerun.csv`)
- Page: https://sroyaltyy.github.io/checklist-answers/

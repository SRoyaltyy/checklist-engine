# UNTESTED_V1 results — PRACTICE 2020–24, HINT, SURVIVORS-ONLY (rules: UNTESTED_V1_RULES.md, commit dc659dff, pushed before this run)
No bar after 2024-12-31 read; price sha fb9bbe69…ef337 asserted. Market-cap floor not applied (no point-in-time share file).

Scope: 87 master ideas + 1,581 map v5.1 rows (1,668 rows) → 1,629 distinct answer columns = 1,629 tests (39 master ideas share a map column).
BH family: 6,802 prior + 2 × 1,629 = **10,060** (prior p-values treated as 1).
Trades = YES answers on the stored ledger cells (the FINDINGS_FREEZE_V1 setup cells); 43,060 of 147,986 cells survive drop_list_v2 + 21-bar room.

| result | master | map | total rows |
|---|---|---|---|
| PASS | 0 | 0 | 0 |
| FAIL | 1 | 7 | 8 |
| TOO FEW (<30 YES trades in a period) | 86 | 1,574 | 1,660 |
| of which never YES on any tradable cell | 48 | 1,075 | 1,123 |
| NOT COMPUTABLE (no answer column / all NR) | 0 | 0 | 0 |

The 8 FAIL rows are near-always-YES (PV-TF-159 SMA20 slope; NB options-expiry/quad-witching rank rows): ~21.6k trades 2020–22, ~16.8k 2023–24;
exit-v1 win 48–50%, 10-day win 45–47%, excess positive on 2020–22 (+1.0–1.2%) and negative on 2023–24 (−0.14 to −0.17%). BH q = 1.
Why "built but not tested": these rows are answered but almost never YES on setup cells, which is why item_ranking skipped them.
Testing them needs the full universe (not just setup cells) or the NO side — not pre-registered here, so not done.
Full table: untested_results_v1.csv.

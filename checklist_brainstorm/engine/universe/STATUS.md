# Universe engine status (Grok Bot) — updated 2026-10-22 12:15 HKT
Price: /workspace/pricehist/universe_2020_survivors.parquet (split-only; 11,712 tickers). SPY for TR from etf_2015.parquet. survivor_only=true, sector_map=current_backfilled.
Labels: chunks/{y}__LABELS.parquet, dividend_adjusted=true (dividends_2020.parquet, added on next-open ex-date; >20% capped+flagged).
## Pieces
- shared_tier.py: ticker-free ids (8,176) + 'base' of BUT rows, once per date (readers unchanged) -> shared/{y}.parquet, chunks/{y}__SHARED.npz
- engine_year.py: 1,478 ticker-dep JG ids vectorized (BUT = base AND stock prior-session move on volume). 2-bit packed year x sector chunks (sectors >2000 tickers split into parts).
  Deferred: 240 grok analyst rows (per-ticker Yahoo ratings) -> NOT_READY; 489 james sector rows are NR before 2026-08-06 (no snapshot) and NR (not vectorized) after.
- tr_port.py + tr_year.py: Theme Radar 528 rows (2,808 row|N keys), formulas unchanged; rank rows per date over whole universe.
- counts_v2.py: per stock-morning yes/ready/frac per scope(mkt|stk) x source x lens x meaning; asterisk->context; lean + ctx_opp; excludes new-bot_excluded_inference. Tag sha256 checked.
## Equivalence
- JG 2024 vs 1,200 slow preburn cells x 9,654 ids: 0 mismatches except the 240 deferred analyst ids (138,688 cells, all X>NOT_READY). No price-source differences observed.
- TR port vs original answer_rows: 553,720 answers, 0 mismatches. TR batch invariance (with N in key): 726,888, 0 mismatches.
## Speed
- shared tier ~12.7 s/date/worker (3 workers); JG stock tier ~19 us/stock-day (57 s per universe-year); TR nonrank 0.26 ms/ticker-day (60 min all years, 1 proc); TR rank+assembly ~3 min/yr; counts_v2 ~1.5 min/yr.

## 12:35 HKT update
- Counts v2 (room spec) DONE for 2023, 2024, 2025, 2026 (JG). TR counts DONE for 2024, 2026. Files: chunks/{y}__COUNTS2_MKT.parquet, chunks/{y}__COUNTS2_STK__{sector}.parquet, chunks/{y}__COUNTS2_TR__{sector}.parquet.
- grok_tags.csv locked (chmod 444) sha256 505f452c65cdabda1576f978ad9a76be5acc546b4b41d0268caeb05d14f58ad7. Tag fingerprints checked at run time (james 11a45eb7, theme-radar ac295dcf, new-bot 1849cb7c).
- New Bot's 650 rows are tagged but not in this engine (no reader port), so they add nothing to the counts yet.
- Queued (one job at a time): shared 2021 -> 2020 (queue_shared.sh), JG engine+counts per year (watch_years.sh), TR rank+assembly+counts 2023, 2022, 2021, 2020 (tr_chain.sh), then TR 2025 retry (its first try ran out of memory; fixed: TR sectors split into parts of at most 400k rows).
- Sector add-on (James 489 sector rows, sector_map=current_backfilled): secadd_queue.sh starts after the main build is idle.
  437 SECTOR_ONLY rows run once per sector x date for all stocks; 52 STOCK_SECTOR rows run per cell for the S&P 500 long-listed subset (2024 first, ~2 h on 2 workers).
  Outputs: chunks/{y}__SECADD_{ALL,SP500}.npz/.json, chunks/{y}__COUNTS2_SECADD_{ALL,SP500}.parquet; equivalence: secadd_equiv.py (24 cells) -> secadd.log.

## 13:33 HKT update
- All JG years 2020-2026 + counts v2 done; TR 2020-2026 done (2025 retry OK). All uploaded to checklist_engine_chunks.
- FRESH (fresh.py): chunks/{y}__FRESH__<sector>.parquet, groups source|lens over quiet_warning ids (JG STK chunks + TR keyed row|N), cols qw_fresh, qw_yes, qw_ready, qw_frac, qw_jump_z (prior 20 sessions, min 10). 2024, 2025 done; others queued in fresh.log.
- coverage_2024.md written (v8.2 buckets + master.csv tables).
- Sector add-on: A 2024 done; B 2024 (S&P cells) running, ETA ~17:30 HKT, then assemble -> secadd_equiv.py -> secadd_counts.py.

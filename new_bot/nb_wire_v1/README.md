# nb_tags_v1 — New Bot map v5.1 rows, 2020-24 tags (add-only)
- nb_tags_{2020..2024}.parquet: ticker,date,packed (2-bit codes 0=NR 1=NO 2=YES, 4/byte, id order in nb_tags_ids.json). 682 map ids present in chunks (646 = 614 NB/NBW/NBX + 32 SI/FINRA; 36 excluded rows absent).
- Survivors-only universe; (ticker,date) pairs in drop_list_v2.csv (sha 5a6cb756...) removed. Only 2020-24 files read; no 2025/26 data opened.
- PIT: answer for D uses bars < D (merge_asof, allow_exact_matches=False). Earnings timing unknown in 2020-24 -> reaction session = first session strictly after report_date.
- New in this pass (NBW): NB-014 (earnings-anchored AVWAP, daily typical price approx), NB-022 (Nasdaq historical EPS surprise%, consensus may be back-filled), NB-024 (reaction z vs prior 12; sparse before ~2023), NB-091 (earnings big-bar W1 lenses; PS variants constant NO, BUT==main).
- nb_map_status_v1.csv: per-row WIRED/WIREABLE/WIRED_DEGENERATE/BLOCKED + reason. for_james_step3.csv: rows to send to winner-vs-loser test.

Parquet tags (not committed, 52 MB tarball): Drive id 1kk2VvkUtsLgv3A3Qhr1Z71yMN2JJoN32, sha256 42de7de65488ae96d1c08112d210316afd5d878daf6afb991c02d7aa8ac01483

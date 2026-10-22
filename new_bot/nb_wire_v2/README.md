# nb_tags_v2: adds CAC-042/043 and DIL-050 to nb_tags_v1 (add-only; v1 files unchanged)
- nb_tags_{2020..2024}.parquet: same keys and row counts as v1. Same code set (0=NR 1=NO 2=YES, 2-bit pack). Ids are in nb_tags_ids.json; it now includes NBW2 owners. No 2025/26 data opened; drop_list_v2 applied; survivors only.
- CAC-NB-042/043: Nasdaq dividends API (declaration date, ex-date, Cash amount); ex-dates after 2024-12-31 discarded. Event for D = ex-date D with declaration on or before the prior bar. 042: amount / close(prior bar) >= 1%. 043: amount >= 2x the prior Cash amount. NR when: the ticker is not Nasdaq-listed (the API returns nothing for NYSE); the declaration date is N/A; or one of the 10 paid-but-missing tickers.
- DIL-NB-050: SEC XBRL dei:EntityCommonStockSharesOutstanding, matched by filing date on or before the bar (only facts filed by 2024-12-31). YES when shares / shares 60 bars earlier >= 1.2; split-like ratios are excluded heuristically. It is a state, so W0-EVT fires on every bar in the window.
- DIL-NB-051 stays BLOCKED: there is no PIT float share count.
- for_james_step3_v2.csv = v1's 193 rows + the new non-degenerate CAC/DIL rows.

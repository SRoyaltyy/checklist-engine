# COMBO_MODEL_V1 — Addendum C (before any training or outcome join)
Registered 2026-10-23 ~02:45 HKT.
1. **$100M market-cap buyable filter applied** (both training sample and 2023–24 check). Shares = latest SEC XBRL
   dei:EntityCommonStockSharesOutstanding with filing date strictly before D (New Bot nb_tags_v2.tar.gz, Drive
   1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4, sha256 573fcea3…86ffb3 verified; file sec_shares_out_filed_le_2024.parquet, filings <= 2024 only).
   Market cap = shares x close of the bar before D. Stock-days with known cap < $100M are removed. Stock-days with no prior filing
   (cap unknown) are KEPT and counted/reported separately (flag: cap unknown). The 300,000 training sample is the V1 draw with the
   filter then applied (still a uniform draw from the filtered 2020–22 population).
2. **New Bot's new rows included:** nb tags now read from nb_tags_v2 (same 646 ids/keys as v1, adds answers for CAC-NB-042/043
   dividend-announcement and DIL-NB-050 dilution rows; DIL-NB-051 stays blocked/NR). Same broken-row rule. Any CAC (dividend-date)
   row among the model's top splits/weights is flagged POSSIBLE LOOK-AHEAD (declaration/ex-date timing), as are earnings/reaction rows.

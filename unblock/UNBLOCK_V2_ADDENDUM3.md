# UNBLOCK_V2_ADDENDUM3 — BRW-NB-005 (Reg SHO threshold list), pre-registration
Committed before any result for this test. Frozen files are not modified.

- Source: New Bot file regsho_nasdaq_th_2020_24.csv (Drive 1HYHBYJN59Sk7sw9mKw6zaahMP9g-XJ87), sha256 d5032717db7d0a8cd064f054b47a7ea435c1d0e8fc759518990b630a1eb73045, 29,522 rows, 2020-01-02..2024-12-31, Nasdaq threshold lists only. nyse_th/ ignored. Parent parquet not opened; no 2025-26 data used.
- Feature REGSHO_TH (yes/no): for entry day D, take the most recent Nasdaq list date L < D (the D-1 list). YES if the ticker is on list L; NO if it is Nasdaq-listed and not on L; -1 (unknown, not NO) otherwise, or if L is more than 5 calendar days before D.
- Nasdaq-listed = exchange "Nasdaq" in SEC company_tickers_exchange.json (pulled 2026-10-23, sha256 c4c73cd3...e408; current, not point-in-time) OR the ticker appeared on a Nasdaq threshold list on some date <= L. Non-Nasdaq stocks are unknown.
- Same harness as wave 2 (w2_run.py): survivors, drop_list_v2, Exit A (+20% target, close day 15) and Exit B (10-day hold), fee 0.006 round trip, $100M mcap filter on population and benchmark, excess vs same-date mean of the filtered population, 500-sample date-clustered bootstrap.
- Only the YES bucket is tested: 4 p-values (2 exits x 2 periods). BH family n = 14,059 + 4 = 14,063, ranked among these 4.
- Pass: win > 55%, n >= 30, q < 0.05, excess > 0 in both 2020-22 and 2023-24, per exit.

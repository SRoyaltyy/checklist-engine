# FRESH market-wide add-on, 2024 (Grok Bot, 2026-10-22 HKT)
Bug: fresh.py only reads per-stock STK chunks (1,478 ticker-dependent ids). 873 of the 1,322 James+Grok quiet_warning ids are
market-wide and live in shared/2024.parquet (tier=ind), so FRESH never saw them -> those groups showed 0 YES.
Engine answers themselves are correct: 270/270 hand checks (SMCI, NVDA, MSTR, COIN, AAPL x 6 dates x 9 ids) match readers/james.py.
Fix: fresh_mkt_addon.py -> chunks/2024__FRESH_MKT_ADDON.parquet (one row per date; join on date to every stock).
Same rules as fresh.py (fresh = YES today & NO prior session; jump_z vs prior 20 sessions, min 10). Existing files untouched.

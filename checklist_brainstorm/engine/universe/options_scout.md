# Options data scout (Grok Bot, 2026-10-22 HKT). Scouting only: no questions built, nothing downloaded in bulk.

## DoltHub post-no-preference/options (free)
Tables (2):
- option_chain: date, act_symbol, expiration, strike, call_put, bid, ask, vol (implied vol), delta, gamma, theta, vega, rho.
  **There are NO volume and NO open-interest columns** (and no last price).
- volatility_history (one row per stock per date): hv_current, hv_week_ago, hv_month_ago, hv_year_high/low(+dates),
  iv_current, iv_week_ago, iv_month_ago, iv_year_high/low(+dates). Some fields are blank (e.g. AAPL 2024-03-08 had iv_month_ago and iv_year_* empty).
Range: 2019-02-09 .. 2026-10-20 (volatility_history 1,972,067 rows).
Distinct tickers / distinct dates per year (volatility_history):
| year | tickers | dates |
|---|---|---|
| 2019 | 1,683 | 48 (mostly Saturdays, about monthly) |
| 2020 | 1,723 | 155 |
| 2021 | 1,597 | 156 |
| 2022 | 1,605 | 152 |
| 2023 | 1,644 | 148 |
| 2024 | 1,622 | 183 |
| 2025 | 1,606 | 259 |
| 2026 | 1,638 | 205 (to Oct 20) |
Gaps: 2020 to about Oct 2024 is **Monday, Wednesday and Friday only** (about 150 dates a year; Tuesdays and Thursdays are missing).
Every weekday is covered from about Oct 2024 (2024 has only about 15 Tuesdays and 16 Thursdays). The roughly 1.6k names are optionable large/mid caps, not the 11.7k universe.
option_chain sample: 2020-03-16 had 1,573 symbols and 39,718 contracts, with no blank IVs. Per-year aggregates on the chain time out on the SQL API.
Timing: commits land around 06:35 UTC the next day (around 02:35 ET) for the prior date's close, so they are end-of-day and knowable before 09:25 ET.
The repository was created on 2021-04-20. Everything dated before that is a backfill loaded that day, so it is not point-in-time as published (the values are end-of-day quotes; the risk is in which names were included). 2,153 commits.
Bulk download options:
- SQL API (https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master?q=...): fine for volatility_history (about 2M rows, small). It returns at most about 1k rows per call, so page by date.
  Chain aggregates time out, so pull the chain one date (or one symbol) at a time, which comes to about 40k+ rows a date and about 1,700 dates.
- dolt CLI is not installed. A `dolt clone` would pull the whole history (likely tens of GB, estimated rather than measured; disk has about 22 GB free). Not recommended.
  Better: the SQL API for volatility_history, plus a per-date chain pull only for the fields needed, written to parquet with one process at a time.

## Our Yahoo chain archive (fullscan data_snapshots_daily)
Exists: SRoyaltyy/fullscan .github/workflows/data_snapshots_daily.yml, added 2026-10-21 (PR #670). It runs Mon-Fri at 21:40 UTC (cron), and the top 300 tickers get 4 expiries each.
Files: data/snapshots/yahoo_options/2026-10-21 and 2026-10-22 so far (2026-10-22 file: 94,327 contracts, 685 underlyings).
Columns include **volume and openInterest**, plus impliedVolatility, bid/ask/lastPrice and lastTradeDate. It starts 2026-10-21, so there is no history.

## Buildable for 2020-24?
- Per-stock put/call ratio (by volume or OI): **NO.** DoltHub has no volume or OI, and the Yahoo archive starts 2026-10-21.
- Per-stock unusual options activity (volume vs OI or vs average): **NO**, for the same reason.
- Buildable from DoltHub for about 1.6k names on M/W/F (daily from about Oct 2024): IV level, IV rank or percentile (from iv_year_high/low or our own history),
  IV/HV, IV change, put-minus-call IV skew, term structure (near vs far expiry IV), and option-implied move. The Taskforce PV-TF-41x rows in master.csv are of this kind.

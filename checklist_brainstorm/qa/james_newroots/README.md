# James new roots (unposted QA, 2026-10-22 HKT)
Files: history/<src>.csv (full backfill, url+fetched_at per row), raw/<src>_full.json (as sent), raw/initial_pull/, proof_james_newroots.csv (source,date,value,usable_0925et,url,fetched_at), spotcheck.csv (15/15 match), fetch_newroots.py (backfill | nightly [DATE], add-only, not_ready != failure), daily/<src>/<DATE>.json.
| src | history | release (ET) | usable 09:25 ET | revisions/vintages | doc |
|---|---|---|---|---|---|
| SOFR | 2018-04-02 | ~08:00 next business day | D+1 | NY Fed may correct same day by ~14:30 ET; API returns current value only, no vintages; revisionIndicator blank on all 2,136 rows | https://www.newyorkfed.org/markets/reference-rates/sofr |
| ON RRP | 2013-09-23 (39 days with >1 op, summed) | results ~13:15 same day | D+1 | not revised | https://www.newyorkfed.org/markets/desk-operations/reverse-repo |
| Treasury auctions | 1979-10-31 | results ~11:30 (bills) / ~13:00 (coupons) auction day | D+1 | final results not revised; fiscaldata lags days (10-19..10-22 still blank on 10-22), nightly uses TreasuryDirect TA_WS | https://fiscaldata.treasury.gov/datasets/treasury-securities-auctions-data/ , https://www.treasurydirect.gov/webapis/ |
| TGA (DTS) | 2005-10-03 | ~16:00 next business day | D+2 | rarely corrected, no vintages; account label changed 2021 (Federal Reserve Account -> TGA Closing Balance) | https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/ |
| UST par curve | 1990-01-02 | after close, by ~18:00 same day | D+1 | occasional corrections, no vintages; method change Dec 2021, history not restated | https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics |

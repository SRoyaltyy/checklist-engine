# Manager Bot QA — Grok v3e retest, James new sources, Taskforce timeframes pilot (2026-10-22 ~03:55 HKT)
Only real fetched data counts. Work files: qa/v3e_dl, qa/v3e_repull, qa/v3e_check_root, qa/james_tc/truthcheck.csv, qa/tf_check/tf_spot.csv.

## JOB 1 — Grok v3e
The Drive files are byte-identical (md5) to out_v3e/, inbox/grok-bot-finviz.csv, inbox/grok-bot-ratings.csv and qa/src/fetch_proof_grok-bot*.csv. Main has 1,654 rows and ratings has 64.
- CFTC start dates: 320 rows, all equal to my report (BTC 2018-04-10; VX 2006-08-29 TFF / 2004-07-27 legacy; ES 1997-09-16, NQ 1999-06-22, RTY 2002-08-13, DX 1992-05-29 commercials; HG 1989-07-31, NG 1990-04-12, ZC/ZS 1998-01-06 large spec; others 2006-06-13 / 1986-01-15). PASS.
- Jobless claims / ISM / VX=F: 0 rows. PASS.
- HOLD=no_nightly_archive: exactly 438 rows (median PT chg 112, price vs mean target 112, revenue next-Q revision 112, beta-residual 102, which was v3c's "future move minus stock return"). These are my 4 failed series. PASS.
- Pin note for 08-06: rewritten=yes, 94cb047, 312.41/32.76 (first commit 6650943 at 313.87/32.91). PASS.
- Ratings ids: FV-GB-3009..3078, 64 unique. 0 duplicates within Grok. 0 collisions with any other inbox file. PASS.
- check_v3 a–k (run on a separate root qa/v3e_check_root with symlinked inbox and qa/src): grok-bot-finviz, grok-bot-ratings and grok-bot-vix-term all have 0 fails. 1,008 h-WARN = 9 save_nightly series × 112 rows (expected).
- Live re-pull of the 72 proof series (qa/v3e_repull): 63 PASS, 0 real FAIL, 9 NOT TESTED. All CFTC series pass on real first/last report dates, and so do upgrades_downgrades and beta-residual (Yahoo). The 9 not tested are save_nightly series with no history to re-pull: median PT chg, price vs mean target, target price chg, recom chg, EPS growth this/next yr chg, forward EPS chg, EPS next-Q revision, revenue next-Q revision. No FRED rows.
- **FLAG (not a check fail):** "EPS next Q revision" (112 rows) says "own snapshots from 2026-10-22". It has no archive, just like revenue next-Q revision, which is HELD, but it does NOT carry HOLD. In v3c it only "passed" through a Yahoo price-history backup, which proves nothing. It should also get HOLD=no_nightly_archive (550 held). The other 5 Finviz-snapshot series rely on Theme Radar's pinned archive from 08-06, so they are OK under the pin ruling.

## JOB 2 — James new sources: 10 random values each vs the publisher, fetched live (seed 20261022)
| source | match | checked against |
|---|---|---|
| SOFR | 10/10 | NY Fed markets API, single-date query |
| ON RRP | 10/10 | NY Fed reverse-repo propositions API, single-date query (sums ops) |
| Treasury auctions | 10/10 high yield/rate; bid-to-cover also equal where present | TreasuryDirect TA_WS by CUSIP (different system from fiscaldata) |
| TGA (DTS) | 10/10 | fiscaldata DTS single-date query. Since 2021 the value sits in open_today_bal of the "TGA Closing Balance" row, and James's value matches it |
| UST par curve | 10/10 on 2y/10y/3m/30y (blank 30y in 2004 = blank) | home.treasury.gov yearly CSV |
Mismatches: 0. My first pass showed false mismatches on auctions and TGA, caused by my own field-name bugs. I fixed those and re-ran.
Caveat: SOFR, RRP and TGA come from the same publisher API family James used, though from different queries. There is no independent web-page copy.

Release times / known-at:
- SOFR: the NY Fed page says "approximately 8:00 a.m. ET" each business day → usable D+1 at 09:25. Live check: at 15:49 ET 10-21 the latest was 10-20. **OK**.
- ON RRP: the live API already had the 10-21 op (237,000,000) by 15:49 ET the same day → D+1 is safe. **OK**.
- Auctions: results come out on auction day (from TreasuryDirect) → D+1 is safe. **OK** (I did not re-fetch the exact time of day).
- TGA/DTS: published ~4:00 PM ET the next business day. I did NOT re-verify this live: the fiscaldata page is JS-only and the API timed out once. The D+2 rule is conservative and safe either way. **OK, release time not re-verified.**
- Yield curve: the 10-21 row was already in the CSV at 15:49 ET 10-21 → D+1 is safe. **OK**.
Revision risk: SOFR, TGA and the curve can be corrected with no vintages kept, so the nightly save is the only point-in-time record. Treasury changed the curve method in Dec 2021 and the TGA label in 2021, and neither history was restated. Auction finals and RRP are effectively not revised.

## JOB 3 — Taskforce timeframes pilot (224 rows)
- check_v3: 0 fails on a–k.
- My own recompute: separate pure-Python code on a fresh Yahoo daily pull (period1=0), compared with Taskforce tfx.py.
  - Coverage: AAPL/MSFT/NVDA × D in {2025-06-11, 2025-03-03 (Mon & 1st of month = no partial bar), 2024-11-27} × 2D/3D/W/M × completed/ptd × RSI14, MACD hist, %B, close/SMA20, close/SMA50.
  - Result: **360/360 match** (tolerance 1e-4 relative), and the last-bar end dates are identical.
- AAPL weekly RSI14 at D=2025-06-11, completed: 44.914816 (week ending 2025-06-06) — **confirmed**. The ptd value is 44.393233 (through 06-10).
- Point-in-time: in every case the bars end before D. ptd uses sessions through D-1. Completed drops D's period entirely, and on 2025-03-03 W/M ptd == completed.
- Not checked: SMA20-vs-SMA50 cross rows (no claimed values to compare) and twin thresholds.

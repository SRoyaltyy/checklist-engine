> **SUPERSEDED 2026-10-22 by PRELOCK_ADDENDUM_OHLCV6.md** (NB-026 merged into UP10_DAY, BH across 6). Do not score.

# PRELOCK ADDENDUM: OHLCV-7 skip/trim warnings (for the joint lock Fri 2026-10-23 23:00 HKT)
Written 2026-10-22 ~16:50 HKT by Trading Bot Taskforce on Manager's decision. Separate from PRELOCK_2025_26.md and PRELOCK_ADDENDUM_00051.md, which are untouched. No 2025–26 data was opened.

## Exactly 7 rows (event start = first YES day after a non-YES day, per ticker)
1. VOLJUMP: stdev(log ret, 10) / stdev(log ret, 60) > 2
2. RVOL>=5: volume D / mean(volume, 50 sessions to D−1) ≥ 5 (min 40)
3. UP10_DAY: close D / close D−1 − 1 ≥ +10%
4. NB-026 T1-THR: nb4-REL-NB-026-T1-THR = YES (code 2; ready = codes 1 or 2)
5. NB-029 P5-POSQ: nb4-HIS-NB-029-P5-POSQ = YES. POSD is the same row and is not tested separately.
6. GAPDOWN: open D / close D−1 − 1 ≤ −5%
7. MFI>80: Money Flow Index(14) on typical price × volume > 80

## Rule
- Signal from bars through close D. Entry at the open of D+1, exit at the open of D+21 (20-session hold). Dividends with ex-date in the hold are added back (capped at 20% of open). |ret| > 200% is dropped. Fee 30bp/side (0.60% round trip). Funds/CEFs/shells are excluded (Finviz 2026-09-29 Industry). Event starts need close D ≥ $2.
- Control: ready-NO stock-days on the same date in the same price-quintile × ATR%(20d)-quintile × prior-1d-return-decile cell (per-date bins, as scored). Residual = event return minus cell control mean. The 95% CI is clustered by date.
- Window: entries 2025-01-01..2026-06-30. Price warm-up from 2024-09-01; exits may use bars up to 2026-08-15.
- **PASS per row = BH (q=0.05, across these 7) significant AND mean residual < 0 AND 95% CI high < 0.** Judged once. Any other result = FAIL.
- Run: `PRELOCK_YEARS=2025,2026 python3 state_test/prelock/prelock_ohlcv7.py`. The script hard-fails if PRELOCK_YEARS is unset, if it is set to 2025/26 before 2026-10-23 15:00 UTC, or if a year has no NB chunks. If 2025-26 prices live in a different file, pass PRICE=/DIVS= and record their sha256 here before scoring. Nothing else may change.

## Hashes (sha256)
- Scorer state_test/prelock/prelock_ohlcv7.py: 3945339fb081f5d073d971e8c3f31e91d00a44eccb6f0fa8d53d9ee5bae199cc. Never run on data; only the PRELOCK_YEARS-unset hard fail was exercised.
- Price /workspace/pricehist/universe_2020_survivors.parquet: fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337
- Dividends /workspace/pricehist/dividends_2020.parquet: 9dde58ae9b9e2e701399989f05ec2853d4ba91c5fcf4c1e331730592824a5ff1
- Fund filter /workspace/snap_2026-09-29.csv: 4431eb257d99259602b25be61d11e801efde886e752ad8468fe76f91e26df5ae
- NB chunks 2020-24 (60 `202[0-4]__NB__*` parquet + json, sorted, concatenated): d859bb1bb20c38925e7577417ef6b07f79806becf1af208a244e42bab27784d4
- NB chunks 2025-26: **not posted** (none in /workspace/data/nb_v2/chunks). They must come from the same NB v2 builder. Record their sha here before scoring.
- Six-bucket map engine/universe/six_bucket_map.csv: f10a31036aa158d43ac27ed83d895091adac43ab9ae9211a2705ebfe63b6d382 (recorded for the lock; the scorer does not use it)
- Overlap script state_test/ohlcv/overlap.py: 85dce6a2af8557465a8f3453a32c4afd447d53d605c134d2ab71a2a78b1c655a. Table prelock/ohlcv7_overlap_2020_24.csv: 43f94157a18c515951d6736ccd658420c1e8f414476678dd283c823eb2d150c3

## Overlap, 2020–24 only (no return scoring)
Cell = % of the ROW's event starts (close ≥ $2) with a COLUMN event start for the same ticker within ±2 sessions. Warning spike = top-bull fifth (lean ≥ 0.6205) + stock-own QW jump z ≥ 1.5 (v5 states).

|                       | VOLJUMP_RV10_60>2   | RVOL>=5   | UP10_DAY   | NB026_T1THR   | NB029_P5POSQ   | GAPDOWN<=-5%   | MFI>80   | WARNSPIKE_L5_QWz>=1.5   |   n_event_starts |
|:----------------------|:--------------------|:----------|:-----------|:--------------|:---------------|:---------------|:---------|:------------------------|-----------------:|
| VOLJUMP_RV10_60>2     | —                   | 48.9      | 44.9       | 44.5          | 34.4           | 41.7           | 22.8     | 15.8                    |             9070 |
| RVOL>=5               | 9.0                 | —         | 36.1       | 34.8          | 16.5           | 27.1           | 31.0     | 14.6                    |            51587 |
| UP10_DAY              | 5.5                 | 23.9      | —          | 77.1          | 15.2           | 25.3           | 22.7     | 15.6                    |            81628 |
| NB026_T1THR           | 6.3                 | 27.3      | 92.1       | —             | 17.9           | 28.5           | 26.0     | 16.9                    |            67548 |
| NB029_P5POSQ          | 22.4                | 58.2      | 78.5       | 78.5          | —              | 48.9           | 35.7     | 17.8                    |            13613 |
| GAPDOWN<=-5%          | 5.3                 | 18.7      | 28.3       | 25.9          | 9.7            | —              | 10.6     | 4.8                     |            76424 |
| MFI>80                | 2.8                 | 20.8      | 23.0       | 22.2          | 6.8            | 10.5           | —        | 14.4                    |            74650 |
| WARNSPIKE_L5_QWz>=1.5 | 3.8                 | 19.2      | 31.7       | 28.8          | 6.7            | 9.3            | 28.3     | —                       |            38405 |

Read: UP10_DAY and NB-026 T1-THR are largely the same event (92% of NB-026 events have a +10% day nearby, and 77% the other way). NB-029 sits mostly inside UP10/NB-026 (78%) and RVOL≥5 (58%). Every row overlaps the warning spike by only 5–18%, so these are mostly separate from the existing locked row.

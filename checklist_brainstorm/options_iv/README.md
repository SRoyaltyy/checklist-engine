# Options IV checklist rows (GK-OPX), 2020-2024 — v2 rebuild after box wipe (2026-10-22 HKT)
Source: DoltHub post-no-preference/options, table volatility_history (free, public SQL API). Raw pulled 2026-10-22 into raw/vol_history_YYYY.csv (values untouched; window YYYY-1-12-15..YYYY-12-31).
2025-26 NOT built (sealed until Fri 23 Oct 23:00 HKT lock). build_year.py asserts 2020<=y<=2024.

## Point-in-time rule (known before 09:25 ET)
A DoltHub row dated D (EOD, committed ~02:35 ET next day) is usable for the 09:25 ET decision of the first NYSE session strictly after D.
For session S take the latest D < S per ticker. lag = sessions between S and first session after D.
lag 0 = fresh (stale=0); lag 1-2 = carried (stale=1); lag>2 -> all NOT_READY; no reading -> lag=99, all NR.
2020..~Oct-2024 DoltHub is Mon/Wed/Fri, so many sessions are stale=1. survivor_only=true (repo created 2021-04-20; earlier rows are a backfill, not PIT membership).

## Definitions (identical to v1)
- GK-OPX-IVR-HI: IV rank = (iv_current-iv_year_low)/(iv_year_high-iv_year_low) >= 0.80 (NR if high<=low)
- GK-OPX-IVR-LO: IV rank <= 0.20
- GK-OPX-IVHV-HI: iv_current/hv_current > 1.3
- GK-OPX-IVHV-LO: iv_current/hv_current < 0.8
- GK-OPX-IVCHG-UP: iv_current / iv_current of ticker's prior DoltHub reading (<=7 cal days earlier) - 1 >= +0.15
- GK-OPX-IVCHG-DN: same change <= -0.15

## Layout
out/YYYY/YYYY__OPT__<Sector>.parquet: ticker, date, packed(2 bytes), stale, lag. Codes 0=NR 1=NO 2=YES, 2-bit, id k at bits 2*(k%4) of byte k//4 (id order above).
Universe/sectors = New Bot 2024 survivor set as recorded in v1 2020 chunks (5,423 tickers, 12 sectors).
Not rebuilt: COUNTS2_OPT outcome-count files (need price history; not in scope / pricehist only has backup_parts).

## Check vs surviving v1 (prior/opt_2020_v1.tar, opt_2021_v1.tar from Drive)
Same 1,372,019 / 1,366,596 cells. packed match 99.68% (2020) / 99.94% (2021).
2020 diffs: 3,647 of 4,421 on 2020-01-06..08 (v1 had a reading before 2020-01-06; DoltHub today returns none before 2020-01-06). Rest ~4 cells/day scattered, likely upstream row revisions. v1 kept for reference; not overwritten.

## sha256: see SHA256SUMS.txt
bc7cb074ab76f49615f209f24e64750dbb1b5e531c3e6bf29272f99036270dd3  opt_2020_v2.tar
50ca946cb2860e95c1ac3ae0ff14a0feba6fa0a4bf249a44b6a13b279117f15d  opt_2021_v2.tar
ed4b97649a544862c6bd3397d039d2ef6deeb1c19666619a9188b5d542e5d306  opt_2022_v2.tar
c0021bb2416f353a78ed151bf397a4718f5dc29c5ffc419bd742d3ba585d49eb  opt_2023_v2.tar
507f226035b596a53b20217bcf76384baaddcf6f9b17ce20df814e79c2077a21  opt_2024_v2.tar
dbba26521e544d724232210151b55cf7edcb8c46fab2ab4ad5662fcd26f159c1  vol_history_2020.csv
155a5e0eef93f87fa1cd4c5a8b8afe53079db45314adcc66849d31b07ae77c95  vol_history_2021.csv
c6d91d9b101af4d500d6290df79586a1adc80ea8745daa898784c5875f5b42c1  vol_history_2022.csv
4b8453b8fa3fc2e6b8f1a67b4fa283dbb761e0c83d2264a8b6f24def12ea89e8  vol_history_2023.csv
be19771ca666a0f3800d7c6b2d7437c264dc4a5795acfd80cfd476c11af01d73  vol_history_2024.csv
d3337de04314530c6a3c6034f4b869e2ad8d92f8893d980bfadccc2954753b4c  vol_history_2020.csv.gz
f2249eb9f61a15834bfbf7c48ab9d1fa7d105d45cdf5af9d38675ae5e8e8e457  vol_history_2021.csv.gz
ea344b219d1b54473c006b43506a5ec35b8b6d5b19184a28cd9b53793a51521e  vol_history_2022.csv.gz
7dc2c9aed29a00f360385304745e10fe506a4e32d66ebf1f7e62aafda1d20389  vol_history_2023.csv.gz
2e5044a7cf84ea1ad4eb7d6c6e41c1dc85bfa69b2913c5522df32587d7079a5c  vol_history_2024.csv.gz
d593e536593ad7b6adfaa4ffe0bea4f4f4bc8b625fd51206b90bb30f6c18e2ba  src/build_year.py
427df20ae59ad3818c2f2eb39c7420004dcc8301e6a78022ad306901f7c51197  src/fetch_raw.py
0698e82cfb54833c9ac5d6ffa8f1ff870363b3eb1a6e125364a1452046089bd9  prior/opt_2020_v1.tar
034ab2da490985216d065234c500c71b93d139196b1a88153c1618ef1a37880a  prior/opt_2021_v1.tar

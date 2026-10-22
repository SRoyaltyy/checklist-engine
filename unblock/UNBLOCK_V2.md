# UNBLOCK_V2 — wave-2 pre-registration (written before any wave-2 result)
Registered 2026-10-23 ~03:20 HKT. Owner: Trading Bot Taskforce. Follows UNBLOCK_V1.md (wave 1, 0/99 pass).
Scope: the 48 BUILDABLE_NOT_BUILT rows of unblock_coverage_v2.csv + the market-cap versions of PV-TF-452/455/458 (FND-NB-001 and SUP-NB-004 are already among the 48).

## Method: identical to wave 1
Population: story_q panel 2020-01-01..2024-12-31 minus drop_list_v2, 21 forward bars, survivors only (2,408,833 stock-days). Exit A EXIT_RULE_V1 (+20% / day-15 close), Exit B 10-day hold, 0.6% round trip. Excess vs same-date mean; 500x date-clustered bootstrap; two-sided p. Only the YES bucket. Periods 2020-22 and 2023-24.
PASS (per exit) = win > 55% AND n >= 30 AND BH q < 0.05 AND excess > 0, in BOTH periods; feature passes if either exit passes.
Date-level features (same value for every stock on a date: CPI/NFP day, CFTC) have excess 0 by construction; p set to 1, cannot pass (as wave 1).
**Test-count base:** 13,764 (room count) + 396 wave-1 p-values (99 features x 2 exits x 2 periods) = 14,160 prior tests. BH computed conservatively: wave-2 p-values ranked among themselves with family size n = 14,160 + wave-2 count (equivalent to every prior test having p = 1; strictest possible).
Point in time: every input dated strictly before D (details per row). Only 2020-24 rows are scored; no fact/file dated or filed after 2024-12-31 is kept.

## Data
- FINRA Reg SHO daily short volume, consolidated (CNMSshvolYYYYMMDD.txt, cdn.finra.org), 2019-09..2024-12. File for day t usable from D = t+1.
- SEC XBRL companyfacts (data.sec.gov), us-gaap facts with filed <= 2024-12-31; a fact is usable on D if filed <= D-1.
- SEC shares outstanding: New Bot nb_tags_v2 sec_shares_out_filed_le_2024.parquet (Drive 1VnJMB0eoB2jGWw-z5KeIix1_0rNyiXO4). Cleaning: values <= 0, > 1e11, or > 50x the ticker's median are set missing. Usable if filed <= D-1.
- SEC submissions (data.sec.gov): 8-K item codes, NT 10-K/10-Q form types (filingDate <= D-1, <= 2024-12-31), and the company SIC code.
- BLS release archives (bls.gov/bls/news-release/cpi.htm, empsit.htm): release dates read from the archived file names.
- CFTC Traders in Financial Futures, futures only (fut_fin_txt_YYYY.zip), 2016-2024.
- Sector ETFs from pricehist/etf_2015.parquet (<= 2024).

Caveats fixed in advance: (1) market cap = SEC shares x close(D-1); closes are split-adjusted to the pull date, so names that split after D get understated market cap. (2) SIC code is today's SIC (not point-in-time); sector = fixed SIC-range map to the 11 SPDRs below. (3) "unplanned" departure cannot be told apart in fixed labels; any 8-K item 5.02 counts.

## SIC -> SPDR map (first match wins)
XLV 2830-2836, 3841-3851, 8000-8099, 5047, 5122 | XLP 2000-2199, 2840-2844, 5140-5149, 5400-5499, 5912 | XLE 1300-1399, 2900-2999, 4610-4619 | XLU 4900-4949 | XLRE 6500-6599, 6798 | XLF 6000-6499, 6700-6797, 6799 | XLC 4800-4899, 2710-2799, 7810-7899 | XLK 3570-3579, 3600-3629, 3640-3699, 3825-3829, 7370-7379 | XLY 2200-2399, 2500-2599, 3630-3639, 3710-3716, 3940-3949, 5200-5999, 7000-7299, 7500-7599, 7900-7999, 8200-8299 | XLB 1000-1499, 2600-2699, 2800-2829, 2850-2899, 3200-3399 | XLI 1500-1799, 3400-3569, 3580-3599, 3700-3799, 3800-3824, 4000-4599, 4700-4799, 5000-5099, 7380-7389, 8700-8748. Else NO_DATA. Cyclical = XLY, XLI, XLF, XLB.

## Features (YES tested)
| feature | id | YES if |
|---|---|---|
| CPI_DAY | CAL-JA-004 | D is a BLS CPI release date |
| NFP_DAY | CAL-JA-005 | D is a BLS Employment Situation release date |
| CFTC_ES_LEVSHORT | MKT-JA-060 | latest released TFF report (report Tuesday + 3 days <= D-1): E-mini S&P 500 leveraged-funds net (long - short) <= 10th pct of its last 156 reports |
| SECT_TOP3 / SECT_BOT3 | SEC-JA-021/022 | stock's sector SPDR ranks top 3 / bottom 3 of 11 by 20-session return at close D-1 (XLC/XLRE ranked only when they have data) |
| SECT_RANK_UP5 | SEC-JA-023 | rank improved >= 5 places vs 20 sessions earlier |
| CYC_DEF_UP | SEC-JA-024 | (XLY+XLI+XLF)/(XLP+XLU+XLV) 20-session change > +3% AND stock is cyclical |
| SECT_LOWCORR | SEC-JA-033 | 60-session corr(stock ret, sector SPDR ret) < 0.3 |
| YTD_VS_SECT20 | PRC-TR-003 | stock YTD - sector SPDR YTD > 20 pts (YTD vs prior year last close; 2021+) |
| SVR1_HI / SVR1_LO / SVR1_JUMP | PV-TF-430/431/432 | SVR1 >= 0.6 / <= 0.3 / SVR1 - SVR60 >= 0.1 |
| SVR5_HI / SVR5_LO / SVR5_JUMP | PV-TF-433/434/435 | same with 5 FINRA days |
| SVR20_HI / SVR20_LO / SVR20_JUMP | PV-TF-436/437/438 | same with 20 FINRA days |
| SVR5_TOPDEC | PV-TF-439 | SVR5 >= 90th pct of its own last 252 SVR5 values (>=120 needed) |
| PRICEUP_SVRUP | PV-TF-440 | close(D-1)/close(D-6) > 1 AND SVR5 - SVR5 five FINRA days earlier >= 0.1 |
| (SVRk = sum short volume / sum total volume over the last k FINRA files dated <= D-1) |||
| MICROCAP | FND-NB-001 | SEC shares x close(D-1) < $300M |
| SHARES_UP20 | SUP-NB-004 | latest shares / shares with end 300-430 days earlier >= 1.2, excluding ratios within 2% of 2,3,4,5,10 (split-like) |
| INS_SELL_1PCT_5/30/90 | PV-TF-452/455/458 | Form 4 code S value (filed in last 5/30/90 calendar days) >= 1% of market cap (10b5-1 flag not in DERA; not excluded) |
| CASH_RUNWAY4Q | EVT-NB-004 | latest operating cash flow < 0 and cash / (abs(OCF YTD) / (YTD days/91)) < 4 |
| EVT_502 | EVT-NB-009 | 8-K with item 5.02 filed in last 7 calendar days |
| EVT_NT_401 | EVT-NB-010 | NT 10-K or NT 10-Q, or 8-K item 4.01, filed in last 7 calendar days |
| EVT_301 | EVT-NB-011 | 8-K item 3.01 filed in last 7 calendar days |
| UNPROFITABLE | FND-NB-004 | latest annual (350-380 day) NetIncomeLoss < 0 (redefined: last fiscal year, not TTM) |
| REV_YOY30 | FND-NB-005 | latest quarterly (80-100 day) revenue / same quarter a year earlier - 1 >= 30% |
| EY3 | FND-TR-003 | latest annual NetIncomeLoss / market cap >= 0.03 |
| PS_TOP5 | FND-TR-004 | market cap / latest annual revenue in top 5% of rows with data that date |
| PFCF_BAD | FND-TR-006 | annual FCF (OCF - capex) <= 0, or mcap / FCF > 100 |
| SALES_QQ20 | FND-TR-009 | latest quarterly revenue / previous quarter - 1 > 20% |
| OPM_NEG | FND-TR-012 | annual OperatingIncomeLoss / annual revenue < 0 |
| ROE20 | FND-TR-013 | annual NetIncomeLoss / latest StockholdersEquity > 20% (equity > 0) |
| DE2 | FND-TR-014 | Liabilities / StockholdersEquity > 2, or equity <= 0 (redefined: total liabilities, no debt tag) |
| CR_LT1 | FND-TR-015 | AssetsCurrent / LiabilitiesCurrent < 1 |
Revenue = Revenues, else RevenueFromContractWithCustomerExcludingAssessedTax, else SalesRevenueNet. "Latest" = latest period end among facts filed <= D-1 (latest filing wins on ties).

## Not attempted in wave 2 (stay open)
CAL-JA-038 (Treasury refunding dates), MKT-JA-059 (NAAIM: no downloadable history found), CAP-NB-001/003 (split dates/announcements), SUP-NB-009 (de-SPAC list), BRW-NB-005 (Reg SHO threshold archives), REL-NB-007/008 (fixed name lists + overnight futures), PV-TF-462..465 (13F). If a source above fails to download, that row is reported open with the reason; nothing is redefined after results.

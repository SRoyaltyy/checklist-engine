# UNBLOCK_V1 — pre-registration (written before any results)
Registered 2026-10-23 ~02:40 HKT, before any feature was joined to outcomes. Owner: Trading Bot Taskforce.
Scope: the 272 "Taskforce (free-data source check)" master ideas + 13 "fails 09:25 ET" ideas + 11 earnings ideas + 1 10-year-history idea from Grok Bot's coverage_audit_v1 (master_coverage.csv, Drive 1wGJORBFa-pm5Uj8ZHnbOpqgMnfQJAMLo).
Per-idea verdicts (BUILT_TESTED / BUILDABLE_NOT_BUILT / BLOCKED / FAILS_0925 / TESTED_EARLIER) are in `unblock_coverage_v1.csv` (committed with this file).

## Data (all free, all dated <= 2024-12-31; 2025-26 never loaded)
- FRED fredgraph CSV: DGS10, DGS2, DGS30, DFII10, T10Y2Y, T10Y3M, T10YIE, DFEDTARU, DCOILWTICO, DTWEXBGS, NFCI (New Bot's /workspace/data/fred) + RRPONTSYD, WALCL, WTREGEN, STLFSI4 (new pull, cut at 2024-12-31).
- Yahoo daily close (yfinance, cut 2024-12-31): GC=F, HG=F, JPY=X, HYG, IEF, TLT, ^GSPC (1990+), ^SKEW. SPY from pricehist/etf_2015.parquet.
- Stock OHLCV: pricehist/universe_2020_survivors.parquet (<=2024). 10y monthly closes: history10y Stooq file.
- Earnings: New Bot Nasdaq calendar 2020-24 (Drive tar 1iE6J8sJlGWJLIYKY7iDTyJQ8hrrA5bjr). All 2020-24 rows are time-not-supplied, so anything needing BMO/AMC stays BLOCKED.
- Insider: SEC DERA Form 345 (data/edgar_form4/dera_2020_24 only). Dividends: pricehist/dividends_2020.parquet.

## Point-in-time
Decision day D, entry at open of D. Every input uses observations dated strictly before D, with these extra lags: DTWEXBGS 7 calendar days, NFCI 6, STLFSI4 7, WALCL/WTREGEN 2, DCOILWTICO 2 (New Bot rule). Form 4: filing_date <= D-1. Earnings: a report is "known" from report_date+1 session (timing unknown); scheduled dates count as known in advance (caveat: Nasdaq historical calendar shows final dates, so pre-announcement date moves are invisible).

## Population and method (identical to history10y/h10_run.py)
Every buyable stock-day in story_q panel 2020-01-01..2024-12-31 after drop_list_v2, with 21 forward bars. SURVIVORS ONLY.
Exits: A = EXIT_RULE_V1 (+20% target, no stop, close of day 15); B = 10-day hold close. 30bp fees each way (0.6% round trip).
Excess = trade return minus same-date mean of the population. Date-clustered bootstrap (500), two-sided p.
Only the YES bucket of each feature is tested (the idea's claim). Periods 2020-22 and 2023-24 separately.
BH-FDR across this run's p-values PLUS all prior p-values (exit grid, score, stacks, trajectory, history10y; prior family = 6,802).
PASS (per exit) = win > 55% AND n >= 30 AND BH q < 0.05 AND excess > 0, in BOTH periods.

## Features (yes/no; YES tested). Market-level features apply to every stock that day.
| feature | master id | YES if |
|---|---|---|
| DGS10_SMA20 | MAC-JA-003 | DGS10 last >= SMA20 + 0.15 |
| DGS10_HI252 | MAC-JA-004 | DGS10 last >= max of last 252 obs |
| DGS2_SMA20 / DGS2_HI252 | MAC-JA-007/008 | same on DGS2 |
| DGS30_SMA20 / DGS30_HI252 | MAC-JA-011/012 | same on DGS30 |
| DFII10_SMA20 / DFII10_HI252 | MAC-JA-015/016 | same on DFII10 |
| C2s10_INV | MAC-JA-019 | T10Y2Y < 0 |
| C2s10_BULLSTEEP | MAC-JA-020 | T10Y2Y 5-obs change >= +0.15 and DGS2 5-obs change < 0 |
| C2s10_BEARSTEEP | MAC-JA-021 | T10Y2Y 5-obs change >= +0.15 and DGS10 5-obs change > 0 |
| C2s10_UNINV | MAC-JA-022 | T10Y2Y crossed <0 to >=0 within last 20 obs |
| C3m10_INV/BULLSTEEP/BEARSTEEP/UNINV | MAC-JA-023..026 | same on T10Y3M |
| USD_UP / USD_LO252 | MAC-JA-029/030 | DTWEXBGS (proxy for DXY) > SMA50 and SMA50 5-obs slope > 0 / at 252-obs low |
| JPY_UP / JPY_LO252 | MAC-JA-033/034 | same on JPY=X |
| WTI_UP / WTI_LO252 | MAC-JA-037/038 | same on DCOILWTICO |
| GOLD_UP / GOLD_LO252 | MAC-JA-041/042 | same on GC=F |
| COPPER_UP / COPPER_LO252 | MAC-JA-045/046 | same on HG=F |
| CUAU_20D | MAC-JA-048 | HG/GC ratio 20-day change > +5% |
| SPX_TLT_CORR | MAC-JA-049 | 60d corr(^GSPC ret, TLT ret) > 0.3 |
| HYG_IEF | MAC-JA-059 | HYG/IEF > its SMA20 |
| NFCI_POS | MAC-JA-061 | latest NFCI > 0 |
| STLFSI_JUMP | MAC-JA-062 | STLFSI4 week-over-week rise >= 0.5 |
| NETLIQ_UP | MAC-JA-063 | WALCL - WTREGEN - 1000*RRPONTSYD, 4-week change > 0 |
| RRP_DROP | MAC-JA-064 | RRPONTSYD fell >= 10% over 20 obs (base >= 1bn) |
| CUT_90D | MAC-JA-084 | DFEDTARU decreased within past 90 calendar days |
| BE10_RISE | MAC-JA-085 | T10YIE rose >= 0.20 over 20 obs |
| SKEW_150 | MKT-JA-014 | ^SKEW > 150 |
| SPY_GT200 | MKT-JA-029 | SPY close > SMA200 |
| SPY_GOLDEN | MKT-JA-030 | SPY SMA50 > SMA200 |
| SPY_DD10 | MKT-JA-031 | SPY >= 10% below 252d high |
| BREADTH200_60 | MKT-JA-043 | > 60% of survivor universe above own SMA200 (redefined: not S&P 500) |
| OPEX_DAY | CAL-JA-006 | D is 3rd Friday |
| OPEX_WEEK | CAL-JA-007 | D is Mon-Thu of 3rd-Friday week |
| POST_OPEX_WEEK | CAL-JA-008 | D in the week after the 3rd-Friday week |
| QUAD_WITCH | CAL-JA-009 | 3rd Friday of Mar/Jun/Sep/Dec |
| VIX_EXP | CAL-JA-010 | Wednesday 30 calendar days before next month's 3rd Friday (shift to prior session if holiday) |
| PRE_HOLIDAY | CAL-JA-020 | next weekday is not a trading day |
| POST_HOLIDAY | CAL-JA-021 | previous weekday was not a trading day |
| HALF_DAY | CAL-JA-022 | NYSE early close (day after Thanksgiving, Jul 3 / Dec 24 when trading; 2020-12-24, 2021-11-26, 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2020-11-27) |
| SANTA | CAL-JA-026 | last 5 sessions of Dec or first 2 of Jan |
| SEPT | CAL-JA-027 | month = 9 |
| NOV_APR | CAL-JA-028 | month in 11,12,1,2,3,4 |
| TAXLOSS | CAL-JA-030 | Dec 1-20 and stock YTD return (vs prior-year last close) < -30% (2021+) |
| TAXLOSS_REV | CAL-JA-031 | first 5 sessions of Jan and prior-year return < -30% (2021+) |
| EARN_PEAK_WEEK | CAL-JA-032 | Nasdaq calendar count of reports in D's Mon-Fri week >= 1,500 (redefined: whole calendar, not S&P) |
| EARN_TOMORROW | CAL-JA-033 | stock's report_date is the next session |
| PEAD | CAL-JA-035 | report_date within the 5 sessions before D-1, surprise > +10%, close(report+1)/close(report-1) > 1, report+1 <= D-1 |
| ELECTION | CAL-JA-037 | 2020-11-03, 2022-11-08, 2024-11-05 |
| EX_DIV | CAL-JA-039 | D is an ex-dividend date for the stock |
| JACKSON_HOLE | CAL-JA-043 | 2020-08-27, 2021-08-27, 2022-08-26, 2023-08-25, 2024-08-23 |
| BUYBACK_BLACKOUT | CAL-JA-044 | stock's next report_date is 1-20 sessions ahead |
| DOY_SEAS | CAL-JA-045 | mean ^GSPC return on this calendar day-of-year (MM-DD) over prior 30 years > +0.1% |
| OWN_SEAS | CAL-JA-046 + HST-NB-004 | stock's avg return in this calendar month over prior 10 years (Stooq, years < D's year) > +2% and positive in >= 7 of 10 |
| POST_CUT_1_4 | CAL-JA-047 | 1-4 sessions after an FOMC cut statement day (redefined from 0-4: day 0 is announced at 14:00, after the open) |
| EARN_TODAY | EVT-TR-001 | report_date == D |
| EARN_WITHIN5 | ERN-NB-003 | next report_date within 1-5 sessions |
| EPS_BEAT10 | ERN-NB-004 | latest known report (report+1 <= D-1, within 60 sessions) surprise > +10% |
| EARN_GAP_FADE | ERN-NB-009 | within last 10 sessions: session after report_date opened >= +5% vs prior close and closed below its open |
| EARN_BIG_MOVER | ERN-NB-010 | mean abs 2-day report move over up to 4 prior reports (>=2 needed) >= 10% |
| AVWAP_EARN | STR-NB-007 | close(D-1) > daily volume-weighted typical price since last report_date (within 60 sessions; daily-bar proxy for VWAP) |
| PERF_W30 | PRC-TR-001 | 5-session return > +30% |
| PERF_M_N30 | PRC-TR-002 | 21-session return < -30% |
| VOLW_2X | PRC-TR-004 | stdev of last 5 daily returns > 2 x stdev of last 21 |
| ATR8 | PRC-TR-005 | ATR14 / close > 8% |
| BETA2 | PRC-TR-006 | 252-session beta vs SPY > 2 |
| CFO_N5 | PRC-TR-008 | D-1 close/open - 1 <= -5% |
| RSI80 / RSI20 | TEC-TR-003/004 | Wilder RSI14 > 80 / < 20 |
| NEAR_52WH / NEAR_52WL | TEC-TR-005/006 | close >= 0.98 x 252-session high / <= 1.02 x 252-session low |
| ADX25_UP | PV-TF-262 | ADX14 > 25 and +DI > -DI |
| PENNY | FND-NB-002 | close(D-1) < $5 |
| HIGH_PRICE | FND-NB-003 | close(D-1) > $500 |
| BETA_BREAK | REL-NB-003 | abs(corr20 - corr120) vs SPY >= 0.4 |
| NEW_LISTING | SUP-NB-008 | first bar in universe within last 180 calendar days and after 2020-03-01 (proxy for IPO age) |
| EXDIV_1PCT | CAP-NB-004 | ex-date today and amount / close(D-1) >= 1% |
| SPECIAL_DIV | CAP-NB-005 | ex-date today and amount / close(D-1) >= 3% |
| DIV_CUT | CAP-NB-006 | ex-date today and amount < 0.95 x the previous ex amount |
| INS_P_5/30/90 | PV-TF-450/453/456 | any non-derivative Form 4 code P (non-amendment) filed in last 5/30/90 calendar days |
| INS_CLUSTER_5/30/90 | PV-TF-451/454/457 | >= 3 distinct reporting owners with code P in that window |
| INS_SELL_5/30/90 | PV-TF-452/455/458 | code S value sum >= $1M in that window (redefined: $ not % of mkt cap; 10b5-1 flag not available) |
| INS_OFFICER_P30 | PV-TF-459 | code P by an officer in last 30 days (redefined: DERA gives officer flag, not CEO/CFO title) |
| INS_P_AFTER_DROP | PV-TF-460 | INS_P_30 and 20-session return <= -15% |
| INS_P_BELOW50 | PV-TF-461 | INS_P_5 and close < SMA50 |

Early-2020 rows lacking the look-back are NO_DATA and not tested. Nothing else is tested in this run. Fails-09:25 ideas are only reclassified here (redefinition proposals in the coverage csv), not tested.

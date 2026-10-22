# Taskforce reader: validation (2026-10-22)
Test set: 20 tickers (GME CELH NAUT AAPL MSFT NVDA TSLA JPM XOM KO PFE AMZN META INTC F BA WMT AMD PLTR COIN) × 5 dates
(2008-06-16, 2016-08-01, 2021-01-27, 2024-05-15, 2026-10-21) = 100 runs × 51,859 row ids. All ids are accounted for: 8,309 PV-TFC + 224 PV-TFX + 43,326 PV-TF, with none missing and no extras.

| | YES | NO | NOT_READY |
|---|---|---|---|
| All 100 runs | 9.9% | 56.7% | 33.5% |
| 91 runs where the stock was trading (9 pre-listing runs excluded) | 10.9% | 62.3% | 26.9% |
| Full PV-TF (listed) | 9.2% | 63.4% | 27.4% |
| Compact PV-TFC (listed) | 19.1% | 55.9% | 25.0% |
| Timeframe PV-TFX (listed) | 21.5% | 77.2% | 1.3% |

NOT_READY reasons (listed runs): needs_cross_section_universe (rank vs sector/market) 65%, source_not_wired 16%, not_implemented 14%, insufficient_history 3%, not_applicable 1%.
Pre-listing runs are all NOT_READY with reason no_yahoo_history/no_history_before_date: COIN ×3, META 2008, NAUT ×2, PLTR ×2, TSLA 2008.

Checks: (1) cutting the raw data at D-1 (AAPL 2024-05-15) gives a byte-identical CSV; (2) a rerun gives a byte-identical CSV; (3) 20 hand-checked answers (10 random + 10 random YES) all match, see handcheck.txt.
Twins (1.72M computable pairs): same-trigger pairs are equal 109,606/109,606. Exclusive pairs: 460,685 opposite and 1,134,871 both NO. Both NO is the neutral band between the two thresholds (e.g. RSI 20–80), so a strict "always opposite" can't hold under the current definitions.
Both-YES on full rows happened only from two sheet defects: Price-volume rank level (YES X>=1 / BUT X<=4, always both true) and Ichimoku cloud level (>=0 / <=0, both true inside the cloud, X=0).
Compact rows are an OR over timeframes, so their twins can both be YES on different N (17,741 cases).
Coverage by data type: coverage_by_type.csv.

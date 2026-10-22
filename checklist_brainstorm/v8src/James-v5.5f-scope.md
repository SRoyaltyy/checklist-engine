# James v5.5f row scope (2026-10-22)
Source: James-v5.5f.csv (7,780 rows, unchanged). Reader: engine/readers/james.py (unchanged).
Scope comes from mirroring answer()'s dispatch for each row (weekday, calendar/held, slow-meta, resolve() symbol, stock+SPDR sector_eval, stock "BUT" clause).

| scope | rows | key |
|---|---|---|
| SHARED | 6570 | date |
| SECTOR | 434 | date + SPDR sector ETF (from the Finviz/theme-radar sector map) |
| PER_STOCK | 776 | date + ticker |

- Code inspection moved 668 rows: any market-series row whose definition has a "BUT stock's own prior-session return ... volume" clause goes to PER_STOCK.
- Rows that always return NOT_READY before reaching the stock (calendar/macro held = 118, source gaps such as Stockcharts/FedWatch/constituents = 540) are counted as SHARED.
- Empirical check: ran answer() for AAPL, MSFT, JPM and XOM on 2026-09-15 and 2026-10-16, plus ALLT (small-cap tech) on 2026-10-16. That is 9 runs and 70,020 answers. The check found 0 mismatches. Every SHARED row gave the same answer and reason across tickers, and every SECTOR row matched within XLK (AAPL/MSFT/ALLT). The check moved 0 rows. 145 PER_STOCK rows did vary across tickers.
- Timing (XOM, one stock-day, warm cache, 25.9 s total): SHARED rows took 78%, SECTOR 7.5% and PER_STOCK 14.6%. If SHARED rows are answered once per day and SECTOR rows once per ETF per day, each extra stock costs about 3.8 s instead of 25.9 s. That saves about 85% of James's compute at universe scale.

## data_need
OHLCV_ONLY 1390, CALENDAR 23, OTHER_DATED 6367. data_source names the source.
- 5,399 of the OTHER_DATED rows are other free daily price series: Treasury yields via FRED/Treasury, futures (CL/GC/HG), DXY, BTC/ETH (Coinbase), HYG/QQQ/IWM/RSP/SMH/EEM, ^MOVE/^OVX and foreign indexes. They go back to 2020 and are only "other" under the strict SPY/sector/VIX definition.
- The rest of OTHER_DATED: Stockcharts breadth 392, intraday/pre-open indications 255, CME FedWatch 75, constituent/membership history 92, macro values from BLS CPI/ISM/Fed targets, CME/CBOE stats, and Finviz market cap/sector (3 rows).
- Caveat: every SECTOR row and every stock-vs-sector row uses the Finviz sector map from theme-radar universe(D). That map exists only from 2026-08 onward, so before then spdr_for returns NOT_READY. Going back to 2020 needs a static or historical sector map.

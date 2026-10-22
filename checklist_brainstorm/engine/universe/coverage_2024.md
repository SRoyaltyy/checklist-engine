# Source coverage 2024 (master.csv, 819 questions)
Cells = 2024 engine cells (shared tier per date; stock tier per ticker-day; TR per ticker-day x N). Answered = YES or NO; the rest are NOT_READY/NR. in_engine = id present in the 2024 chunks.

## Focus on the engine's own question set (merged_draft_v8.2, 21409 ids; buckets by regex on source + data_type; a row can be in several buckets)
| bucket                  |   questions |   in_engine |   q_with_any_answer |      cells |   answered |   answered_share |
|:------------------------|------------:|------------:|--------------------:|-----------:|-----------:|-----------------:|
| options (chains/OI/IV)  |         266 |         220 |                 220 |  324684360 |  226063398 |           0.6963 |
| put/call                |          20 |           0 |                   0 |          0 |          0 |         nan      |
| short volume (Reg SHO)  |          20 |           0 |                   0 |          0 |          0 |         nan      |
| short interest / borrow |         134 |           0 |                   0 |          0 |          0 |         nan      |
| insider (Form 4)        |          54 |           0 |                   0 |          0 |          0 |         nan      |
| Finviz (any)            |        4577 |        1824 |                 528 | 6533438832 | 5622995744 |           0.8606 |

Note: master.csv has 819 ids and only 105 of them are in v8.2/the engine; its options, short, insider and Finviz ids are all absent (table below).

## master.csv focus: options / put-call / short volume / insider / Finviz (matched on source, data_type, variant)
| source                                                                         | data_type          |   questions |   in_engine |   q_with_any_answer |   cells |   answered |   answered_share |
|:-------------------------------------------------------------------------------|:-------------------|------------:|------------:|--------------------:|--------:|-----------:|-----------------:|
| Benzinga/Finviz ratings                                                        | Analyst            |           1 |           0 |                   0 |       0 |          0 |              nan |
| CBOE                                                                           | Market sentiment   |           1 |           0 |                   0 |       0 |          0 |              nan |
| CBOE                                                                           | Market-wide        |           4 |           0 |                   0 |       0 |          0 |              nan |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Relative strength  |          10 |           0 |                   0 |       0 |          0 |              nan |
| DoltHub post-no-preference/options (free)                                      | Options            |          11 |           0 |                   0 |       0 |          0 |              nan |
| FINRA Reg SHO CNMSshvol daily (free)                                           | Short volume       |          11 |           0 |                   0 |       0 |          0 |              nan |
| FINRA short interest                                                           | Short interest     |           2 |           0 |                   0 |       0 |          0 |              nan |
| FINRA short interest / Finviz v=131 snapshot                                   | Short interest     |           3 |           0 |                   0 |       0 |          0 |              nan |
| FRED + Finviz                                                                  | Credit             |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz                                                                         | Industry group     |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz Target Price                                                            | Analyst            |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz groups                                                                  | Industry group     |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | 52w range          |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Analyst            |           4 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Balance sheet      |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Change from open   |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Earnings           |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Float              |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Gap                |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Growth             |           5 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Industry           |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Moving averages    |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Oscillator         |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Ownership          |           3 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Pattern            |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Performance        |           3 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Profitability      |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Sector             |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Short interest     |           3 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Valuation          |           6 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Volatility         |           3 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot)                            | Volume             |           2 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot) + theme-radar              | Theme              |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot) + theme-radar composite    | Theme              |           1 |           0 |                   0 |       0 |          0 |              nan |
| Finviz screener export (theme-radar daily snapshot) + theme-radar themes       | Theme              |           1 |           0 |                   0 |       0 |          0 |              nan |
| IBKR shortable file                                                            | Securities lending |           1 |           0 |                   0 |       0 |          0 |              nan |
| Options OI estimate                                                            | Market-wide        |           1 |           0 |                   0 |       0 |          0 |              nan |
| Options chain                                                                  | Market-wide        |           1 |           0 |                   0 |       0 |          0 |              nan |
| PAID — flagged, not bought                                                     | Options            |           1 |           0 |                   0 |       0 |          0 |              nan |
| Premarket quote (Yahoo/Finviz) for pre-open trial; daily O for pre-close trial | Gap                |           8 |           0 |                   0 |       0 |          0 |              nan |
| SEC 13F data sets (free)                                                       | 13F                |           4 |           0 |                   0 |       0 |          0 |              nan |
| SEC Form 3/4/5 data sets + EDGAR acceptance time (free)                        | Insider            |          12 |           0 |                   0 |       0 |          0 |              nan |
| Yahoo chains archived by data_snapshots_daily (free)                           | Options            |           7 |           0 |                   0 |       0 |          0 |              nan |
| Yahoo/Finviz analyst recommendation counts                                     | Analyst            |           1 |           0 |                   0 |       0 |          0 |              nan |

## By source
| source                                                                         |   questions |   in_engine |   q_with_any_answer |          cells |   answered |   answered_share |
|:-------------------------------------------------------------------------------|------------:|------------:|--------------------:|---------------:|-----------:|-----------------:|
| 10-Q cover / XBRL                                                              |           1 |           0 |                   0 |    0           |          0 |         nan      |
| 10-Q/10-K/S-1                                                                  |           1 |           0 |                   0 |    0           |          0 |         nan      |
| 10-Q/8-K                                                                       |           1 |           0 |                   0 |    0           |          0 |         nan      |
| 8-K / exchange notices                                                         |           1 |           0 |                   0 |    0           |          0 |         nan      |
| 8-K/merger arb                                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| AAII                                                                           |           2 |           0 |                   0 |    0           |          0 |         nan      |
| AAII survey                                                                    |           2 |           0 |                   0 |    0           |          0 |         nan      |
| AH + PM quotes                                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| AH quotes                                                                      |           1 |           0 |                   0 |    0           |          0 |         nan      |
| AH quotes (Polygon)                                                            |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Agency release + consensus calendar                                            |           8 |           0 |                   0 |    0           |          0 |         nan      |
| Asia index                                                                     |           3 |           3 |                   2 |  756           |        504 |           0.6667 |
| BLS/BEA + consensus calendar                                                   |           8 |           0 |                   0 |    0           |          0 |         nan      |
| Benzinga ratings                                                               |           2 |           0 |                   0 |    0           |          0 |         nan      |
| Benzinga/Finviz ratings                                                        |           1 |           0 |                   0 |    0           |          0 |         nan      |
| BiopharmCatalyst/FDA                                                           |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Bloomberg/Citi                                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| CBOE                                                                           |          19 |          12 |                   4 | 3024           |       1008 |           0.3333 |
| CBOE + OHLC                                                                    |           2 |           2 |                   0 |  504           |          0 |           0      |
| CFE                                                                            |           1 |           1 |                   0 |  252           |          0 |           0      |
| CFTC COT                                                                       |           1 |           0 |                   0 |    0           |          0 |         nan      |
| CL futures / DCOILWTICO                                                        |           4 |           2 |                   1 |  504           |        252 |           0.5    |
| CME                                                                            |           8 |           7 |                   0 | 1764           |          0 |           0      |
| CME + OHLC                                                                     |           2 |           2 |                   0 |  504           |          0 |           0      |
| CME + daily OHLC                                                               |           1 |           1 |                   0 |  252           |          0 |           0      |
| CME FedWatch                                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| CME futures                                                                    |           2 |           1 |                   0 |  252           |          0 |           0      |
| CNN                                                                            |           4 |           0 |                   0 |    0           |          0 |         nan      |
| Consensus                                                                      |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Constituent OHLC                                                               |           9 |           8 |                   0 | 2016           |          0 |           0      |
| Crypto exchanges                                                               |           4 |           4 |                   1 | 1008           |        252 |           0.25   |
| Crypto spot                                                                    |           1 |           0 |                   0 |    0           |          0 |         nan      |
| DXY / DX futures                                                               |           4 |           2 |                   1 |  504           |        252 |           0.5    |
| Daily OHLC                                                                     |          30 |          12 |                   0 |    3.54171e+07 |          0 |           0      |
| Daily OHLC (Yahoo/Stooq)                                                       |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 |         366 |           0 |                   0 |    0           |          0 |         nan      |
| Daily close                                                                    |           3 |           0 |                   0 |    0           |          0 |         nan      |
| Daily close + Nasdaq rule 5550                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Dividend calendar                                                              |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Dividend feed                                                                  |           2 |           0 |                   0 |    0           |          0 |         nan      |
| DoltHub post-no-preference/options (free)                                      |          11 |           0 |                   0 |    0           |          0 |         nan      |
| EDGAR                                                                          |           2 |           0 |                   0 |    0           |          0 |         nan      |
| EDGAR 424B / PR                                                                |           1 |           0 |                   0 |    0           |          0 |         nan      |
| EDGAR 424B5                                                                    |           1 |           0 |                   0 |    0           |          0 |         nan      |
| EDGAR 8-K                                                                      |           1 |           0 |                   0 |    0           |          0 |         nan      |
| EDGAR S-3/424B                                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| ETF holdings (ETFdb/issuers)                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| ETF issuer data                                                                |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Earnings calendar                                                              |           2 |           0 |                   0 |    0           |          0 |         nan      |
| Earnings calendar + AH quotes                                                  |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Earnings results                                                               |           2 |           0 |                   0 |    0           |          0 |         nan      |
| Eurex/CME                                                                      |           1 |           1 |                   0 |  252           |          0 |           0      |
| Eurex/STOXX                                                                    |           2 |           2 |                   0 |  504           |          0 |           0      |
| Excel avoid_AH flag + theme-radar                                              |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FDA calendar                                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FINRA Reg SHO CNMSshvol daily (free)                                           |          11 |           0 |                   0 |    0           |          0 |         nan      |
| FINRA short interest                                                           |           2 |           0 |                   0 |    0           |          0 |         nan      |
| FINRA short interest / Finviz v=131 snapshot                                   |           3 |           0 |                   0 |    0           |          0 |         nan      |
| FRED                                                                           |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FRED + Finviz                                                                  |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FRED + daily OHLC                                                              |           1 |           1 |                   0 |  252           |          0 |           0      |
| FRED BAMLC0A0CM                                                                |           3 |           0 |                   0 |    0           |          0 |         nan      |
| FRED BAMLH0A0HYM2                                                              |           3 |           0 |                   0 |    0           |          0 |         nan      |
| FRED BAMLH0A3HYC                                                               |           3 |           0 |                   0 |    0           |          0 |         nan      |
| FRED DFII10                                                                    |           3 |           1 |                   1 |  252           |        252 |           1      |
| FRED DGS10                                                                     |           3 |           1 |                   1 |  252           |        252 |           1      |
| FRED DGS2                                                                      |           3 |           1 |                   1 |  252           |        252 |           1      |
| FRED DGS30                                                                     |           3 |           1 |                   1 |  252           |        252 |           1      |
| FRED NFCI                                                                      |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FRED RRPONTSYD                                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FRED STLFSI4                                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FRED T10Y2Y                                                                    |           4 |           0 |                   0 |    0           |          0 |         nan      |
| FRED T10Y3M                                                                    |           4 |           0 |                   0 |    0           |          0 |         nan      |
| FRED T10YIE                                                                    |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FTSE Russell prelim lists                                                      |           1 |           0 |                   0 |    0           |          0 |         nan      |
| FX                                                                             |           4 |           2 |                   1 |  504           |        252 |           0.5    |
| Fed                                                                            |           2 |           0 |                   0 |    0           |          0 |         nan      |
| Fed calendar + futures                                                         |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Finviz                                                                         |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Finviz Target Price                                                            |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Finviz groups                                                                  |           2 |           0 |                   0 |    0           |          0 |         nan      |
| Finviz screener export (theme-radar daily snapshot)                            |          47 |           0 |                   0 |    0           |          0 |         nan      |
| Finviz screener export (theme-radar daily snapshot) + theme-radar              |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Finviz screener export (theme-radar daily snapshot) + theme-radar composite    |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Finviz screener export (theme-radar daily snapshot) + theme-radar themes       |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Float data                                                                     |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Float history                                                                  |           1 |           0 |                   0 |    0           |          0 |         nan      |
| GC futures                                                                     |           4 |           2 |                   1 |  504           |        252 |           0.5    |
| HG futures                                                                     |           4 |           2 |                   1 |  504           |        252 |           0.5    |
| HKEX                                                                           |           1 |           1 |                   0 |  252           |          0 |           0      |
| IBKR SLB / Ortex / iBorrowDesk                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| IBKR shortable file                                                            |           1 |           0 |                   0 |    0           |          0 |         nan      |
| IPO dates                                                                      |           1 |           0 |                   0 |    0           |          0 |         nan      |
| IR                                                                             |           1 |           0 |                   0 |    0           |          0 |         nan      |
| IR calendars                                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Index calendars                                                                |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Index data                                                                     |           1 |           1 |                   0 |  252           |          0 |           0      |
| Intraday 1m bars                                                               |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Intraday bars                                                                  |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Intraday bars + earnings dates                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Issuer shares-outstanding daily                                                |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Issuer sites                                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Local exchange + FX                                                            |           1 |           0 |                   0 |    0           |          0 |         nan      |
| NAAIM                                                                          |           1 |           0 |                   0 |    0           |          0 |         nan      |
| NYSE                                                                           |          11 |          11 |                   0 | 2772           |          0 |           0      |
| NYSE/Fed/BLS/S&P/earnings calendar                                             |          45 |          13 |                   3 | 3276           |        756 |           0.2308 |
| Nasdaq/NYSE halt feed                                                          |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Nasdaq/NYSE threshold lists                                                    |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Nasdaq/Polygon splits                                                          |           1 |           0 |                   0 |    0           |          0 |         nan      |
| OHLC                                                                           |          19 |           8 |                   8 | 2016           |       2016 |           1      |
| OHLC + industry map                                                            |           1 |           0 |                   0 |    0           |          0 |         nan      |
| OHLC+dates                                                                     |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Options OI estimate                                                            |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Options chain                                                                  |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Ortex/S3                                                                       |           1 |           0 |                   0 |    0           |          0 |         nan      |
| PAID — flagged, not bought                                                     |           1 |           0 |                   0 |    0           |          0 |         nan      |
| PR                                                                             |           1 |           0 |                   0 |    0           |          0 |         nan      |
| PR/transcripts                                                                 |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Pre-market quotes                                                              |           3 |           0 |                   0 |    0           |          0 |         nan      |
| Pre-market quotes (Polygon/Webull/IBKR)                                        |           8 |           0 |                   0 |    0           |          0 |         nan      |
| Pre-market quotes (Polygon/Webull/IBKR) + float                                |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Premarket quote (Yahoo/Finviz) for pre-open trial; daily O for pre-close trial |           8 |           0 |                   0 |    0           |          0 |         nan      |
| Press releases / splits feed                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Press releases/8-K                                                             |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Prices x shares                                                                |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Ratings feed                                                                   |           1 |           0 |                   0 |    0           |          0 |         nan      |
| S&P/FTSE Russell                                                               |           1 |           0 |                   0 |    0           |          0 |         nan      |
| SEC 13F data sets (free)                                                       |           4 |           0 |                   0 |    0           |          0 |         nan      |
| SEC FTD (free, UA header)                                                      |           4 |           0 |                   0 |    0           |          0 |         nan      |
| SEC Form 3/4/5 data sets + EDGAR acceptance time (free)                        |          12 |           0 |                   0 |    0           |          0 |         nan      |
| SPAC trackers                                                                  |           1 |           0 |                   0 |    0           |          0 |         nan      |
| XBRL                                                                           |           3 |           0 |                   0 |    0           |          0 |         nan      |
| Yahoo chains archived by data_snapshots_daily (free)                           |           7 |           0 |                   0 |    0           |          0 |         nan      |
| Yahoo/Finviz analyst recommendation counts                                     |           1 |           0 |                   0 |    0           |          0 |         nan      |
| Yahoo/Zacks                                                                    |           1 |           0 |                   0 |    0           |          0 |         nan      |
| iBorrowDesk                                                                    |           1 |           0 |                   0 |    0           |          0 |         nan      |
| theme-radar composite_rank                                                     |           1 |           0 |                   0 |    0           |          0 |         nan      |
| theme-radar score_delta                                                        |           1 |           0 |                   0 |    0           |          0 |         nan      |

## By source x data_type
| source                                                                         | data_type                |   questions |   in_engine |   q_with_any_answer |          cells |   answered |   answered_share |   NR_share |
|:-------------------------------------------------------------------------------|:-------------------------|------------:|------------:|--------------------:|---------------:|-----------:|-----------------:|-----------:|
| 10-Q cover / XBRL                                                              | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| 10-Q/10-K/S-1                                                                  | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| 10-Q/8-K                                                                       | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| 8-K / exchange notices                                                         | Corporate action         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| 8-K/merger arb                                                                 | Corporate event          |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| AAII                                                                           | Market-wide              |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| AAII survey                                                                    | Market sentiment         |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| AH + PM quotes                                                                 | After-hours              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| AH quotes                                                                      | After-hours              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| AH quotes (Polygon)                                                            | After-hours              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Agency release + consensus calendar                                            | Macro surprise           |           8 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Asia index                                                                     | Market-wide              |           3 |           3 |                   2 |  756           |        504 |           0.6667 |     0.3333 |
| BLS/BEA + consensus calendar                                                   | Macro surprise           |           8 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Benzinga ratings                                                               | Analyst                  |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Benzinga/Finviz ratings                                                        | Analyst                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| BiopharmCatalyst/FDA                                                           | Biotech catalyst         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Bloomberg/Citi                                                                 | Macro surprise           |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| CBOE                                                                           | Market sentiment         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| CBOE                                                                           | Market-wide              |          18 |          12 |                   4 | 3024           |       1008 |           0.3333 |     0.6667 |
| CBOE + OHLC                                                                    | Market-wide              |           2 |           2 |                   0 |  504           |          0 |           0      |     1      |
| CFE                                                                            | Market-wide              |           1 |           1 |                   0 |  252           |          0 |           0      |     1      |
| CFTC COT                                                                       | Market-wide              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| CL futures / DCOILWTICO                                                        | Cross-asset              |           4 |           2 |                   1 |  504           |        252 |           0.5    |     0.5    |
| CME                                                                            | Cross-asset              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| CME                                                                            | Market-wide              |           7 |           7 |                   0 | 1764           |          0 |           0      |     1      |
| CME + OHLC                                                                     | Market-wide              |           2 |           2 |                   0 |  504           |          0 |           0      |     1      |
| CME + daily OHLC                                                               | Cross-asset              |           1 |           1 |                   0 |  252           |          0 |           0      |     1      |
| CME FedWatch                                                                   | Fed                      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| CME futures                                                                    | Commodity proxy          |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| CME futures                                                                    | Rates                    |           1 |           1 |                   0 |  252           |          0 |           0      |     1      |
| CNN                                                                            | Market sentiment         |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| CNN                                                                            | Market-wide              |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Consensus                                                                      | Analyst                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Constituent OHLC                                                               | Market-wide              |           4 |           3 |                   0 |  756           |          0 |           0      |     1      |
| Constituent OHLC                                                               | Sector breadth           |           5 |           5 |                   0 | 1260           |          0 |           0      |     1      |
| Crypto exchanges                                                               | Market-wide              |           4 |           4 |                   1 | 1008           |        252 |           0.25   |     0.75   |
| Crypto spot                                                                    | Crypto proxy             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| DXY / DX futures                                                               | Cross-asset              |           4 |           2 |                   1 |  504           |        252 |           0.5    |     0.5    |
| Daily OHLC                                                                     | Calendar                 |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC                                                                     | Credit                   |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC                                                                     | Cross-asset              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC                                                                     | Moving averages          |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC                                                                     | Overbought/oversold      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC                                                                     | Prior-day structure      |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC                                                                     | Rotation                 |           7 |           3 |                   0 |    8.85427e+06 |          0 |           0      |     1      |
| Daily OHLC                                                                     | Sector correlation       |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC                                                                     | Sector divergence        |           2 |           2 |                   0 |    5.90285e+06 |          0 |           0      |     1      |
| Daily OHLC                                                                     | Sector relative strength |          11 |           6 |                   0 |    1.77085e+07 |          0 |           0      |     1      |
| Daily OHLC                                                                     | Sector volatility        |           1 |           1 |                   0 |    2.95142e+06 |          0 |           0      |     1      |
| Daily OHLC (Yahoo/Stooq)                                                       | Candlestick              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | 52w hi/lo                |          36 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Bollinger/volatility     |          21 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Candlestick              |          81 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Gap                      |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Money flow               |          19 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Moving averages          |          55 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Overbought/oversold      |          52 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Price return             |          28 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Relative strength        |          35 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Trend strength           |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily OHLC (Yahoo/Stooq, free)                                                 | Volume                   |          36 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily close                                                                    | Price bucket             |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily close                                                                    | Prior-day structure      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Daily close + Nasdaq rule 5550                                                 | Prior-day structure      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Dividend calendar                                                              | Corporate action         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Dividend feed                                                                  | Corporate action         |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| DoltHub post-no-preference/options (free)                                      | Options                  |          11 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| EDGAR                                                                          | Corporate event          |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| EDGAR 424B / PR                                                                | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| EDGAR 424B5                                                                    | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| EDGAR 8-K                                                                      | Corporate event          |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| EDGAR S-3/424B                                                                 | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| ETF holdings (ETFdb/issuers)                                                   | ETF ownership            |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| ETF issuer data                                                                | Sector flows             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Earnings calendar                                                              | Earnings                 |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Earnings calendar + AH quotes                                                  | Industry group           |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Earnings results                                                               | Earnings                 |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Eurex/CME                                                                      | Market-wide              |           1 |           1 |                   0 |  252           |          0 |           0      |     1      |
| Eurex/STOXX                                                                    | Market-wide              |           2 |           2 |                   0 |  504           |          0 |           0      |     1      |
| Excel avoid_AH flag + theme-radar                                              | Theme                    |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FDA calendar                                                                   | Biotech catalyst         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FINRA Reg SHO CNMSshvol daily (free)                                           | Short volume             |          11 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FINRA short interest                                                           | Short interest           |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FINRA short interest / Finviz v=131 snapshot                                   | Short interest           |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED                                                                           | Liquidity                |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED + Finviz                                                                  | Credit                   |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED + daily OHLC                                                              | Rates                    |           1 |           1 |                   0 |  252           |          0 |           0      |     1      |
| FRED BAMLC0A0CM                                                                | Credit                   |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED BAMLH0A0HYM2                                                              | Credit                   |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED BAMLH0A3HYC                                                               | Credit                   |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED DFII10                                                                    | Rates                    |           3 |           1 |                   1 |  252           |        252 |           1      |     0      |
| FRED DGS10                                                                     | Rates                    |           3 |           1 |                   1 |  252           |        252 |           1      |     0      |
| FRED DGS2                                                                      | Rates                    |           3 |           1 |                   1 |  252           |        252 |           1      |     0      |
| FRED DGS30                                                                     | Rates                    |           3 |           1 |                   1 |  252           |        252 |           1      |     0      |
| FRED NFCI                                                                      | Financial conditions     |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED RRPONTSYD                                                                 | Liquidity                |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED STLFSI4                                                                   | Financial conditions     |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED T10Y2Y                                                                    | Yield curve              |           4 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED T10Y3M                                                                    | Yield curve              |           4 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FRED T10YIE                                                                    | Inflation expectations   |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FTSE Russell prelim lists                                                      | Index membership         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| FX                                                                             | Cross-asset              |           4 |           2 |                   1 |  504           |        252 |           0.5    |     0.5    |
| Fed                                                                            | Calendar                 |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Fed                                                                            | Fed                      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Fed calendar + futures                                                         | Fed                      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz                                                                         | Industry group           |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz Target Price                                                            | Analyst                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz groups                                                                  | Industry group           |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | 52w range                |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Analyst                  |           4 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Balance sheet            |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Change from open         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Earnings                 |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Float                    |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Gap                      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Growth                   |           5 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Industry                 |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Moving averages          |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Oscillator               |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Ownership                |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Pattern                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Performance              |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Profitability            |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Sector                   |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Short interest           |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Valuation                |           6 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Volatility               |           3 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot)                            | Volume                   |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot) + theme-radar              | Theme                    |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot) + theme-radar composite    | Theme                    |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Finviz screener export (theme-radar daily snapshot) + theme-radar themes       | Theme                    |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Float data                                                                     | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Float history                                                                  | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| GC futures                                                                     | Cross-asset              |           4 |           2 |                   1 |  504           |        252 |           0.5    |     0.5    |
| HG futures                                                                     | Cross-asset              |           4 |           2 |                   1 |  504           |        252 |           0.5    |     0.5    |
| HKEX                                                                           | Market-wide              |           1 |           1 |                   0 |  252           |          0 |           0      |     1      |
| IBKR SLB / Ortex / iBorrowDesk                                                 | Securities lending       |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| IBKR shortable file                                                            | Securities lending       |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| IPO dates                                                                      | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| IR                                                                             | Corporate event          |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| IR calendars                                                                   | Corporate event          |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Index calendars                                                                | Index membership         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Index data                                                                     | Market-wide              |           1 |           1 |                   0 |  252           |          0 |           0      |     1      |
| Intraday 1m bars                                                               | Prior-day structure      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Intraday bars                                                                  | Prior-day structure      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Intraday bars + earnings dates                                                 | Prior-day structure      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Issuer shares-outstanding daily                                                | ETF flows                |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Issuer sites                                                                   | ETF flows                |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Local exchange + FX                                                            | ADR / dual listing       |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| NAAIM                                                                          | Market-wide              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| NYSE                                                                           | Market-wide              |          11 |          11 |                   0 | 2772           |          0 |           0      |     1      |
| NYSE/Fed/BLS/S&P/earnings calendar                                             | Calendar                 |          45 |          13 |                   3 | 3276           |        756 |           0.2308 |     0.7692 |
| Nasdaq/NYSE halt feed                                                          | Prior-day structure      |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Nasdaq/NYSE threshold lists                                                    | Securities lending       |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Nasdaq/Polygon splits                                                          | Corporate action         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| OHLC                                                                           | Correlation              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| OHLC                                                                           | Earnings                 |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| OHLC                                                                           | Market-wide              |          11 |           8 |                   8 | 2016           |       2016 |           1      |     0      |
| OHLC                                                                           | Own history              |           5 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| OHLC                                                                           | Relative strength        |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| OHLC + industry map                                                            | Correlation              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| OHLC+dates                                                                     | Earnings                 |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Options OI estimate                                                            | Market-wide              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Options chain                                                                  | Market-wide              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Ortex/S3                                                                       | Securities lending       |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| PAID — flagged, not bought                                                     | Options                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| PR                                                                             | Earnings                 |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| PR/transcripts                                                                 | Earnings                 |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Pre-market quotes                                                              | Market-wide              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Pre-market quotes                                                              | Sector gap               |           2 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Pre-market quotes (Polygon/Webull/IBKR)                                        | Pre-market               |           8 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Pre-market quotes (Polygon/Webull/IBKR) + float                                | Pre-market               |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Premarket quote (Yahoo/Finviz) for pre-open trial; daily O for pre-close trial | Gap                      |           8 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Press releases / splits feed                                                   | Corporate action         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Press releases/8-K                                                             | Corporate action         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Prices x shares                                                                | Size bucket              |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Ratings feed                                                                   | Analyst                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| S&P/FTSE Russell                                                               | Index membership         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| SEC 13F data sets (free)                                                       | 13F                      |           4 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| SEC FTD (free, UA header)                                                      | FTD                      |           4 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| SEC Form 3/4/5 data sets + EDGAR acceptance time (free)                        | Insider                  |          12 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| SPAC trackers                                                                  | Share supply             |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| XBRL                                                                           | Biotech catalyst         |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| XBRL                                                                           | Profitability            |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| XBRL                                                                           | Revenue                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Yahoo chains archived by data_snapshots_daily (free)                           | Options                  |           7 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Yahoo/Finviz analyst recommendation counts                                     | Analyst                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| Yahoo/Zacks                                                                    | Analyst                  |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| iBorrowDesk                                                                    | Securities lending       |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| theme-radar composite_rank                                                     | Theme                    |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |
| theme-radar score_delta                                                        | Theme                    |           1 |           0 |                   0 |    0           |          0 |         nan      |   nan      |

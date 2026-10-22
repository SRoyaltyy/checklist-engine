import yfinance as yf,pandas as pd
T="AAPL MSFT AMZN GOOGL META NVDA TSLA JPM V JNJ WMT PG MA UNH HD XOM CVX BAC KO PEP ABBV MRK PFE COST AVGO ADBE CSCO CRM NFLX INTC AMD ORCL QCOM TXN IBM CAT BA GE HON MMM DIS NKE MCD SBUX T VZ GS MS LLY AMGN SPY QQQ IWM XLK XLF XLE XLV XLY XLP XLI XLB XLU ^VIX HYG TLT GC=F CL=F DX-Y.NYB".split()
d=yf.download(T,start='2018-01-01',end='2026-01-01',auto_adjust=True,group_by='ticker',progress=False,threads=True)
d.to_pickle('bars.pkl');print(d.shape, d.columns.levels[0].size)

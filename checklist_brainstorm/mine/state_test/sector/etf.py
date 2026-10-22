import yfinance as yf, pandas as pd
E=['XLK','XLF','XLV','XLE','XLI','XLY','XLP','XLU','XLB','XLRE','XLC','SPY']
d=yf.download(E,start='2019-01-01',end='2025-01-01',auto_adjust=True,progress=False)['Close']
assert d.index.max()<pd.Timestamp('2025-01-01'); d.index=d.index.strftime('%Y-%m-%d'); d.to_csv('etf_2019_24.csv'); print(d.shape,d.isna().sum().to_dict())

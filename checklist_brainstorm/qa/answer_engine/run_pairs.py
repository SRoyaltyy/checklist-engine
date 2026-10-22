import sys,csv,random; sys.path.insert(0,'/workspace/checklist_brainstorm/engine/readers'); import james
# fixed, seeded pair list (deterministic). kind: large/small/delisted/recent/holiday/market
P=[('AAPL','2015-03-10','large'),('MSFT','2016-11-09','large'),('JPM','2018-02-06','large'),('XOM','2020-03-17','large'),('NVDA','2023-05-25','large'),
('TSLA','2021-01-04','large'),('AMZN','2019-07-05','holiday(after Jul4)'),('KO','2017-11-24','holiday(Black Fri half-day)'),('PG','2022-12-27','holiday(after Xmas)'),('WMT','2024-01-02','holiday(after NY)'),
('CELH','2019-06-12','small'),('PLUG','2020-08-14','small'),('FIZZ','2016-05-04','small'),('SDEV','2025-04-03','small'),('GLND','2026-09-15','small'),
('NAUT','2025-02-20','small'),('PACB','2024-10-15','small'),('QSI','2023-09-08','small'),('BBBY','2022-08-17','delisted'),('SIVB','2023-03-08','delisted'),
('AAPL','2026-10-21','recent'),('MSFT','2026-10-22','recent(today)'),('CELH','2026-10-20','recent'),('AMD','2026-10-01','recent'),('SPY','2026-07-02','holiday(pre Jul3 half-day)'),
('SPY','2015-08-24','market'),('SPY','2018-12-24','market'),('SPY','2020-03-16','market'),('SPY','2022-06-13','market'),('SPY','2025-04-07','market')]
import os;start=os.environ.get('START');W=csv.writer(open('james_v55e_results.csv','a' if start else 'w',newline=''))
if not start: W.writerow(['row_id','ticker','date','pair_kind','answer','reason','data_as_of'])
if start: P=P[[p[0]+p[1] for p in P].index(start):]
for t,d,k in P:
    for r in james.answer(t,d): W.writerow([r['row_id'],t,d,k,r['answer'],r['reason'],r['data_as_of']])
    print(t,d,flush=True)

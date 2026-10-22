import json,csv,os,time,datetime as dt,io,re
from curl_cffi import requests as R
OUT='/workspace/checklist_brainstorm/fetch_tests'
res=[]
NH={'Accept':'application/json, text/plain, */*','Origin':'https://www.nasdaq.com','Referer':'https://www.nasdaq.com/'}
def get(key,url,method='GET',headers=None,data=None,parse=None,note=''):
    os.makedirs(f'{OUT}/{key}',exist_ok=True)
    st=None;rows=0;sample='';ok=False;err=''
    try:
        r=R.request(method,url,headers=headers,json=data,impersonate='chrome',timeout=40)
        st=r.status_code
        fn=re.sub(r'[^A-Za-z0-9]+','_',url[-80:])[:80]
        open(f'{OUT}/{key}/{fn}.raw','wb').write(r.content)
        if st!=200: err=f'HTTP {st}'
        else:
            rows,sample=parse(r) if parse else (len(r.content),r.text[:60])
            ok=rows>0
            if not ok: err='empty'
    except Exception as e: err=str(e)[:150]
    res.append(dict(key=key,url=url,note=note,http_status=st,rows=rows,sample_value=str(sample)[:120],passed='pass' if ok else 'fail',error=err))
    print(key,st,rows,str(sample)[:80],err,note,flush=True); time.sleep(0.7)
def ychart(r):
    j=r.json()['chart']['result'][0];t=j.get('timestamp',[]);q=j['indicators']['quote'][0]
    c=[x for x in q['close'] if x is not None]
    first=dt.datetime.utcfromtimestamp(t[0]).date() if t else ''
    ev=j.get('events',{})
    return len(t),f'first={first} last_close={c[-1] if c else None} events={ {k:len(v) for k,v in ev.items()} }'
Y='https://query1.finance.yahoo.com/v8/finance/chart/'
for s in ['AAPL','MSFT','TSLA','SPY']: get('yahoo_daily',Y+s+'?range=max&interval=1d&events=div,split',parse=ychart)
for s in ['AAPL','NVDA','SPY']: get('yahoo_1m_prepost',Y+s+'?range=5d&interval=1m&includePrePost=true',parse=ychart)
p1=int(dt.datetime(2026,10,15,4).timestamp());get('yahoo_1m_prepost',Y+f'AAPL?period1={p1}&period2={p1+86400}&interval=1m&includePrePost=true',parse=ychart,note='earliest 2026-10-15')
p1=int(dt.datetime(2026,9,1,4).timestamp());get('yahoo_1m_prepost',Y+f'AAPL?period1={p1}&period2={p1+86400}&interval=1m&includePrePost=true',parse=ychart,note='expect fail >30d')
get('yahoo_1h_futures',Y+'NG=F?range=730d&interval=1h',parse=ychart);get('yahoo_1h_futures',Y+'CL=F?range=60d&interval=1h',parse=ychart)
get('yahoo_home_fx',Y+'7203.T?range=max&interval=1d',parse=ychart);get('yahoo_home_fx',Y+'JPY=X?range=1mo&interval=1d',parse=ychart)
def nrows(path):
    def f(r):
        j=r.json();d=j.get('data') or {}
        for k in path: d=(d or {}).get(k) if isinstance(d,dict) else None
        d=d or []
        return len(d),(d[0] if d else '')
    return f
N='https://api.nasdaq.com/api/calendar/'
for d in ['2026-10-21','2025-10-30','2012-10-22','2012-10-19']: get('nasdaq_earnings',N+'earnings?date='+d,headers=NH,parse=nrows(['rows']),note=d)
for s in ['AAPL','JPM','NFLX']: get('nasdaq_earnings_surprise',f'https://api.nasdaq.com/api/company/{s}/earnings-surprise',headers=NH,parse=nrows(['earningsSurpriseTable','rows']))
for d in ['2026-10-21','2025-06-02','2016-03-15','2016-03-14','2015-03-16']: get('nasdaq_dividends',N+'dividends?date='+d,headers=NH,parse=nrows(['calendar','rows']),note=d)
for d in ['','?date=2026-10-21','?date=2020-08-31']: get('nasdaq_splits',N+'splits'+d,headers=NH,parse=nrows(['rows']),note=d)
for d in ['2026-09','2015-01','2010-06','2010-05']: get('nasdaq_ipo','https://api.nasdaq.com/api/ipo/calendar?date='+d,headers=NH,parse=nrows(['priced','rows']),note=d)
def fin(r):
    j=r.json();return len(j),(j[0] if j else '')
F='https://api.finra.org/data/group/otcMarket/name/weeklySummary'
for wk in ['2026-10-05','2025-06-02','2022-01-03']:
    get('finra_ats_weekly',F,'POST',headers={'Accept':'application/json'},data={'limit':5,'compareFilters':[{'compareType':'EQUAL','fieldName':'weekStartDate','fieldValue':wk},{'compareType':'EQUAL','fieldName':'issueSymbolIdentifier','fieldValue':'AAPL'}]},parse=fin,note=wk)
def sv(r):
    L=[l for l in r.text.splitlines() if l.startswith('AAPL|')];return len(r.text.splitlines()),(L[0] if L else 'no AAPL')
for f in ['FNRAshvol20261021','FNRAshvol20250102','FNRAshvol20100104','CNMSshvol20261021','CNMSshvol20100104']: get('finra_regsho_daily',f'https://cdn.finra.org/equity/regsho/daily/{f}.txt',parse=sv,note=f)
def rss(r): n=r.text.count('<item>');return n,(re.findall(r'<ndaq:IssueSymbol>(.*?)<',r.text)[:3])
for d in ['10202026','06022025','01022020']: get('nasdaqtrader_halts',f'https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts&haltdate={d}',parse=rss,note=d)
def txt(r): L=r.text.splitlines();return len(L)-1,(L[1] if len(L)>1 else '')
for d in ['20261021','20250102','20080102']: get('regsho_threshold',f'https://www.nasdaqtrader.com/dynamic/symdir/regsho/nasdaqth{d}.txt',parse=txt,note=d)
for d in ['20261021','20250102','20110228']: get('ssr_shorthalts',f'https://www.nasdaqtrader.com/dynamic/symdir/shorthalts/shorthalts{d}.txt',parse=txt,note=d)
def nyse(r): return r.text.count('Good Friday')+r.text.count('Thanksgiving'),'GoodFriday/Thanksgiving mentions'
get('nyse_holidays','https://www.nyse.com/markets/hours-calendars',parse=nyse)
def fv(r):
    m={k:re.search(k+r'</td>.*?<b>(.*?)</b>',r.text,re.S) for k in ['Shs Float','Shs Outstand']}
    ind=re.findall(r'f=ind_(\w+)',r.text)[:1]
    v={k:(x.group(1) if x else None) for k,x in m.items()};return (1 if all(v.values()) else 0),f'{v} ind={ind}'
for s in ['AAPL','TSLA','GME']: get('finviz_quote',f'https://finviz.com/quote.ashx?t={s}',parse=fv)
def ish(r): L=r.text.splitlines();return max(0,len(L)-10),(L[:2])
get('ishares_holdings','https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund',parse=ish)
get('ishares_holdings','https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund&asOfDate=20250102',parse=ish,note='historic asOfDate')
def xl(r):
    import pandas as pd;d=pd.read_excel(io.BytesIO(r.content),skiprows=4);return len(d),str(d.iloc[0].to_dict())
for e in ['xlk','xlf']: get('spdr_holdings',f'https://www.ssga.com/us/en/intermediary/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{e}.xlsx',parse=xl)
def cb(r): j=r.json();o=j['data']['options'];return len(o),o[0]
for s in ['AAPL','_SPX' if False else 'MSFT','TSLA']: get('cboe_options',f'https://cdn.cboe.com/api/global/delayed_quotes/options/{s}.json',parse=cb)
def stq(r): L=r.text.splitlines();return (len(L)-1 if L and L[0].startswith('Date') else 0),L[:2]
get('stooq_daily','https://stooq.com/q/d/l/?s=aapl.us&i=d',parse=stq)
json.dump(res,open(f'{OUT}/results.json','w'),indent=1,default=str)

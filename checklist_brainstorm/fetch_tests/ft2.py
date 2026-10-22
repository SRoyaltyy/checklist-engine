exec(open('ft.py').read().split("Y='https")[0])
Y='https://query1.finance.yahoo.com/v8/finance/chart/'
for s in ['AAPL','MSFT','SPY']: get('yahoo_daily',Y+s+'?period1=0&period2=1792000000&interval=1d&events=div,split',parse=ychart)
def sv(r):
    L=[l for l in r.text.splitlines() if l.startswith('AAPL|')];return (len(L)),(L[0] if L else 'no AAPL')
for f in ['CNMSshvol20261020','CNMSshvol20250102','CNMSshvol20100104','CNMSshvol20090803','FNSQshvol20261020','FNYXshvol20261020','FNQCshvol20261020','FNRAshvol20261020']: get('finra_regsho_daily',f'https://cdn.finra.org/equity/regsho/daily/{f}.txt',parse=sv,note=f)
def txt(r): L=[l for l in r.text.splitlines() if '|' in l];return len(L)-1,(L[1] if len(L)>1 else '')
get('regsho_threshold','https://www.nasdaqtrader.com/dynamic/symdir/regsho/nasdaqth20261020.txt',parse=txt,note='20261020')
def fv(r):
    t=re.sub(r'<[^>]+>',' ',r.text);v={k:(re.search(k+r'\s+([\d.]+[KMB])',t) or [None,None])[1] for k in ['Shs Float','Shs Outstand']}
    return (1 if all(v.values()) else 0),f'{v} ind={re.findall(r"f=ind_(\w+)",r.text)[:1]}'
for s in ['AAPL','TSLA','GME']: get('finviz_quote',f'https://finviz.com/quote.ashx?t={s}',parse=fv)
def fin(r):
    j=r.json();return len(j),(j[0] if j else "")
F="https://api.finra.org/data/group/otcMarket/name/weeklySummary"
for wk in ['2026-09-28','2026-09-21']:
    get('finra_ats_weekly',F,'POST',headers={'Accept':'application/json'},data={'limit':5,'compareFilters':[{'compareType':'EQUAL','fieldName':'weekStartDate','fieldValue':wk},{'compareType':'EQUAL','fieldName':'issueSymbolIdentifier','fieldValue':'AAPL'}]},parse=fin,note=wk)
def ish(r): L=r.text.splitlines();ok=any('Ticker' in l for l in L[:15]);return (len(L) if ok else 0),L[:3]
get('ishares_holdings','https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund',headers={'Accept':'text/csv,*/*','Referer':'https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf'},parse=ish)
get('ishares_holdings','https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf/1467271812596.ajax?fileType=csv&fileName=SOXX_holdings&dataType=fund',parse=ish)
json.dump(res,open(f'{OUT}/results2.json','w'),indent=1,default=str)

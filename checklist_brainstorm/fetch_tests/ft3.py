exec(open('ft.py').read().split("Y='https")[0])
def fin(r):
    j=r.json();return len(j),(j[0] if j else '')
F='https://api.finra.org/data/group/otcMarket/name/weeklySummary'
for wk in ['2026-09-28','2026-09-21','2026-10-12']:
    get('finra_ats_weekly',F,'POST',headers={'Accept':'application/json'},data={'limit':5,'compareFilters':[{'compareType':'EQUAL','fieldName':'weekStartDate','fieldValue':wk},{'compareType':'EQUAL','fieldName':'issueSymbolIdentifier','fieldValue':'AAPL'}]},parse=fin,note=wk)
def ish(r): L=r.text.splitlines();ok=any('Ticker' in l for l in L[:15]);return (len(L) if ok else 0),L[:3]
for u in ['https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund','https://www.ishares.com/us/products/239705/ishares-phlx-semiconductor-etf/1467271812596.ajax?fileType=csv&fileName=SOXX_holdings&dataType=fund']:
    get('ishares_holdings',u,headers={'Accept':'text/csv,*/*'},parse=ish)
def sv(r):
    L=[l for l in r.text.splitlines() if '|AAPL|' in l];return (len(L)),(L[0] if L else 'no AAPL')
for f in ['CNMSshvol20261020','CNMSshvol20250102','CNMSshvol20180801','FNSQshvol20100104','FNYXshvol20100104','FNRAshvol20100104']: get('finra_regsho_daily',f'https://cdn.finra.org/equity/regsho/daily/{f}.txt',parse=sv,note=f)
json.dump(res,open(f'{OUT}/results3.json','w'),indent=1,default=str)

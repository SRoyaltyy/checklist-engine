import csv,random,requests,json,io,time
random.seed(20261022)
H={'User-Agent':'Mozilla/5.0'}
J='../james_newroots/history/'
out=[]
def add(src,key,claim,live,url,ok,note=''):
    out.append(dict(source=src,key=key,james=claim,publisher=live,match='MATCH' if ok else 'MISMATCH',url=url,note=note));print(out[-1])
def samp(f,n=10): r=list(csv.DictReader(open(J+f)));return random.sample(r,n)
def get(u,**k):
    for i in range(3):
        try:
            x=requests.get(u,headers=H,timeout=40,**k);x.raise_for_status();return x
        except Exception as e: err=e;time.sleep(3)
    raise err
# SOFR
for r in samp('sofr.csv'):
    d=r['date'];u=f'https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate={d}&endDate={d}'
    try:
        a=get(u).json()['refRates'];v=a[0]['percentRate'] if a else None
        add('sofr',d,r['sofr_pct'],v,u,v is not None and abs(float(v)-float(r['sofr_pct']))<1e-9)
    except Exception as e: add('sofr',d,r['sofr_pct'],'ERR '+repr(e)[:80],u,False,'fetch error')
# RRP
for r in samp('onrrp.csv'):
    d=r['date'];u=f'https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json?startDate={d}&endDate={d}'
    try:
        ops=get(u).json()['repo']['operations'];v=sum(int(o.get('totalAmtAccepted',0)) for o in ops)
        add('onrrp',d,r['accepted_usd'],v,u,int(float(r['accepted_usd']))==v,f'{len(ops)} ops')
    except Exception as e: add('onrrp',d,r['accepted_usd'],'ERR '+repr(e)[:80],u,False,'fetch error')
# auctions vs TreasuryDirect
for r in samp('auctions.csv'):
    c=r['cusip'];u=f'https://www.treasurydirect.gov/TA_WS/securities/search?cusip={c}&format=json'
    try:
        a=[x for x in get(u).json() if (x.get('auctionDate') or x.get('competitiveAuctionCloseDate') or '')[:10]==r['auction_date']]
        if not a: add('auctions',c+' '+r['auction_date'],r['high_yield_or_rate'],'not found',u,False);continue
        x=a[0];cands=[x.get(k) for k in ('highYield','highInvestmentRate','highDiscountRate','highRate','highDiscountMargin','interestRate') if x.get(k)]
        ok=any(abs(float(v)-float(r['high_yield_or_rate']))<1e-6 for v in cands if v not in ('',None)) if r['high_yield_or_rate'] not in ('','null') else False
        add('auctions',c+' '+r['auction_date']+' '+r['term'],r['high_yield_or_rate'],'|'.join(map(str,cands)),u,ok,f"btc {r['bid_to_cover']} vs {x.get('bidToCoverRatio')}")
    except Exception as e: add('auctions',c,r['high_yield_or_rate'],'ERR '+repr(e)[:80],u,False,'fetch error')
# TGA
for r in samp('tga.csv'):
    d=r['record_date'];u=f'https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?filter=record_date:eq:{d}&page[size]=50'
    try:
        a=get(u).json()['data'];vals={x['account_type']:(x['close_today_bal'] if x['close_today_bal'] not in (None,'null') else x['open_today_bal']) for x in a}
        v=vals.get(r['account_type'])
        add('tga',d,r['tga_close_mn'],v,u,v not in (None,'null') and float(v)==float(r['tga_close_mn']),r['account_type'])
    except Exception as e: add('tga',d,r['tga_close_mn'],'ERR '+repr(e)[:80],u,False,'fetch error')
# curve
cache={}
for r in samp('ust_curve.csv'):
    y=r['date'][:4];u=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv'
    try:
        if y not in cache: cache[y]=list(csv.DictReader(io.StringIO(get(u).text)))
        m,dd,yy=r['date'][5:7],r['date'][8:10],y
        row=[x for x in cache[y] if x['Date']==f'{m}/{dd}/{yy}']
        if not row: add('ust_curve',r['date'],r['10y'],'date not found',u,False);continue
        x=row[0];pub={'2y':x.get('2 Yr'),'10y':x.get('10 Yr'),'3m':x.get('3 Mo'),'30y':x.get('30 Yr')}
        ok=all((r[k] in ('',None) and pub[k] in ('',None)) or (r[k] not in ('',None) and pub[k] not in ('',None) and abs(float(r[k])-float(pub[k]))<1e-9) for k in pub)
        add('ust_curve',r['date'],'/'.join(r[k] for k in pub),'/'.join(str(pub[k]) for k in pub),u,ok,'2y/10y/3m/30y')
    except Exception as e: add('ust_curve',r['date'],r['10y'],'ERR '+repr(e)[:80],u,False,'fetch error')
csv.DictWriter(open('truthcheck.csv','w'),fieldnames=out[0].keys()).writerows([dict(zip(out[0].keys(),out[0].keys()))]+out)

import csv,json,urllib.request,random,re,datetime as dt
UA={'User-Agent':'Mozilla/5.0 (research; cyrus)'}
def g(u):
    import time
    for i in range(4):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read().decode()
        except Exception:
            if i==3: raise
            time.sleep(5)
H=lambda k: list(csv.DictReader(open(f'history/{k}.csv')))
now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'); out=[]
random.seed(7)
def add(src,date,ours,theirs,url,note=''):
    ok=abs(float(ours)-float(theirs))<1e-6*max(1,abs(float(ours))) if theirs not in (None,'') else False
    out.append(dict(source=src,date=date,value=ours,check_value=theirs,match=ok,url=url,fetched_at=now,note=note))
for r in random.sample(H('sofr'),3):
    u=f"https://markets.newyorkfed.org/api/rates/all/search.json?startDate={r['date']}&endDate={r['date']}"
    t=[x for x in json.loads(g(u))['refRates'] if x['type']=='SOFR']; add('sofr',r['date'],r['sofr_pct'],t[0]['percentRate'] if t else '',u,'NY Fed rates/all endpoint')
for r in random.sample([x for x in H('onrrp') if x['date']>='2021'],3):
    u=f"https://markets.newyorkfed.org/api/rp/results/search.json?startDate={r['date']}&endDate={r['date']}"
    try:
        t=[x for x in json.loads(g(u))['repo']['operations'] if x.get('operationType')=='Reverse Repo']; add('onrrp',r['date'],r['accepted_usd'],t[0].get('totalAmtAccepted') if t else '',u,'NY Fed rp/all results endpoint')
    except Exception as e: add('onrrp',r['date'],r['accepted_usd'],'',u,f'err {e}')
for r in random.sample([x for x in H('auctions') if x['auction_date']>='2015'],3):
    u=f"https://www.treasurydirect.gov/TA_WS/securities/search?cusip={r['cusip']}&format=json"
    try:
        t=[x for x in json.loads(g(u)) if (x.get('auctionDate') or x['competitiveAuctionCloseDate'])[:10]==r['auction_date']]
        tv=(t[0].get('highYield') or t[0].get('highDiscountRate') or t[0].get('highRate') or t[0].get('highDiscountMargin')) if t else ''
        add('auctions',r['auction_date']+' '+r['term'],r['high_yield_or_rate'],tv,u,'TreasuryDirect TA_WS (separate system)')
    except Exception as e: add('auctions',r['auction_date'],r['high_yield_or_rate'],'',u,f'err {e}')
tg=H('tga'); idx={x['record_date']:i for i,x in enumerate(tg)}
for r in random.sample([x for x in tg if x['record_date']>='2022-01-01'][:-2],3):
    nxt=tg[idx[r['record_date']]+1]['record_date']
    u=f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?filter=record_date:eq:{nxt}"
    t=[x for x in json.loads(g(u))['data'] if x['account_type']=='Treasury General Account (TGA) Opening Balance']
    add('tga',r['record_date'],r['tga_close_mn'],t[0]['open_today_bal'] if t else '',u,f'next DTS ({nxt}) opening balance')
for r in random.sample([x for x in H('ust_curve') if x['date']>='2010'],3):
    ym=r['date'][:7].replace('-','')
    u=f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month={ym}"
    x=g(u); m=re.search(r'<d:NEW_DATE[^>]*>'+r['date']+r'T00:00:00</d:NEW_DATE>.*?<d:BC_10YEAR[^>]*>([\d.]+)<',x,re.S)
    add('ust_curve',r['date']+' 10y',r['10y'],m.group(1) if m else '',u,'Treasury XML feed')
w=csv.DictWriter(open('spotcheck.csv','w',newline=''),fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for o in out: print(o['source'],o['date'],o['value'],o['check_value'],o['match'],o['note'][:40])

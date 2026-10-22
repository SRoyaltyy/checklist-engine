#!/usr/bin/env python3
"""James new roots: SOFR, ON RRP, Treasury auctions, TGA, Treasury daily par yield curve.
Official documented APIs only, no keys.  Usage:
  fetch_newroots.py backfill        # full history -> raw/<src>_full.json|csv + history/<src>.csv
  fetch_newroots.py nightly [DATE]  # add-only: writes daily/<src>/<DATE>.json once; never overwrites;
                                    # data not posted yet => status not_ready (exit 0), not a failure.
"""
import sys,os,json,csv,datetime as dt,urllib.request,io,time
ROOT=os.path.dirname(os.path.abspath(__file__)); UA={'User-Agent':'Mozilla/5.0 (research; cyrus)'}
def get(u,tries=3):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=90).read()
        except Exception as e:
            if i==tries-1: raise
            time.sleep(5*(i+1))
now=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
FD='https://api.fiscaldata.treasury.gov/services/api/fiscal_service'
def fd_all(path,fields,filt,sort):
    out=[];n=1
    while True:
        u=f'{FD}{path}?fields={fields}&filter={filt}&sort={sort}&page%5Bsize%5D=10000&page%5Bnumber%5D={n}'
        j=json.loads(get(u)); out+=j['data']
        if n>=j['meta']['total-pages']: return out,u
        n+=1
SRC={
 'sofr':  dict(url=lambda a,b:f'https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate={a}&endDate={b}', start='2018-04-02'),
 'onrrp': dict(url=lambda a,b:f'https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json?startDate={a}&endDate={b}', start='2013-09-23'),
}
def rows_sofr(a,b):
    u=SRC['sofr']['url'](a,b); j=json.loads(get(u)); return [(r['effectiveDate'],r['percentRate'],r.get('volumeInBillions'),r.get('revisionIndicator','')) for r in j['refRates']],u,j
def rows_rrp(a,b):
    u=SRC['onrrp']['url'](a,b); j=json.loads(get(u))
    rr=[(r['operationDate'],r.get('totalAmtAccepted'),r.get('participatingCpty'),r.get('operationId')) for r in j['repo']['operations'] if r.get('operationType')=='Reverse Repo' and r.get('termCalenderDays',1)<=4 and r.get('auctionStatus','Results')=='Results']
    return rr,u,j
def rows_auc(a,b):
    d,u=fd_all('/v1/accounting/od/auctions_query','record_date,cusip,security_type,security_term,auction_date,issue_date,high_yield,high_investment_rate,high_discnt_rate,high_discnt_margin,bid_to_cover_ratio,offering_amt,total_accepted',f'auction_date:gte:{a},auction_date:lte:{b}','auction_date')
    return [(r['auction_date'],r['security_term'],r['security_type'],r['cusip'],next((r[k] for k in ('high_yield','high_discnt_rate','high_discnt_margin') if r.get(k) not in (None,'null','')),''),r['bid_to_cover_ratio'],r['offering_amt']) for r in d],u,d
def rows_auc_td(a,b):
    # nightly: TreasuryDirect posts results minutes after each auction; fiscaldata lags several days
    u='https://www.treasurydirect.gov/TA_WS/securities/auctioned?format=json&days=10'; d=json.loads(get(u))
    k=lambda x:(x.get('auctionDate') or x.get('competitiveAuctionCloseDate') or '')[:10]
    return [(k(x),x['securityTerm'],x['securityType'],x['cusip'],(x.get('highYield') or x.get('highDiscountRate') or x.get('highRate') or x.get('highDiscountMargin')),x.get('bidToCoverRatio'),x.get('offeringAmount')) for x in d if a<=k(x)<=b and (x.get('highYield') or x.get('highDiscountRate') or x.get('highRate') or x.get('highDiscountMargin'))],u,d
def rows_tga(a,b):
    d,u=fd_all('/v1/accounting/dts/operating_cash_balance','record_date,account_type,open_today_bal,close_today_bal',f'record_date:gte:{a},record_date:lte:{b}','record_date')
    keep=[r for r in d if r['account_type'] in ('Treasury General Account (TGA) Closing Balance','Treasury General Account (TGA)','Federal Reserve Account')]
    def v(r):  # closing-balance row carries the value in open_today_bal; older rows in close_today_bal
        return r['open_today_bal'] if r['account_type'].endswith('Closing Balance') else r['close_today_bal']
    return [(r['record_date'],v(r),r['account_type']) for r in keep],u,d
def rows_ust(a,b):
    out=[];raw={};u=None
    for y in range(int(a[:4]),int(b[:4])+1):
        u=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv'
        t=get(u).decode(); raw[y]=t
        for r in csv.DictReader(io.StringIO(t)):
            m,d_,yy=r['Date'].split('/'); D=f'{yy}-{m}-{d_}'
            if a<=D<=b: out.append((D,r.get('2 Yr'),r.get('10 Yr'),r.get('3 Mo'),r.get('30 Yr')))
    return sorted(out),u,raw
F={'sofr':(rows_sofr,'2018-04-02',['date','sofr_pct','volume_bn','revision_indicator']),
   'onrrp':(rows_rrp,'2013-09-23',['date','accepted_usd','counterparties','operation_id']),
   'auctions':(rows_auc,'1979-01-01',['auction_date','term','type','cusip','high_yield_or_rate','bid_to_cover','offering_amt']),
   'tga':(rows_tga,'2005-10-03',['record_date','tga_close_mn','account_type']),
   'ust_curve':(rows_ust,'1990-01-02',['date','2y','10y','3m','30y'])}
def backfill():
    os.makedirs(f'{ROOT}/history',exist_ok=True); os.makedirs(f'{ROOT}/raw',exist_ok=True)
    today=dt.date.today().isoformat(); rep=[]
    for k,(fn,st,cols) in F.items():
        if len(sys.argv)>2 and k not in sys.argv[2:]: continue
        rows,u,raw=fn(st,today)
        json.dump(raw,open(f'{ROOT}/raw/{k}_full.json','w'))
        with open(f'{ROOT}/history/{k}.csv','w',newline='') as f: w=csv.writer(f); w.writerow(cols+['url','fetched_at']); t=now(); [w.writerow(list(r)+[u,t]) for r in rows]
        rep.append((k,len(rows),rows[0][0] if rows else None,rows[-1][0] if rows else None)); print(rep[-1],flush=True)
def nightly(day=None):
    day=day or dt.date.today().isoformat(); lo=(dt.date.fromisoformat(day)-dt.timedelta(days=7)).isoformat(); st={}
    for k,(fn,_,cols) in F.items():
        p=f'{ROOT}/daily/{k}/{day}.json'; os.makedirs(os.path.dirname(p),exist_ok=True)
        if os.path.exists(p): st[k]='exists_skip'; continue
        if k=='auctions': fn=rows_auc_td
        try: rows,u,_=fn(lo,day)
        except Exception as e: st[k]=f'fetch_error:{e}'; continue
        if not rows: st[k]='not_ready'; continue
        tmp=p+'.tmp'; json.dump({'fetched_at':now(),'url':u,'columns':cols,'rows':rows},open(tmp,'w'))
        os.link(tmp,p) if not os.path.exists(p) else None; os.remove(tmp); st[k]='written'   # link fails if a file appeared meanwhile -> never overwrite
    print(json.dumps(st)); return 0 if not any(v.startswith('fetch_error') for v in st.values()) else 1
if __name__=='__main__':
    sys.exit(backfill() if sys.argv[1]=='backfill' else nightly(sys.argv[2] if len(sys.argv)>2 else None))

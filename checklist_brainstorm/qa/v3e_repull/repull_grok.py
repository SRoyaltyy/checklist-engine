import csv,json,time,datetime as dt,requests,yfinance as yf,re
H={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) Chrome/120 Safari/537.36','Accept':'application/json, text/plain, */*'}
now=lambda: dt.datetime.now().strftime('%Y-%m-%d %H:%M HKT')
rows=[]
for f in ['in/fp_grok_v3c.csv','in/fp_grok_ratings.csv']:
    rows+=list(csv.DictReader(open(f)))
out=[];cache={}
def rec(r,src,st,n,fd,ld,lv,v,note):
    out.append(dict(owner='grok-bot',series=r['series'],source_used=src,fetched_at_HKT=now(),http_status=st,rows=n,first_date=fd,last_date=ld,last_value=lv,claimed_earliest=r['earliest_history_date'],verdict=v,note=note))
def claimed(r):
    m=re.search(r'\d{4}-\d{2}-\d{2}',r['earliest_history_date']);return m.group(0) if m else None
def ok_hist(fd,c,tol=45):
    return c is None or (dt.date.fromisoformat(fd)-dt.date.fromisoformat(c)).days<=tol
# nasdaq econ
NAMES={'CPI':r'^CPI\b(?!.*Core)|Consumer Price Index','core CPI':r'Core CPI|CPI ex|Core Consumer','NFP':r'Nonfarm Payrolls|Non-Farm','jobless claims':r'Jobless Claims|Initial Claims','retail sales':r'Retail Sales','ISM mfg':r'ISM Manufacturing|ISM Mfg','ISM services':r'ISM (Non-Manufacturing|Services)'}
def nasdaq(d):
    if d in cache: return cache[d]
    time.sleep(1)
    try:
        x=requests.get(f'https://api.nasdaq.com/api/calendar/economicevents?date={d}',headers=H,timeout=20)
        rs=(x.json().get('data') or {}).get('rows') or []
    except Exception as e: x=None;rs=[]
    cache[d]=(x.status_code if x is not None else 'ERR',rs);return cache[d]
def find_event(pat,start,end):
    d=start;hits=[];st=None;scanned=0
    while d<=end:
        if d.weekday()<5:
            st,rs=nasdaq(d.isoformat());scanned+=1
            for e in rs:
                if e.get('country','').startswith('United States') and re.search(pat,e.get('eventName',''),re.I) and str(e.get('actual','')).strip() not in ('','&nbsp;'):
                    hits.append((d.isoformat(),e['eventName'],e.get('actual'),e.get('consensus')))
        d+=dt.timedelta(1)
    return st,hits
today=dt.date(2026,10,22)
for r in rows:
    s=r['series'];src=r['source'];c=claimed(r)
    try:
      if r['status'] not in('works','save_nightly'): continue
      if s in NAMES:
        st,rec_hits=find_event(NAMES[s],today-dt.timedelta(40),today)
        cd=dt.date.fromisoformat(c)
        st2,old=find_event(NAMES[s],cd-dt.timedelta(5),cd+dt.timedelta(40))
        if rec_hits and old:
            rec(r,'api.nasdaq.com economicevents',st,len(rec_hits)+len(old),old[0][0],rec_hits[-1][0],f"{rec_hits[-1][1]} {rec_hits[-1][2]} vs cons {rec_hits[-1][3]}",'pass',f"old sample {old[0][1]} {old[0][2]}/{old[0][3]}; scanned recent 40d + 40d after claimed earliest")
        elif not rec_hits and not old: rec(r,'api.nasdaq.com economicevents',st,0,'','','','fail_empty' if st==200 else 'fail_blocked','no matching US event with actual in either window')
        elif not old: rec(r,'api.nasdaq.com economicevents',st,len(rec_hits),'',rec_hits[-1][0],rec_hits[-1][2],'fail_history_short','no event with actual found within 40d after claimed earliest')
        else: rec(r,'api.nasdaq.com economicevents',st,len(old),old[0][0],old[-1][0],old[-1][2],'fail_other','no recent (40d) release found')
      elif 'publicreporting.cftc.gov' in src:
        ds=re.search(r'resource/(\w{4}-\w{4})',src).group(1)
        code={'ES':'13874A','NQ':'209742','RTY':'239742','ZN':'043602','ZB':'020601','VX':'1170E1','DX':'098662','BTC':'133741','6E':'099741','6J':'097741','CL':'067651','GC':'088691','HG':'085692','NG':'023651','ZC':'002602','ZS':'005602'}[s.split()[0]]
        k=(ds,code)
        if k not in cache:
            time.sleep(0.3)
            base=f'https://publicreporting.cftc.gov/resource/{ds}.json'
            q=lambda o: requests.get(base,params={'$select':'report_date_as_yyyy_mm_dd','$where':f"cftc_contract_market_code='{code}'",'$order':f'report_date_as_yyyy_mm_dd {o}','$limit':1},timeout=30)
            a=q('ASC');b=q('DESC')
            n=requests.get(base,params={'$select':'count(*)','$where':f"cftc_contract_market_code='{code}'"},timeout=30).json()
            cache[k]=(a.status_code,a.json(),b.json(),n)
        st,a,b,n=cache[k]
        if not a: rec(r,f'CFTC {ds} code {code}',st,0,'','','','fail_empty','no rows for market code');continue
        fd=a[0]['report_date_as_yyyy_mm_dd'][:10];ld=b[0]['report_date_as_yyyy_mm_dd'][:10];cnt=list(n[0].values())[0]
        v='pass'
        if not ok_hist(fd,c,120): v='fail_history_short'
        elif (today-dt.date.fromisoformat(ld)).days>16: v='fail_other'
        rec(r,f'CFTC {ds} code {code}',st,cnt,fd,ld,'report '+ld,v,'' if v=='pass' else f'first {fd} vs claimed {c}; last {ld}')
      elif 'upgrades_downgrades' in src:
        if 'ud' not in cache:
            time.sleep(2);cache['ud']=yf.Ticker('AAPL').upgrades_downgrades
        u=cache['ud']
        if u is None or len(u)==0: rec(r,'yfinance AAPL upgrades_downgrades',200,0,'','','','fail_empty','');continue
        idx=sorted(u.index);fd=str(idx[0])[:10];ld=str(idx[-1])[:10];last=u.loc[idx[-1]]
        last=last.iloc[0] if hasattr(last,'iloc') and last.ndim>1 else last
        lv=f"{last.get('Firm')} {last.get('Action')} {last.get('ToGrade')} PT {last.get('priorPriceTarget')}->{last.get('currentPriceTarget')}"
        v='pass' if ok_hist(fd,c) and (today-dt.date.fromisoformat(ld)).days<=30 else 'fail_history_short'
        rec(r,'yfinance AAPL upgrades_downgrades',200,len(u),fd,ld,lv,v,'')
      elif r['status']=='save_nightly' or s=='beta-residual':
        if s=='beta-residual' or src.startswith('Yahoo yfinance') or s=='future move minus stock return':
            sym={'ES':'ES=F','NQ':'NQ=F','RTY':'RTY=F','CL':'CL=F','GC':'GC=F','HG':'HG=F','BTC':'BTC-USD','10y':'^TNX','beta-residual':'SPY','future move minus stock return':'XLK'}[s]
            time.sleep(2);h=yf.Ticker(sym).history(period='max' if s=='beta-residual' else '5d')
            if len(h)==0: rec(r,f'yfinance {sym}','?',0,'','','','fail_empty','');continue
            fd=str(h.index[0])[:10];ld=str(h.index[-1])[:10]
            v='pass' if (today-dt.date.fromisoformat(ld)).days<=4 and (s!='beta-residual' or ok_hist(fd,c,10)) else 'fail_other'
            rec(r,f'yfinance {sym}',200,len(h),fd,ld,round(float(h.Close.iloc[-1]),4),v,'today-value check only' if r['status']=='save_nightly' else 'full history check')
        elif 'analyst_price_targets' in src:
            time.sleep(2);t=yf.Ticker('AAPL').analyst_price_targets
            rec(r,'yfinance AAPL analyst_price_targets',200,1 if t else 0,'','2026-10-22',json.dumps(t)[:120] if t else '','pass' if t else 'fail_empty','today-value check only')
        elif 'eps_trend' in src:
            time.sleep(2);t=yf.Ticker('AAPL').eps_trend
            rec(r,'yfinance AAPL eps_trend',200,len(t) if t is not None else 0,'','2026-10-22',str(t.iloc[1].to_dict())[:120] if t is not None and len(t)>1 else '','pass' if t is not None and len(t) else 'fail_empty','today-value check only')
        elif 'revenue_estimate' in src:
            time.sleep(2);t=yf.Ticker('AAPL').revenue_estimate
            rec(r,'yfinance AAPL revenue_estimate',200,len(t) if t is not None else 0,'','2026-10-22',str(t.iloc[0].to_dict())[:120] if t is not None and len(t) else '','pass' if t is not None and len(t) else 'fail_empty','today-value check only')
        elif 'groups.ashx' in src:
            if 'fv' not in cache:
                x=requests.get('https://finviz.com/groups.ashx?g=industry&v=140',headers={'User-Agent':H['User-Agent']},timeout=20)
                cache['fv']=(x.status_code,x.text)
            st,t=cache['fv'];n=t.count('screener.ashx?v=111&f=ind_')
            rec(r,'finviz groups.ashx industry v=140',st,n,'','2026-10-22',f'{n} industry links' ,'pass' if st==200 and n>50 else 'fail_blocked','today-value check only')
        else: rec(r,src[:40],'',0,'','','','fail_other','no handler')
    except Exception as e:
        rec(r,src[:40],'ERR',0,'','','','fail_other',repr(e)[:150])
json.dump(out,open('raw.json','w'))
print(len(out))

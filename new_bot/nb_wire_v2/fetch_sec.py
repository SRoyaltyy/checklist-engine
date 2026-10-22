# SEC XBRL dei:EntityCommonStockSharesOutstanding per survivor; keep facts filed <= 2024-12-31 only.
import json, pandas as pd, requests, time, threading, concurrent.futures as cf
j=json.load(open('sec_tickers.json')); m={}
for v in j.values(): m.setdefault(v['ticker'].replace('.','-'),v['cik_str'])
U=[t for t in open('univ.txt').read().split() if t in m]
H={'User-Agent':'Cyrus Fung research cyrus@example.com'}; lock=threading.Lock(); last=[0.0]
def get(t):
    url=f'https://data.sec.gov/api/xbrl/companyconcept/CIK{m[t]:010d}/dei/EntityCommonStockSharesOutstanding.json'
    for a in range(4):
        with lock:
            w=0.13-(time.time()-last[0]); 
            if w>0: time.sleep(w)
            last[0]=time.time()
        try: r=requests.get(url,headers=H,timeout=30)
        except Exception: time.sleep(2); continue
        if r.status_code==404: return t,'nofacts',[]
        if r.status_code==200:
            out=[]
            for u in r.json().get('units',{}).values():
                for f in u:
                    if f.get('filed','9999')<='2024-12-31': out.append(dict(ticker=t,cik=m[t],end=f['end'],val=f['val'],filed=f['filed'],form=f.get('form'),accn=f.get('accn')))
            return t,'ok',out
        if r.status_code==403: return t,'403',[]
        time.sleep(3*(a+1))
    return t,'fail',[]
res=[];st=[]
with cf.ThreadPoolExecutor(4) as ex:
    for i,(t,s,o) in enumerate(ex.map(get,U)):
        res+=o; st.append((t,s,len(o)))
        if i%500==0: print(i,len(U),pd.Series([x[1] for x in st]).value_counts().to_dict(),flush=True)
pd.DataFrame(res).to_parquet('sec/sec_shares_out_filed_le_2024.parquet',index=False)
pd.DataFrame(st,columns=['ticker','status','n']).to_csv('sec/fetch_status.csv',index=False); print('done',len(U),len(res))

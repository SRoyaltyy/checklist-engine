# Nasdaq dividend history (declarationDate) for NASD-listed survivors. Rows with ex-date > 2024-12-31 are discarded in memory, never saved.
import pandas as pd, requests, json, time, concurrent.futures as cf
cur=pd.read_csv('/workspace/theme-radar-shadowlock/data/snapshots/current.csv',usecols=['Ticker','Exchange'])
U=set(open('univ.txt').read().split()); T=sorted(set(cur[cur.Exchange=='NASD'].Ticker)&U)
H={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64)','Accept':'application/json'}
def get(t):
    for a in range(4):
        try:
            r=requests.get(f'https://api.nasdaq.com/api/quote/{t.replace("-",".")}/dividends?assetclass=stocks',headers=H,timeout=20)
            if r.status_code==200:
                d=r.json().get('data') or {}; rows=((d.get('dividends') or {}).get('rows')) or []
                out=[]
                for x in rows:
                    ex=pd.to_datetime(x['exOrEffDate'],format='%m/%d/%Y',errors='coerce')
                    if pd.isna(ex) or ex>pd.Timestamp('2024-12-31'): continue
                    out.append(dict(ticker=t,ex=ex,type=x['type'],amount=x['amount'],decl=x['declarationDate']))
                return t,'ok',out
        except Exception as e: pass
        time.sleep(2*(a+1))
    return t,'fail',[]
res=[];st=[]
with cf.ThreadPoolExecutor(6) as ex:
    for i,(t,s,o) in enumerate(ex.map(get,T)):
        res+=o; st.append((t,s,len(o)))
        if i%500==0: print(i,len(T),flush=True)
pd.DataFrame(res).to_parquet('div/nasdaq_dividends_2020_24.parquet',index=False)
pd.DataFrame(st,columns=['ticker','status','n_rows']).to_csv('div/fetch_status.csv',index=False); print('done',len(T),len(res))

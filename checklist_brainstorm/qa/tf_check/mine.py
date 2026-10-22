import requests,json,math,datetime as dt,sys
sys.path.insert(0,'/workspace/tf/tfx'); import tfx  # only for claimed values
H={'User-Agent':'Mozilla/5.0'}
def pull(t):
    r=requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=0&period2=1792000000&interval=1d&events=split',headers=H,timeout=40).json()['chart']['result'][0]
    q=r['indicators']['quote'][0];out={}
    for ts,c in zip(r['timestamp'],q['close']):
        if c is None: continue
        d=(dt.datetime.utcfromtimestamp(ts)-dt.timedelta(hours=5)).date(); out[d]=c
    return out
spy=sorted(pull('SPY')); spy=[d for d in spy if d>=dt.date(1993,1,29)]; spos={d:i for i,d in enumerate(spy)}
def key(d,tf):
    if tf=='W': y,w,_=d.isocalendar(); return (y,w)
    if tf=='M': return (d.year,d.month)
    return spos[d]//int(tf[0])
def bars(cl,tf,D,mode):
    ds=[d for d in sorted(cl) if d<D and (tf in 'WM' or d in spos)]
    cur=key(D,tf);done={};part=[]
    for d in ds:
        k=key(d,tf)
        if k==cur: part.append((d,cl[d]))
        else: done[k]=(d,cl[d])
    b=[done[k] for k in sorted(done)]
    if mode=='ptd' and part: b.append(part[-1])
    return b
def ema(x,n):
    a=2/(n+1);e=x[0];o=[e]
    for v in x[1:]: e=a*v+(1-a)*e;o.append(e)
    return o
def feats(b):
    c=[v for _,v in b]
    d=[c[i]-c[i-1] for i in range(1,len(c))];n=14
    au=sum(max(x,0) for x in d[:n])/n;ad=sum(max(-x,0) for x in d[:n])/n
    for x in d[n:]: au=(au*13+max(x,0))/14;ad=(ad*13+max(-x,0))/14
    rsi=100-100/(1+au/ad)
    m=[a-b for a,b in zip(ema(c,12),ema(c,26))];h=m[-1]-ema(m,9)[-1]
    w=c[-20:];mu=sum(w)/20;sd=math.sqrt(sum((v-mu)**2 for v in w)/20);pb=(c[-1]-(mu-2*sd))/(4*sd)
    s50=sum(c[-50:])/50
    return dict(rsi14=rsi,macd_hist=h,pctb=pb,c_sma20=c[-1]/mu-1,c_sma50=c[-1]/s50-1,s20_gt_s50=int(mu>s50),last_bar_end=b[-1][0],n=len(b))
res=[]
for t in ['AAPL','MSFT','NVDA']:
    cl=pull(t)
    raw,sp=tfx.load_daily(t)
    for D in ['2025-06-11','2025-03-03','2024-11-27']:
        Dd=dt.date.fromisoformat(D)
        for tf in ['2D','3D','W','M']:
            for mode in ['complete','ptd']:
                me=feats(bars(cl,tf,Dd,mode))
                th=tfx.feats(tfx.resample(raw,sp,tf,D,mode))
                th['s20_gt_s50']=None
                for k in ['rsi14','macd_hist','pctb','c_sma20','c_sma50']:
                    a,b=me[k],float(th[k]);ok=abs(a-b)<=max(1e-4,1e-4*abs(b))
                    res.append((t,D,tf,mode,k,round(b,6),round(a,6),ok,str(th['last_bar_end']),str(me['last_bar_end'])))
                assert me['last_bar_end']<Dd
import csv;w=csv.writer(open('tf_spot.csv','w'));w.writerow('ticker D tf mode feat taskforce manager match tf_last_bar mgr_last_bar'.split());w.writerows(res)
print(len(res),sum(r[7] for r in res));[print(r) for r in res if not r[7] or r[8]!=r[9]]
print([r for r in res if r[0]=='AAPL' and r[1]=='2025-06-11' and r[2]=='W' and r[4]=='rsi14'])

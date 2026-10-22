# Build GK-OPX IV YES/NO rows for one year (2020-2024 only) from raw DoltHub volatility_history CSV.
# Same definitions/layout as v1 chunks (opt_YYYY_v1.tar). Codes 0=NR 1=NO 2=YES, 2-bit packed, id0 in lowest bits.
import sys, json, glob, os, numpy as np, pandas as pd, exchange_calendars as xc
y=int(sys.argv[1]); assert 2020<=y<=2024, "2025-26 sealed"
IDS=["GK-OPX-IVR-HI","GK-OPX-IVR-LO","GK-OPX-IVHV-HI","GK-OPX-IVHV-LO","GK-OPX-IVCHG-UP","GK-OPX-IVCHG-DN"]
v1=json.load(open("prior/x/chunks/2020__OPT__Energy.json"))
# universe+sectors = New Bot 2024 survivor set, as recorded in the v1 2020 chunks
uni={}
for f in glob.glob("prior/x/chunks/2020__OPT__*.parquet"):
    sec=f.split("__OPT__")[1][:-8]
    for t in pd.read_parquet(f,columns=["ticker"]).ticker.unique(): uni[t]=sec
cal=xc.get_calendar("XNYS")
allS=cal.sessions_in_range(f"{y-1}-11-01",f"{y}-12-31"); allS=[s.date() for s in allS]
S=[s for s in allS if s.year==y]; sidx={s:i for i,s in enumerate(allS)}
raw=pd.read_csv(f"raw/vol_history_{y}.csv",parse_dates=["date"])
raw["date"]=raw.date.dt.date
raw=raw[raw.act_symbol.isin(uni)].sort_values(["act_symbol","date"])
import bisect
def first_session_after(d):
    i=bisect.bisect_right(allS,d); return i
out=[]
g={t:df for t,df in raw.groupby("act_symbol")}
for t in sorted(uni):
    df=g.get(t); dates=list(df.date) if df is not None else []
    recs=df.to_dict("records") if df is not None else []
    for s in S:
        i=bisect.bisect_left(dates,s)-1  # latest D < S
        codes=[0]*6; stale=0; lag=99
        if i>=0:
            r=recs[i]; lag=sidx[s]-first_session_after(r["date"])
            if lag<=2:
                stale=int(lag>0); iv=r["iv_current"]; hv=r["hv_current"]; lo=r["iv_year_low"]; hi=r["iv_year_high"]
                def yn(c): return 2 if c else 1
                if pd.notna(iv) and pd.notna(lo) and pd.notna(hi) and hi>lo:
                    rk=(iv-lo)/(hi-lo); codes[0]=yn(rk>=0.80); codes[1]=yn(rk<=0.20)
                if pd.notna(iv) and pd.notna(hv) and hv>0:
                    q=iv/hv; codes[2]=yn(q>1.3); codes[3]=yn(q<0.8)
                if i>=1 and (r["date"]-recs[i-1]["date"]).days<=7:
                    p=recs[i-1]["iv_current"]
                    if pd.notna(iv) and pd.notna(p) and p>0:
                        ch=iv/p-1; codes[4]=yn(ch>=0.15); codes[5]=yn(ch<=-0.15)
        b=bytearray(2)
        for k,c in enumerate(codes): b[k//4]|=c<<(2*(k%4))
        out.append((t,uni[t],s.isoformat(),bytes(b),stale,lag))
o=pd.DataFrame(out,columns=["ticker","sector","date","packed","stale","lag"])
os.makedirs(f"out/{y}",exist_ok=True)
for sec,d in o.groupby("sector"):
    fn=f"out/{y}/{y}__OPT__{sec}.parquet"; d.drop(columns="sector").reset_index(drop=True).to_parquet(fn,index=False)
    m=dict(v1); m.update(year=y,sector=sec,n_tickers=int(d.ticker.nunique()),n_cells=len(d),
      raw_file=f"raw/vol_history_{y}.csv",version="v2_rebuild_2026-10-22")
    json.dump(m,open(fn[:-8]+".json","w"),indent=1)
fresh=(o.lag==0).sum(); print(y,"cells",len(o),"fresh",fresh,"stale",(o.stale==1).sum(),"NR_all",(o.packed==b'\0\0').sum())

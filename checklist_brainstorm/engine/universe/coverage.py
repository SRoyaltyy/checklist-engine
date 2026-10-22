import sys, glob, numpy as np, pandas as pd
sys.path.insert(0,'.'); from engine_year import unpack, CHUNKS
y=int(sys.argv[1]); m=pd.read_csv('../../master.csv',dtype=str)
ans={}; tot={}
def add(ids,C):
    a=(C>0).sum(0); n=C.shape[0]
    for i,q in enumerate(ids): ans[q]=ans.get(q,0)+int(a[i]); tot[q]=tot.get(q,0)+n
sh=np.load(CHUNKS/f"{y}__SHARED.npz"); add(list(sh["ids"]),unpack(sh["packed"],len(sh["ids"])))
for f in sorted(glob.glob(str(CHUNKS/f"{y}__*.npz"))):
    if any(k in f for k in ("SHARED","__TR__","SECADD")): continue
    z=np.load(f); ids=list(z["ids"]); P=z["packed"]
    for i in range(0,len(P),25000): add(ids,unpack(P[i:i+25000],len(ids)))
for f in sorted(glob.glob(str(CHUNKS/f"{y}__TR__*.npz"))):
    z=np.load(f); ks=[k.split("|")[0] for k in z["keys"]]; P=z["packed"]
    for i in range(0,len(P),20000):
        C=unpack(P[i:i+20000],len(ks)); df=pd.DataFrame(C>0,columns=ks)
        a=df.T.groupby(level=0).sum().sum(1); n=df.T.groupby(level=0).size()*len(C)
        for q in a.index: ans[q]=ans.get(q,0)+int(a[q]); tot[q]=tot.get(q,0)+int(n[q])
m["in_engine"]=m.id.isin(tot); m["cells"]=m.id.map(tot).fillna(0); m["answered"]=m.id.map(ans).fillna(0)
m["any_answer"]=m.answered>0
g=m.groupby(["source","data_type"],dropna=False).agg(questions=("id","size"),in_engine=("in_engine","sum"),q_with_any_answer=("any_answer","sum"),cells=("cells","sum"),answered=("answered","sum")).reset_index()
g["answered_share"]=(g.answered/g.cells.where(g.cells>0)).round(4); g["NR_share"]=(1-g.answered_share).round(4)
m.to_csv(f"coverage_{y}_byid.csv",index=False); g.to_csv(f"coverage_{y}.csv",index=False)
s=m.groupby("source",dropna=False).agg(questions=("id","size"),in_engine=("in_engine","sum"),q_with_any_answer=("any_answer","sum"),cells=("cells","sum"),answered=("answered","sum")).reset_index()
s["answered_share"]=(s.answered/s.cells.where(s.cells>0)).round(4)
pat="option|put|call|short|insider|finviz|form 4|13f"
foc=g[g.source.str.contains(pat,case=False,na=False)|g.data_type.str.contains(pat,case=False,na=False)]
with open(f"coverage_{y}.md","w") as o:
    o.write(f"# Source coverage {y} (master.csv, {len(m)} questions)\nCells = engine cells in {y} chunks (shared per date, stock tier per ticker-day, TR per ticker-day x N). Answered = YES or NO; rest NOT_READY/NR. 'in_engine' = id present in the {y} chunks at all.\n\n## By source\n"+s.to_markdown(index=False)+"\n\n## Focus: options / put-call / short volume / insider / Finviz\n"+foc.to_markdown(index=False)+"\n\n## By source x data_type\n"+g.to_markdown(index=False)+"\n")
print(s.to_string()); print(foc.to_string())

"""Order-only corrected A_SHARED for the look-alike cells (Bug-1 fix only, for attributable re-score)."""
import numpy as np, pandas as pd, sys
sys.path.insert(0,".."); 
U="/workspace/checklist_brainstorm/engine/universe/chunks"
def unpack(P,n): return np.stack([(P[:,j//4]>>(2*(j%4)))&3 for j in range(n)],1).astype(np.uint8)
ids0=[str(i) for i in np.load(f"{U}/2020__SHARED.npz")["ids"]]; pos={c:i for i,c in enumerate(ids0)}
D,A=[],[]
for y in range(2020,2025):
    z=np.load(f"{U}/{y}__SHARED.npz"); iy=[str(i) for i in z["ids"]]; a=unpack(z["packed"],len(iy))
    o=np.empty(len(iy),int); o[[pos[c] for c in iy]]=np.arange(len(iy)); A.append(a[:,o]); D+=[str(x)[:10] for x in z["dates"]]
A=np.concatenate(A); dm={d:i for i,d in enumerate(D)}
E=pd.read_parquet("/workspace/tmp_laf/cells.parquet"); di=E.date.dt.strftime("%Y-%m-%d").map(dm)
out=np.zeros((len(E),len(ids0)),np.uint8); ok=di.notna().values; out[ok]=A[di[ok].astype(int).values]
old=np.load("/workspace/tmp_laf/A_SHARED.npz"); assert list(map(str,old["ids"]))==ids0 and old["A"].shape==out.shape
y=E.date.dt.year.values; print("diff non-2023",(old["A"][y!=2023]!=out[y!=2023]).sum(),"diff 2023",(old["A"][y==2023]!=out[y==2023]).sum())
np.savez_compressed("/workspace/tmp_fix23/A_SHARED.npz",A=out,ids=np.array(ids0))

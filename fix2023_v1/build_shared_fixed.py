"""Build corrected SHARED answers 2020-24: per-year id order aligned to the 2020 order; Bug-2 columns -> NR."""
import numpy as np, pandas as pd
U="/workspace/checklist_brainstorm/engine/universe/chunks"
def unpack(P,n): return np.stack([(P[:,j//4]>>(2*(j%4)))&3 for j in range(n)],1).astype(np.uint8)
ids0=[str(i) for i in np.load(f"{U}/2020__SHARED.npz")["ids"]]; pos={c:i for i,c in enumerate(ids0)}
D,A=[],[]
for y in range(2020,2025):
    z=np.load(f"{U}/{y}__SHARED.npz"); iy=[str(i) for i in z["ids"]]; assert set(iy)==set(ids0)
    dt=[str(x)[:10] for x in z["dates"]]; assert max(dt)<="2024-12-31"
    a=unpack(z["packed"],len(iy)); o=np.empty(len(iy),int); o[[pos[c] for c in iy]]=np.arange(len(iy)); A.append(a[:,o]); D+=dt
A=np.concatenate(A); m=set(pd.read_csv("missing_as_no_rows.csv").col)
mask=np.array([c in m for c in ids0]); A[:,mask]=0
np.savez_compressed("shared_answers_2020_24.npz",A=A,ids=np.array(ids0),dates=np.array(D),missing_fixed_cols=np.array(ids0)[mask])
print(A.shape,mask.sum())

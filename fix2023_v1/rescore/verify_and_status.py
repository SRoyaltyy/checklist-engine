"""FIX2023_V1 re-score. (a) FINDINGS_FREEZE_V1: pairs are same-date, so a market-wide SHARED answer is identical for winner and loser
-> SHARED items never differ -> never enter the honesty split. Verified on both pair sets with the corrected and the old A_SHARED.
(b) untested_v1: re-run with corrected SHARED block (untested_run_fix.py) and diff. (c) per-SHARED-row status CSV."""
import numpy as np, pandas as pd
cells=pd.read_parquet("/workspace/tmp_laf/cells.parquet"); ci=pd.Index(cells.ticker+"|"+cells.date.dt.strftime("%Y-%m-%d"))
for tag,f in (("old","/workspace/tmp_laf/A_SHARED.npz"),("fixed","/workspace/tmp_fix23/A_SHARED.npz")):
    A=np.load(f)["A"]
    for pf in ("pairs","pairs_v1"):
        p=pd.read_parquet(f"/workspace/tmp_laf/{pf}.parquet"); w=ci.get_indexer(p.winner.astype(str)+"|"+p.winner_date.astype(str).str[:10]); l=ci.get_indexer(p.loser.astype(str)+"|"+p.loser_date.astype(str).str[:10])
        assert (w>=0).all() and (l>=0).all(); Aw,Al=A[w],A[l]; d=((Aw>0)&(Al>0)&(Aw!=Al)).sum()
        print(tag,pf,"pairs",len(p),"SHARED winner/loser differing cells",int(d))
for f in ("FINDINGS_FREEZE_V1.csv","honesty_split.csv.gz","exit_v1/honesty_split.csv.gz"):
    d=pd.read_csv(f"../../practice_results/lookalike_features/{f}"); print(f,"SHARED rows",int(d.source.str.contains("SHARED").sum()))
ids=[str(i) for i in np.load("/workspace/tmp_fix23/A_SHARED.npz")["ids"]]
o=pd.read_csv("../../untested_v1/untested_results_v1.csv"); n=pd.read_csv("untested_results_v1_fix2023.csv")
m=o.merge(n[["list","row_id","status","A_d_n","A_c_n","B_d_n","B_c_n"]],on=["list","row_id"],suffixes=("_v1","_fixed"),how="outer")
m=m[m.col.astype(str).isin(ids)].copy()
miss=set(pd.read_csv("../missing_as_no_rows.csv").col)
m["status_changed"]=m.status_v1.str.split(":").str[0]!=m.status_fixed.str.split(":").str[0]
m["missing_as_no_bug2"]=m.col.isin(miss)
m["findings_freeze_v1"]="not in freeze (same-date pairs: SHARED never differs); unchanged"
m[["list","row_id","label","col","status_v1","status_fixed","status_changed","missing_as_no_bug2","A_d_n_fixed","A_c_n_fixed","B_d_n_fixed","B_c_n_fixed","findings_freeze_v1"]].to_csv("../shared_rows_corrected_status.csv",index=False)
print("SHARED rows in untested_v1",len(m)); print(pd.crosstab(m.status_v1.str[:20],m.status_fixed.str[:20]))

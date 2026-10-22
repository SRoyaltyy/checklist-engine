"""Loader for FIX2023_V1 corrected answers. Codes: 0=NR, 1=NO, 2=YES.
shared(dates=None)                 -> DataFrame dates x 8,176 SHARED ids (per-year order fixed, missing-as-NO -> NR)
shared_for(tickers_dates_df)       -> SHARED answers broadcast to (ticker,date) rows (market-wide rows)
mask_missing(A, ids)               -> sets the 264 missing-as-NO columns (any kind: SHARED/TR/NB/MPV) to NR in any engine answer matrix"""
import os, numpy as np, pandas as pd
H=os.path.dirname(os.path.abspath(__file__))
MISSING=set(pd.read_csv(f"{H}/missing_as_no_rows.csv").col.astype(str))
def shared(dates=None):
    z=np.load(f"{H}/shared_answers_2020_24.npz"); df=pd.DataFrame(z["A"],index=pd.to_datetime(z["dates"]),columns=z["ids"])
    return df if dates is None else df.reindex(pd.to_datetime(dates)).fillna(0).astype(np.uint8)
def shared_for(td):
    S=shared(); i=S.index.get_indexer(pd.to_datetime(td["date"])); out=np.zeros((len(td),S.shape[1]),np.uint8); ok=i>=0; out[ok]=S.values[i[ok]]
    return pd.DataFrame(out,columns=S.columns,index=td.index)
def mask_missing(A, ids):
    A=np.array(A,copy=True); A[:,[j for j,c in enumerate(map(str,ids)) if c in MISSING]]=0; return A

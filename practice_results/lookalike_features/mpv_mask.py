"""Warm-up mask for master_pv rows: price file starts 2020-01-02, so NaN-lookback comparisons would read as NO.
Rows with lookback >= 126 bars -> NA before 2021-01-05; all others -> NA before 2020-06-01. HST-NB-004 (needs 10y) dropped -> NOT_READY."""
import numpy as np, pandas as pd
T = "/workspace/tmp_laf"; z = np.load(f"{T}/A_MPV.npz", allow_pickle=True); A = z["A"].copy(); ids = list(z["ids"])
d = pd.read_parquet(f"{T}/cells.parquet", columns=["date"]).date.values
LONG = {f"PV-TF-{k:03d}" for k in list(range(285, 302 + 1)) + [96, 97, 102, 103, 110, 111, 118, 119, 126, 127] + list(range(128, 136)) + list(range(186, 195)) + [202, 203, 206, 276, 277, 385, 395, 405, 408, 409]} | {"SEC-JA-010", "SEC-JA-011", "SEC-JA-028", "HST-NB-001", "HST-NB-003"}
for j, k in enumerate(ids):
    cut = np.datetime64("2021-01-05") if k in LONG else np.datetime64("2020-06-01"); A[d < cut, j] = 0
keep = [j for j, k in enumerate(ids) if k != "HST-NB-004"]
np.savez(f"{T}/A_MPV.npz", A=A[:, keep], ids=np.array([ids[j] for j in keep])); print(len(keep), (A[:, keep] > 0).mean())

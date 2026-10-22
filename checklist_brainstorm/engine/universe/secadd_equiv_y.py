# Year-parameterised copy of secadd_equiv.py (usage: secadd_equiv_y.py YEAR).
import sys, numpy as np, pandas as pd
sys.path.insert(0, '.'); import sector_addon as S, engine_year as E
J = S.reader(); J._tr_universe = lambda d: S.U; rows = J._rows(); rows = rows[rows.id.isin(S.CL)]; J._rows = lambda: rows
rng = np.random.default_rng(5); Y = int(sys.argv[1]); ds = S.sessions(Y); res = []
for name in ("SP500", "ALL"):
    z = np.load(E.CHUNKS / f"{Y}__SECADD_{name}.npz"); tk = list(z["tickers"]); ids = list(z["ids"]); nd = len(z["dates"]); packed = z["packed"]
    pool = tk if name == "SP500" else [t for t in tk if t not in set(S.sp500()) and t in S.U.index]
    for t in rng.choice(pool, 12, replace=False):
        d = ds[rng.integers(len(ds))]; S.CELL_MEMO.clear()
        slow = {a["row_id"]: S.CODE[a["answer"]] for a in J.answer(t, d)}
        row = tk.index(t) * nd + ds.index(d)
        fast = E.unpack(packed[row:row+1], len(ids))[0]
        for j, i in enumerate(ids):
            if (name == "ALL" or Y != 2024) and S.CL[i] != "SECTOR_ONLY": continue
            res.append((name, t, d, i, slow[i], int(fast[j])))
R = pd.DataFrame(res, columns=["subset", "ticker", "date", "row_id", "slow", "fast"])
print(R.groupby("subset").apply(lambda x: pd.Series({"cells": x.groupby(["ticker", "date"]).ngroups, "answers": len(x), "mismatch": int((x.slow != x.fast).sum())})))
R[R.slow != R.fast].to_csv(f"secadd_equiv_mismatches_{Y}.csv", index=False)

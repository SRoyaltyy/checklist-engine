import numpy as np, pandas as pd
from story_q import SQ, CP, H
M = pd.read_parquet("panel.parquet"); HARD = CP[:6]; W = CP[6]
for h in H: M[f"x{h}"] = M[f"r{h}"] - M.groupby("date")[f"r{h}"].transform("mean")
codes = M[HARD].values; M["A"] = (codes == 2).all(1); M["B"] = (codes > 0).all(1) & (codes == 1).any(1)
M["yr"] = M.date.dt.year; rng = np.random.default_rng(7)
def stats(m, h, nb=1000):
    s = M.loc[m, ["date", f"r{h}", f"x{h}"]].dropna()
    if len(s) < 30: return dict(n=len(s))
    g = s.groupby("date").agg(n=(f"x{h}", "size"), sx=(f"x{h}", "sum"), sr=(f"r{h}", "sum"))
    N, SX = g.n.values, g.sx.values; bs = []
    for _ in range(nb):
        k = rng.integers(0, len(g), len(g)); bs.append(SX[k].sum() / N[k].sum())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(n=len(s), dates=len(g), mean=s[f"r{h}"].mean()*100, med=s[f"r{h}"].median()*100, hit=(s[f"r{h}"] > 0).mean()*100,
                exc=s[f"x{h}"].mean()*100, lo=lo*100, hi=hi*100, sig="*" if lo > 0 or hi < 0 else "")
def tab(rows):
    out = ["| group | h | n | dates | mean% | median% | hit% | excess% | 95% CI | |", "|---|---|---|---|---|---|---|---|---|---|"]
    for name, m in rows:
        for h in H:
            d = stats(m, h)
            if "mean" not in d: out.append(f"| {name} | {h} | {d['n']} | | | | | | | |"); continue
            out.append(f"| {name} | {h} | {d['n']:,} | {d['dates']} | {d['mean']:.2f} | {d['med']:.2f} | {d['hit']:.1f} | {d['exc']:+.2f} | [{d['lo']:+.2f}, {d['hi']:+.2f}] | {d['sig']} |")
    return "\n".join(out)
A, B = M.A, M.B; w = M[W] == 2; wn = M[W] == 1
L = ["## 1. Chart-picture gate", tab([("ALL", M.r5.notna() | True), ("A all6 HARD YES", A), ("B any HARD NO", B), ("A & WARN yes", A & w), ("A & WARN no", A & wn)]),
     "\n## 2. Group A per year", tab([(f"A {y}", A & (M.yr == y)) for y in range(2020, 2025)]),
     "\n## 3. Story questions alone (YES vs NO)", tab(sum([[(f"{q} YES", M[q]), (f"{q} NO", ~M[q])] for q in SQ], [])),
     "\n## 4. Story questions within A", tab(sum([[(f"A&{q} YES", A & M[q]), (f"A&{q} NO", A & ~M[q])] for q in SQ], []))]
open("tables.md", "w").write("\n".join(L)); print("\n".join(L))

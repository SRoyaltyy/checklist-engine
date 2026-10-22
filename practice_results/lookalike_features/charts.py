#!/usr/bin/env python3
"""One side-by-side PNG per winner/loser pair (PRACTICE 2020-24 HINT). Window = 120 bars before D + 21 after; cutoff D marked.
Panels: candles + SMA5/10/20/50/100/200 + BB(20,2) with chains shaded (green/red runs), RSI14, MACD(12,26,9). Indicators are drawn
from all bars in the window; the setup answers themselves use bars < D only. Usage: charts.py [--limit N] [--workers 8] [--sample-dir DIR]"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")
import argparse, sys, io, numpy as np, pandas as pd, pyarrow.parquet as pq
from multiprocessing import Pool
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import PX, LO, HI, TMP
PXD = {}
def ind(c):
    s = pd.Series(c); d = s.diff(); up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan)); m = s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean(); sg = m.ewm(span=9, adjust=False).mean()
    return rsi.values, m.values, sg.values, (m - sg).values
def side(axs, tk, D, title):
    p = PXD[tk]; i = int(np.searchsorted(p["date"], np.datetime64(D))); a, b = max(0, i - 120), min(len(p["date"]), i + 22)
    o, h, l, c = (p[k] for k in "ohlc"); x = np.arange(a, b) - i
    rsi, m, sg, hist = ind(c)
    ax = axs[0]; col = np.where(c[a:b] >= o[a:b], "#2a9d4b", "#d23c3c")
    # chains shaded (prior bars only)
    s = np.sign(c[a:i] - o[a:i]); b0 = np.r_[0, np.flatnonzero(np.diff(s) != 0) + 1]; b1 = np.r_[b0[1:], len(s)]
    for sgn, colr in ((1, "#2a9d4b"), (-1, "#d23c3c")):
        mk = s[b0] == sgn; ax.broken_barh([(x[u] - 0.5, v - u) for u, v in zip(b0[mk], b1[mk])], (0, 1), transform=ax.get_xaxis_transform(), color=colr, alpha=0.12, lw=0)
    ax.vlines(x, l[a:b], h[a:b], color=col, lw=0.6); ax.bar(x, np.abs(c[a:b] - o[a:b]) + 1e-9, bottom=np.minimum(o[a:b], c[a:b]), color=col, width=0.7)
    cs = pd.Series(c)
    for n, cc in zip([5, 10, 20, 50, 100, 200], ["#f4a261", "#e9c46a", "#3366cc", "#8e44ad", "#555", "#000"]): ax.plot(x, cs.rolling(n).mean().values[a:b], lw=0.7, color=cc, label=f"SMA{n}")
    mu, sd = cs.rolling(20).mean().values[a:b], cs.rolling(20).std(ddof=0).values[a:b]; ax.fill_between(x, mu - 2 * sd, mu + 2 * sd, color="#3366cc", alpha=0.06)
    for A_ in axs: A_.axvline(-0.5, color="k", ls="--", lw=0.8); A_.axvspan(-0.5, x[-1] + 0.5, color="#fff3c4", alpha=0.35, lw=0)
    ax.set_title(title, fontsize=8); ax.legend(fontsize=5, ncol=6, loc="upper left"); ax.tick_params(labelsize=6)
    axs[1].plot(x, rsi[a:b], lw=0.7, color="#8e44ad"); axs[1].axhline(70, lw=0.4, color="#999"); axs[1].axhline(30, lw=0.4, color="#999"); axs[1].set_ylim(0, 100); axs[1].set_ylabel("RSI14", fontsize=6)
    axs[2].bar(x, hist[a:b], color=np.where(hist[a:b] >= 0, "#2a9d4b", "#d23c3c"), width=0.8); axs[2].plot(x, m[a:b], lw=0.6, color="#333"); axs[2].plot(x, sg[a:b], lw=0.6, color="#f4a261"); axs[2].set_ylabel("MACD", fontsize=6)
    for A_ in axs[1:]: A_.tick_params(labelsize=6)
    axs[2].set_xlabel("bars from cutoff D (dashed line; shaded = after cutoff)", fontsize=6)
def render(r):
    fn = os.path.join(r["dir"], r["png"])
    if os.path.exists(fn): return os.path.getsize(fn)
    fig, axs = plt.subplots(3, 2, figsize=(11, 5.6), dpi=100, gridspec_kw=dict(height_ratios=[3, 1, 1]), sharex="col")
    side(axs[:, 0], r["winner"], r["winner_date"], f"WIN {r['winner']} D={r['winner_date']} net10 {r['winner_net10_pct']}% ex {r['winner_ex10_pct']}%")
    side(axs[:, 1], r["loser"], r["loser_date"], f"LOSE {r['loser']} D={r['loser_date']} net10 {r['loser_net10_pct']}% ex {r['loser_ex10_pct']}%")
    cap = (r["top_items_differing"] or "(none of the top-40 items differ)").split(" ; ")[:6]
    fig.suptitle(f"{r['pair_id']} | {r['setup']} | PRACTICE 2020–24 HINT | items differing: {r['n_items_differ']}", fontsize=8)
    fig.text(0.01, 0.005, "Top differing items: " + " | ".join(cap), fontsize=5.5, wrap=True)
    fig.subplots_adjust(left=0.04, right=0.99, top=0.9, bottom=0.1, hspace=0.08, wspace=0.12); bio = io.BytesIO(); fig.savefig(bio, format="png", dpi=100); plt.close(fig)
    bio.seek(0); Image.open(bio).convert("RGB").quantize(64).save(fn, optimize=True); return os.path.getsize(fn)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int); ap.add_argument("--workers", type=int, default=6); ap.add_argument("--out", default=f"{TMP}/pngs"); A = ap.parse_args()
    D = pd.read_parquet(f"{TMP}/pairs.parquet")
    if A.limit: D = D.groupby("setup").head(A.limit)
    t = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close"], filters=[("date", ">=", LO), ("date", "<=", HI), ("ticker", "in", sorted(set(D.winner) | set(D.loser)))]).to_pandas()
    assert t.date.max() <= HI
    for tk, g in t.drop_duplicates(["ticker", "date"]).sort_values("date").groupby("ticker"):
        PXD[tk] = dict(date=g.date.values.astype("datetime64[ns]"), o=g.open.values, h=g.high.values, l=g.low.values, c=g.close.values)
    del t
    recs = []
    for r in D.to_dict("records"):
        r["dir"] = os.path.join(A.out, r["setup"]); r["png"] = f"{r['pair_id']}_{r['winner']}_{r['winner_date']}_vs_{r['loser']}_{r['loser_date']}.png"
        r["winner_date"] = str(r["winner_date"]); r["loser_date"] = str(r["loser_date"]); recs.append(r)
    for s in D.setup.unique(): os.makedirs(os.path.join(A.out, s), exist_ok=True)
    with Pool(A.workers, maxtasksperchild=200) as p: sizes = list(p.imap_unordered(render, recs, chunksize=8))
    # index.md per setup
    for s in D.setup.unique():
        L = [f"# {s} — winner vs loser pairs (PRACTICE 2020–24 HINT)", "", "Diff-table row = `pair_id` in `pair_diffs.csv.gz`.", "", "| pair_id (diff-table row) | winner | loser | items differing | chart |", "|---|---|---|---|---|"]
        for r in recs:
            if r["setup"] == s: L.append(f"| {r['pair_id']} | {r['winner']} {r['winner_date']} | {r['loser']} {r['loser_date']} | {r['n_items_differ']} | [png]({r['png']}) |")
        open(os.path.join(A.out, s, "index.md"), "w").write("\n".join(L) + "\n")
    print("pngs", len(sizes), "bytes", sum(sizes), "mean", np.mean(sizes))
if __name__ == "__main__": main()

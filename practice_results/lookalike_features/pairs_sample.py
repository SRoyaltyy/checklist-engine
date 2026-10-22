#!/usr/bin/env python3
"""PAIRS_SAMPLE_20.pdf: 20 random fixed (v2) pairs from pair_diffs.csv.gz, seed 20261023, spread across setups (5 per setup).
PRACTICE 2020-24 HINT only. Charts via charts.side(); stories use bars < D only; EXIT_RULE_V1 recomputed per stock
(entry open D, +20% TP gap-fills at open, no stop, close of day 15, 30bp/side), bars <= 2024-12-31."""
import os, sys, numpy as np, pandas as pd, pyarrow.parquet as pq
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charts; from build import PX, PX_SHA, LO, HI, sha
SEED, PER = 20261023, 5
assert sha(PX) == PX_SHA
here = os.path.dirname(os.path.abspath(__file__))
D = pd.read_csv(f"{here}/pair_diffs.csv.gz")
S = pd.concat([D[D.setup == s].sample(PER, random_state=SEED) for s in sorted(D.setup.unique())]).sort_values(["setup", "pair_id"])
tk = sorted(set(S.winner) | set(S.loser))
t = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close"], filters=[("date", ">=", LO), ("date", "<=", HI), ("ticker", "in", tk)]).to_pandas()
assert t.date.max() <= HI
for k, g in t.drop_duplicates(["ticker", "date"]).sort_values("date").groupby("ticker"):
    charts.PXD[k] = dict(date=g.date.values.astype("datetime64[ns]"), o=g.open.values, h=g.high.values, l=g.low.values, c=g.close.values)
def exit_v1(p, i):
    o0 = p["o"][i]; tgt = o0 * 1.2
    if i + 15 > len(p["c"]): return None, "not enough bars"
    for k in range(15):
        j = i + k
        if p["h"][j] >= tgt: return (max(p["o"][j], tgt) / o0 - 1 - 0.006) * 100, f"hit +20% on day {k+1}"
    return (p["c"][i + 14] / o0 - 1 - 0.006) * 100, "sold at day-15 close"
def pct(a, b): return (b / a - 1) * 100
def story(p, i):
    c, o = p["c"][:i], p["o"][:i]  # bars before D only
    if len(c) < 60: return "not much history before the cutoff"
    m2, m1, w2 = pct(c[-42], c[-1]), pct(c[-21], c[-1]), pct(c[-10], c[-1])
    hi = c[-126:].max(); dh = pct(hi, c[-1]); vol = np.std(np.diff(np.log(c[-20:]))) * 100
    red = int((c[-10:] < o[-10:]).sum())
    def mv(x, span):
        if x <= -25: return f"crashed {abs(x):.0f}% over {span}"
        if x <= -8: return f"fell {abs(x):.0f}% over {span}"
        if x >= 25: return f"shot up {x:.0f}% over {span}"
        if x >= 8: return f"rose {x:.0f}% over {span}"
        return f"went roughly sideways over {span} ({x:+.0f}%)"
    s = [mv(m2, "the 2 months before")]
    s.append(f"then {'kept falling' if w2 <= -5 else 'bounced' if w2 >= 5 else 'went quiet'} in the last 2 weeks ({w2:+.0f}%)")
    s.append(f"{red} of the last 10 days were red")
    s.append("sitting right at its 6-month high" if dh > -5 else f"{abs(dh):.0f}% below its 6-month high")
    s.append("very jumpy" if vol > 5 else "fairly jumpy" if vol > 2.5 else "calm")
    return "; ".join(s) + "."
out = f"{here}/PAIRS_SAMPLE_20.pdf"
with PdfPages(out, metadata={"Title": "Look-alike pairs sample (PRACTICE 2020-24 HINT)", "CreationDate": None, "ModDate": None}) as pdf:
    fig = plt.figure(figsize=(11.7, 8.3)); fig.text(0.05, 0.9, "Look-alike pairs: 20-pair spot check", fontsize=20, weight="bold")
    fig.text(0.05, 0.84, "PRACTICE 2020–24 HINT DATA ONLY. No 2025+ data used.", fontsize=13, color="#c00")
    fig.text(0.05, 0.25, "\n".join([f"Source: pair_diffs.csv.gz (fixed v2 pairing, {len(D):,} pairs). Random pick: seed {SEED}, {PER} per setup ({', '.join(sorted(S.setup.unique()))}).",
        "Each page: same setup, same day, two look-alike stocks. Left = the winner, right = the loser (by the 10-day label).",
        "Story at top uses only the days BEFORE the dashed line (cutoff D). Buy = open of day D. Shaded yellow = what happened after.",
        "10-day result: net % after 30bp/side fees, and 'vs avg' = excess over matched controls (the label).",
        "EXIT_RULE_V1: sell at +20% if hit (gap fills at open), no stop, otherwise sell at day-15 close, 30bp/side.",
        "Chart panels: candles + moving averages (SMA5–200) + Bollinger band, RSI14, MACD. Green/red shading = up/down day runs.",
        "Question to ask on each page: do the two charts really look alike before the line? If yes, the pairing did its job."]), fontsize=10.5)
    pdf.savefig(fig); plt.close(fig)
    for n, r in enumerate(S.to_dict("records"), 1):
        fig = plt.figure(figsize=(11.7, 8.3))
        gs = fig.add_gridspec(3, 2, height_ratios=[3, 1, 1], left=0.05, right=0.99, top=0.76, bottom=0.2, hspace=0.08, wspace=0.12)
        res = []
        for col, side in ((0, "winner"), (1, "loser")):
            a0 = fig.add_subplot(gs[0, col]); axs = [a0, fig.add_subplot(gs[1, col], sharex=a0), fig.add_subplot(gs[2, col], sharex=a0)]
            T, d = r[side], str(r[f"{side}_date"]); charts.side(axs, T, d, f"{'WINNER' if side=='winner' else 'LOSER'}: {T}, buy at open {d}")
            p = charts.PXD[T]; i = int(np.searchsorted(p["date"], np.datetime64(d)))
            ev, how = exit_v1(p, i); n10, x10 = r[f"{side}_net10_pct"], r[f"{side}_ex10_pct"]
            res.append((T, story(p, i), n10, x10, ev, how))
        fig.text(0.05, 0.955, f"Pair {n}/20 · {r['pair_id']} · setup {r['setup']} · PRACTICE 2020–24 HINT", fontsize=11, weight="bold")
        for k, (T, st, *_ ) in enumerate(res):
            fig.text(0.05, 0.915 - k * 0.07, f"{'Winner' if k==0 else 'Loser'} {T} before buying: {st}", fontsize=9, wrap=True)
        for k, (T, st, n10, x10, ev, how) in enumerate(res):
            wl = "WIN" if x10 > 0 else "LOSS"
            e = "n/a" if ev is None else f"{ev:+.1f}% ({'WIN' if ev > 0 else 'LOSS'}, {how})"
            fig.text(0.05, 0.12 - k * 0.04, f"{'Winner' if k==0 else 'Loser'} {T}: 10-day {n10:+.1f}% net, {x10:+.1f}% vs avg → {wl} on 10-day label | EXIT_RULE_V1: {e}", fontsize=9.5)
        fig.text(0.05, 0.025, f"Items differing between the two: {r['n_items_differ']} of {r['n_items_both_answered']} answered. HINT data, not a live result.", fontsize=7.5, color="#555")
        pdf.savefig(fig); plt.close(fig)
print(out); print(S[["pair_id", "winner", "loser"]].to_string())

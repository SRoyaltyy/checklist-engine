#!/usr/bin/env python3
"""Case-card generator — PRACTICE 2020–24, HINT only. Never reads 2025+ rows (filtered on load + asserted).
Signals from the frozen HINT panel (story_q.py build; features use bars < D; entry open[D]; exit open[D+h]; net = gross - 0.60%).
Usage: make_cards.py --q sq8_above_last_red_high [--base all6] [--h 5 10 21] [--primary 10] [--n 20] [--seed 7]"""
import argparse, hashlib, os, sys, numpy as np, pandas as pd, pyarrow.parquet as pq
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
HB = "/workspace/ce_repo/practice_results/hint_scan_2020_24"; sys.path.insert(0, HB)
PX = "/workspace/pricehist/universe_2020_survivors.parquet"; PX_SHA = "fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337"
PANEL = "/workspace/state_test/story_q/panel.parquet"
LO, HI = pd.Timestamp("2020-01-01"), pd.Timestamp("2024-12-31")
SQ = ["sq1_lower_highs3", "sq2_higher_lows3", "sq3_shrinking_green3", "sq4_below_mid_5of10", "sq5_big_red_recent",
      "sq6_dip_vol_lower", "sq7_lowerbb_reclaim", "sq8_above_last_red_high", "sq9_breakdown_vol"]
HARD = ["cp_mid_slope_up", "cp_gr_body20_ge_0p9", "cp_pctB_ge_0p12", "cp_dip_atr_le_4p2", "cp_days_since_h20_in_5_18", "cp_dd_vs_run_ge_0p5"]
COST = 0.006

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

def load_px(tk):
    p = pq.read_table(PX, columns=["ticker", "date", "open", "high", "low", "close", "volume"],
                      filters=[("ticker", "==", tk), ("date", ">=", LO), ("date", "<=", HI)]).to_pandas()
    assert len(p) == 0 or (p.date.max() <= HI and p.date.min() >= LO), "2025+ row leaked"
    return p.drop_duplicates("date").sort_values("date").reset_index(drop=True)

def chart(px, i, hs, title, path, entry_yes):
    a, b = max(0, i - 60), min(len(px), i + 22); w = px.iloc[a:b].reset_index(drop=True); k = i - a
    full = px.close.rolling(20); mid = full.mean().iloc[a:b].values; lb = (full.mean() - 2 * full.std(ddof=0)).iloc[a:b].values
    fig, ax = plt.subplots(figsize=(7, 3.2), dpi=72); x = np.arange(len(w))
    up = w.close >= w.open; col = np.where(up, "#2a9d4b", "#d23c3c")
    ax.vlines(x, w.low, w.high, color=col, lw=0.7)
    ax.bar(x, (w.close - w.open).abs().clip(lower=1e-9), bottom=np.minimum(w.open, w.close), color=col, width=0.7)
    ax.plot(x, mid, color="#3366cc", lw=0.9, label="mid (20d SMA)"); ax.plot(x, lb, color="#888", lw=0.9, ls="--", label="lower band (−2σ)")
    ax.axvspan(k - 0.5, len(w) - 0.5, color="#fff3c4", alpha=0.5, zorder=0)
    ax.scatter([k], [w.open[k]], marker="^", color="k", zorder=5, s=30, label="entry open D")
    for h, m in zip(hs, ["o", "s", "D"]):
        if k + h < len(w): ax.scatter([k + h], [w.open[k + h]], marker=m, facecolor="none", edgecolor="purple", zorder=5, s=30); ax.annotate(f"{h}d", (k + h, w.open[k + h]), fontsize=6, color="purple")
    t = list(range(0, len(w), 15)); ax.set_xticks(t); ax.set_xticklabels([w.date[j].strftime("%y-%m-%d") for j in t], fontsize=6)
    ax.tick_params(axis="y", labelsize=6); ax.set_title(title + "  | PRACTICE 2020–24 HINT", fontsize=7); ax.legend(fontsize=5, loc="upper left")
    fig.tight_layout(); fig.savefig(path, dpi=72); plt.close(fig)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--q", required=True); ap.add_argument("--base", default="none", choices=["none", "all6"])
    ap.add_argument("--h", type=int, nargs="+", default=[5, 10, 21]); ap.add_argument("--primary", type=int, default=10)
    ap.add_argument("--n", type=int, default=20); ap.add_argument("--seed", type=int, default=7); ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    A = ap.parse_args(); assert A.q in SQ
    s = sha(PX); assert s == PX_SHA, f"price file sha mismatch {s}"
    M = pq.read_table(PANEL, filters=[("date", ">=", LO), ("date", "<=", HI)]).to_pandas(); assert M.date.max() <= HI and M.date.min() >= LO
    M["base"] = (M[HARD].values == 2).all(1) if A.base == "all6" else True
    rk = [f"r{h}" for h in A.h]; P = f"r{A.primary}"
    for h in A.h: M[f"x{h}"] = M[f"r{h}"] - M.groupby("date")[f"r{h}"].transform("mean")
    sig = M.base & M[A.q]; ctl = M.base & ~M[A.q]
    tag = f"{A.q}" + ("__in_all6" if A.base == "all6" else "__all_names"); od = os.path.join(A.out, tag); os.makedirs(od, exist_ok=True)
    pop = {h: M.loc[sig, f"r{h}"].dropna() for h in A.h}; popx = {h: M.loc[sig, f"x{h}"].dropna() for h in A.h}
    S = M[sig & M[P].notna()]; rng = np.random.default_rng(A.seed)
    win = S[S[P] > 0]; los = S[S[P] <= 0]; nw = A.n // 2
    pick = pd.concat([win.sample(nw, random_state=A.seed), los.sample(A.n - nw, random_state=A.seed)]).sort_values("date")
    C = M[ctl & M[P].notna()]; Cg = C.groupby("date")
    rows = []
    for j, r in enumerate(pick.itertuples()):
        g = Cg.get_group(r.date); c = g.iloc[rng.integers(len(g))]
        px = load_px(r.ticker); i = int(np.where(px.date.values == np.datetime64(r.date))[0][0])
        # sanity: recompute net from raw prices
        for h in A.h:
            if i + h < len(px): assert abs(px.open[i + h] / px.open[i] - 1 - COST - getattr(r, f"r{h}")) < 1e-6
        yes = [q for q in SQ if getattr(r, q)]
        d = dict(case=j + 1, ticker=r.ticker, setup_date_D=r.date.date(), answers_use_bars_before=r.date.date(), questions_yes=";".join(yes),
                 base_all6=bool(r.base) if A.base == "all6" else "", entry_open_D=round(px.open[i], 4))
        for h in A.h:
            v = getattr(r, f"r{h}"); d[f"net{h}%"] = round(v * 100, 2) if pd.notna(v) else None
            cv = c[f"r{h}"]; d[f"ctl{h}%"] = round(cv * 100, 2) if pd.notna(cv) else None
            d[f"excess{h}%"] = round((v - cv) * 100, 2) if pd.notna(v) and pd.notna(cv) else None
            d[f"res{h}"] = "WIN" if pd.notna(v) and v > 0 else ("LOSE" if pd.notna(v) else "")
        d["control_ticker"] = c.ticker
        png = f"{j + 1:02d}_{r.ticker}_{r.date.date()}_{d[f'res{A.primary}']}.png"; d["chart"] = png
        chart(px, i, A.h, f"{tag} | {r.ticker} D={r.date.date()} | net{A.primary}={d[f'net{A.primary}%']}% {d[f'res{A.primary}']} vs ctl {c.ticker}", os.path.join(od, png), True)
        rows.append(d)
    T = pd.DataFrame(rows); T.to_csv(os.path.join(od, "cases.csv"), index=False)
    L = [f"# Case cards — {tag} — PRACTICE 2020–24, HINT only (not evidence; 2025–26 sealed)", "",
         f"Prices `universe_2020_survivors.parquet` sha `{PX_SHA[:8]}…{PX_SHA[-5:]}` (verified), rows 2020-01-01..2024-12-31 only (asserted). Signals from frozen HINT panel (story_q.py `…bfbca9`).",
         f"Question `{A.q}`; base filter `{A.base}`; horizons {A.h}; primary {A.primary}d; N={A.n}; seed={A.seed}. Answers use bars < D; entry = open D; exit = open D+h; net of 30bp/side.",
         "Sample is **stratified** (half winners, half losers at the primary horizon), so the card win rate is 50% by design — use the population line below for the real rate.",
         f"Control = random same-day stock-day passing the same base filter with `{A.q}` = NO. Excess = card net − control net.", "", "## Population summary (all matching stock-days)", "",
         "| h | n | win% | mean net% | median net% | mean excess vs same-day all% |", "|---|---|---|---|---|---|"]
    summ = []
    for h in A.h:
        p = pop[h]; L.append(f"| {h} | {len(p):,} | {(p > 0).mean() * 100:.1f} | {p.mean() * 100:.2f} | {p.median() * 100:.2f} | {popx[h].mean() * 100:+.2f} |")
        summ.append(f"{h}d n={len(p):,} win={(p > 0).mean() * 100:.1f}% mean={p.mean() * 100:.2f}% exc={popx[h].mean() * 100:+.2f}%")
    L += ["", "## Cards", "", "| # | ticker | D | yes | " + " | ".join(f"net{h}% | ex{h}% | {h}d" for h in A.h) + " | ctl | chart |",
          "|" + "---|" * (5 + 3 * len(A.h) + 1)]
    for d in rows:
        L.append(f"| {d['case']} | {d['ticker']} | {d['setup_date_D']} | {d['questions_yes'].replace('sq', 'q').replace(';', ' ')} | " +
                 " | ".join(f"{d[f'net{h}%']} | {d[f'excess{h}%']} | {d[f'res{h}']}" for h in A.h) + f" | {d['control_ticker']} | ![]({d['chart']}) |")
    open(os.path.join(od, "CASES.md"), "w").write("\n".join(L) + "\n")
    print(tag, "|", " ; ".join(summ))

if __name__ == "__main__": main()

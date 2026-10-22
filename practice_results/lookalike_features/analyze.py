#!/usr/bin/env python3
"""Look-alike win/loss mining — PRACTICE 2020-24 HINT only. Deterministic (no randomness; ties broken by ticker).
Steps: tradability filter (provisional, tradability.py) on cases AND controls -> re-score 4 rules -> per-item win-rate ranking (BH)
-> pair every winner with its nearest same-setup loser -> per-pair diffs over every sheet item -> aggregate 'differs in winner's favour' (BH)."""
import os, sys, glob, numpy as np, pandas as pd, pyarrow.parquet as pq
from scipy.stats import norm, binomtest
from scipy.stats import binom
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import PANEL, PX, PX_SHA, LO, HI, HARD, SQ, sha, TMP
from tradability import tradable
OUT = os.path.dirname(os.path.abspath(__file__)); HS = (5, 10, 21); PRIMARY = 10
CB = f"{TMP}/cb/casebook"
def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]; r = np.empty(n); r[o] = np.minimum(q, 1); return r

def main():
    assert sha(PX) == PX_SHA
    M = pq.read_table(PANEL, filters=[("date", ">=", LO), ("date", "<=", HI)]).to_pandas(); assert M.date.max() <= HI
    M["all6"] = (M[HARD].values == 2).all(1)
    if os.environ.get("OUTCOME_FILE"):  # pluggable outcome (e.g. Taskforce exit rule): parquet/csv with ticker,date,r5,r10,r21 (net returns, entry at D)
        f = os.environ["OUTCOME_FILE"]; O = pd.read_parquet(f) if f.endswith(".parquet") else pd.read_csv(f, parse_dates=["date"])
        assert O.date.max() <= HI; M = M.drop(columns=[f"r{h}" for h in HS]).merge(O[["ticker", "date"] + [f"r{h}" for h in HS]], on=["ticker", "date"], how="left")
    if os.path.exists(f"{TMP}/trad.parquet"): T = pd.read_parquet(f"{TMP}/trad.parquet")
    else:
        px = pq.read_table(PX, columns=["ticker", "date", "close", "volume"], filters=[("date", ">=", LO), ("date", "<=", HI)]).to_pandas().drop_duplicates(["ticker", "date"])
        assert px.date.max() <= HI; T = tradable(M[["ticker", "date"]], px); T.to_parquet(f"{TMP}/trad.parquet"); del px
    M = M.merge(T, on=["ticker", "date"], how="left"); M["tradable"] = M.tradable.fillna(False).astype(bool)
    F = [c for c in T if c.startswith("fail_")]
    RULES = {"chartpass_all6": (M.all6, ~M.all6, None), "q5_in_all6": (M.all6 & M.sq5_big_red_recent, M.all6 & ~M.sq5_big_red_recent, "R2"),
             "q7_in_all6": (M.all6 & M.sq7_lowerbb_reclaim, M.all6 & ~M.sq7_lowerbb_reclaim, "R3"), "q8_in_all6": (M.all6 & M.sq8_above_last_red_high, M.all6 & ~M.sq8_above_last_red_high, "R4")}
    L = ["# Look-alike win/loss mining — PRACTICE 2020–24, **HINT only** (not evidence; 2025–26 sealed until the lock)", "",
         f"Prices `universe_2020_survivors.parquet` sha `{PX_SHA[:8]}…{PX_SHA[-5:]}` (verified). Rows 2020-01-01..2024-12-31 only (asserted). Every feature uses bars < D; entry open D, exit open D+h, net of 30bp/side.",
         "Win = stock net return beats the same-day mean of tradable matched controls (same base filter, rule = NO). Deterministic: no sampling, no seed needed (ties broken by ticker).", "",
         "See `LOOKBACK_GRID.md` (fixed lookback grid, recorded before computing).", "", "## Tradability filter — Taskforce `buyable_filter_v1/drop_list_v2.csv.gz` (sha 5a6cb756…63239)", "",
         "Fullscan PREREG §6 liquid gate (avg vol ≥ 500k, vol > 0, SPAC rule) as built by Taskforce. **ETF rule PARTIAL** (only SPY/QQQ/IWM + 11 sector SPDRs). **Market cap ≥ $100M NOT YET APPLIED** (awaits SEC share counts).",
         "Applied to cases AND controls before any scoring, pairing or charting. Drop-list rows dated > 2024 discarded on read. Earlier provisional run with own filter (incl. mcap proxy) superseded.", "",
         "### Exclusions (stock-days removed; a day can fail several rules)", "", "| setup | n before | n after | removed | " + " | ".join(F) + " |", "|" + "---|" * (4 + len(F))]
    for g, (s, c, _) in RULES.items():
        S = M[s]; L.append(f"| {g} | {len(S):,} | {S.tradable.sum():,} | {(~S.tradable).sum():,} | " + " | ".join(f"{S[f].sum():,}" for f in F) + " |")
    L.append(f"| all panel rows (controls pool) | {len(M):,} | {M.tradable.sum():,} | {(~M.tradable).sum():,} | " + " | ".join(f"{M[f].sum():,}" for f in F) + " |")
    L += ["", "### Re-score of the 4 rules: before vs after the filter (raw = mean net%; exc = mean excess vs same-day all%)", "", "| rule | h | n before | win% before | raw before | exc before | n after | win% after | raw after | exc after |", "|---|---|---|---|---|---|---|---|---|---|"]
    Mt = M[M.tradable]
    for h in HS:
        M[f"xa{h}"] = M[f"r{h}"] - M.groupby("date")[f"r{h}"].transform("mean"); Mt = Mt.assign(**{f"xa{h}": Mt[f"r{h}"] - Mt.groupby("date")[f"r{h}"].transform("mean")})
    for g, (s, c, _) in RULES.items():
        for h in HS:
            a = M.loc[s, [f"r{h}", f"xa{h}"]].dropna(); b = Mt.loc[s[M.tradable], [f"r{h}", f"xa{h}"]].dropna()
            L.append(f"| {g} | {h} | {len(a):,} | {(a.iloc[:, 0] > 0).mean() * 100:.1f} | {a.iloc[:, 0].mean() * 100:.2f} | {a.iloc[:, 1].mean() * 100:+.2f} | {len(b):,} | {(b.iloc[:, 0] > 0).mean() * 100:.1f} | {b.iloc[:, 0].mean() * 100:.2f} | {b.iloc[:, 1].mean() * 100:+.2f} |")
    # events (tradable only) with matched-control excess
    ev = []
    for g, (s, c, _) in RULES.items():
        st, ct = s & M.tradable, c & M.tradable; E = M.loc[st, ["ticker", "date"] + SQ + [f"r{h}" for h in HS]].copy(); E["group"] = g
        for h in HS: E[f"ex{h}"] = E[f"r{h}"] - E.date.map(M[ct].groupby("date")[f"r{h}"].mean())
        ev.append(E)
    E = pd.concat(ev, ignore_index=True); del M, Mt
    # item matrix: all sheet items (codes 0=NR 1=NO 2=YES) + panel checks + NEW rows (tercile code 1/2/3 over the tradable pool)
    cells = pd.read_parquet(f"{TMP}/cells.parquet"); ci = pd.Index(cells.ticker + "|" + cells.date.dt.strftime("%Y-%m-%d"))
    pos = ci.get_indexer(E.ticker + "|" + E.date.dt.strftime("%Y-%m-%d")); assert (pos >= 0).all()
    blocks, names, src = [], [], []
    for k, lab in [("JG", "sheet:JG (James v8.2 ticker rows)"), ("NB", "sheet:NB (New Bot)"), ("TR", "sheet:TR (Theme Radar)"), ("SHARED", "sheet:SHARED (market rows)"), ("PB2", "path bank v2 question"), ("MPV", "master.csv price/volume row (ported formula)")]:
        z = np.load(f"{TMP}/A_{k}.npz"); blocks.append(z["A"][pos]); names += list(z["ids"]); src += [lab] * len(z["ids"])
    blocks.append(np.where(E[SQ].values, 2, 1).astype(np.uint8)); names += SQ; src += ["sheet:chart-picture v2 story Q"] * len(SQ)
    NW = pd.concat([pd.read_parquet(f"{TMP}/new.parquet"), pd.read_parquet(f"{TMP}/new2.parquet"), pd.read_parquet(f"{TMP}/grid.parquet"), pd.read_parquet(f"{TMP}/path2.parquet")], axis=1).iloc[pos].reset_index(drop=True)
    # shape template + nearest-neighbour win share (template / neighbours from 2020-22 events only; leave-one-out inside 2020-22)
    ZP = np.load(f"{TMP}/zpath.npz"); yrs = E.date.dt.year.values; exv = E[f"ex{PRIMARY}"].values
    for L_, key in ((60, "z60"), (126, "z126")):
        Z = ZP[key][pos]; sh_ = np.full(len(E), np.nan); nn_ = np.full(len(E), np.nan)
        for g in RULES:
            gi = np.flatnonzero((E.group == g).values & ~np.isnan(Z[:, 0])); tr = gi[(yrs[gi] <= 2022) & ~np.isnan(exv[gi])]
            if len(tr) < 50: continue
            T = Z[tr][exv[tr] > 0].mean(0); T = (T - T.mean()) / T.std()
            sh_[gi] = (Z[gi] * T).mean(1) / np.maximum(Z[gi].std(1), 1e-9)
            Xt = Z[tr].astype(np.float32); wt = (exv[tr] > 0).astype(np.float32); n2 = (Xt ** 2).sum(1)
            for c0 in range(0, len(gi), 2000):
                q = gi[c0:c0 + 2000]; Xq = Z[q].astype(np.float32); dd = (Xq ** 2).sum(1)[:, None] + n2[None, :] - 2 * Xq @ Xt.T
                dd[q[:, None] == tr[None, :]] = np.inf; k = np.argpartition(dd, 25, axis=1)[:, :25]; nn_[q] = wt[k].mean(1)
        NW[f"shape{L_}"] = sh_; NW[f"nn_win{L_}"] = nn_
    tc = np.zeros((len(E), NW.shape[1]), np.uint8)
    for j, col in enumerate(NW):
        v = NW[col].values; ok = ~np.isnan(v); q1, q2 = np.nanquantile(v, [1 / 3, 2 / 3]); tc[ok, j] = 1 + (v[ok] > q1) + (v[ok] > q2)
    blocks.append(tc); names += [f"{c} [NEW, tercile]" for c in NW]; src += ["lookback grid (LOOKBACK_GRID.md)" if c.startswith("grid_") else "path-level v2 / shape (LOOKBACK_GRID.md)" if c.startswith(("path2_", "shape", "nn_win")) else "NEW (not on sheet)" for c in NW]
    A = np.concatenate(blocks, 1); names = np.array(names); src = np.array(src); K = len(names)
    # 1) per-item win rate ranking: YES vs NO (NEW rows: top vs bottom tercile)
    rk = []
    for g in RULES:
        gi = (E.group == g).values
        for h in HS:
            y = E[f"ex{h}"].values; ok = gi & ~np.isnan(y); W = (y[ok] > 0).astype(np.float32); Ag = A[ok]
            isnew = (np.char.find(names, "[NEW") >= 0); hiC = np.where(isnew, 3, 2); loC = np.where(isnew, 1, 1)
            Hm = (Ag == hiC); Lm = (Ag == loC)
            nH = Hm.sum(0); nL = Lm.sum(0); wH = W @ Hm; wL = W @ Lm
            pH = wH / np.maximum(nH, 1); pL = wL / np.maximum(nL, 1); pp = (wH + wL) / np.maximum(nH + nL, 1)
            se = np.sqrt(pp * (1 - pp) * (1 / np.maximum(nH, 1) + 1 / np.maximum(nL, 1))); z = np.where((nH > 0) & (nL > 0) & (se > 0), (pH - pL) / np.where(se > 0, se, 1), 0)
            rk.append(pd.DataFrame(dict(group=g, h=h, item=names, source=src, n_yes_or_top=nH, win_yes_or_top=pH * 100, n_no_or_bottom=nL, win_no_or_bottom=pL * 100,
                                        diff_pp=(pH - pL) * 100, cohen_h=2 * np.arcsin(np.sqrt(pH)) - 2 * np.arcsin(np.sqrt(pL)), base_win=W.mean() * 100, p=2 * norm.sf(np.abs(z)), testable=(nH >= 30) & (nL >= 30))))
    R = pd.concat(rk, ignore_index=True); R = R[R.testable].copy(); R["q_bh"] = bh(R.p.values)
    R["best_bucket"] = np.where(R.diff_pp >= 0, "YES/top", "NO/bottom"); R["best_win"] = np.maximum(R.win_yes_or_top, R.win_no_or_bottom)
    R["best_n"] = np.where(R.diff_pp >= 0, R.n_yes_or_top, R.n_no_or_bottom)
    R["HINT_candidate"] = (R.best_win > 55) & (R.best_n >= 30) & (R.q_bh < 0.1)
    R.sort_values("p").to_csv(f"{OUT}/item_ranking.csv.gz", index=False, float_format="%.5g")
    # 1b) per sentence: frequency among winners vs losers (tradable events, h=PRIMARY), global BH over every item x setup
    fq = []
    for g in RULES:
        gi = (E.group == g).values; y = E[f"ex{PRIMARY}"].values; ok = gi & ~np.isnan(y); W = y[ok] > 0; Ag = A[ok]
        isnew = (np.char.find(names, "[NEW") >= 0); hiC = np.where(isnew, 3, 2)
        Wf = W.astype(np.float32); Lf = (~W).astype(np.float32); K_ = Ag.shape[1]; nw, nl, yw, yl = (np.zeros(K_) for _ in range(4))
        for c0 in range(0, K_, 1500):
            sl = slice(c0, c0 + 1500); ans = (Ag[:, sl] > 0).astype(np.float32); yes = (Ag[:, sl] == hiC[sl]).astype(np.float32)
            nw[sl] = Wf @ ans; nl[sl] = Lf @ ans; yw[sl] = Wf @ yes; yl[sl] = Lf @ yes
        pw = yw / np.maximum(nw, 1); pl = yl / np.maximum(nl, 1); pp = (yw + yl) / np.maximum(nw + nl, 1)
        se = np.sqrt(pp * (1 - pp) * (1 / np.maximum(nw, 1) + 1 / np.maximum(nl, 1))); z = np.where(se > 0, (pw - pl) / np.where(se > 0, se, 1), 0)
        fq.append(pd.DataFrame(dict(group=g, item=names, source=src, n_win=nw, yes_pct_winners=pw * 100, n_lose=nl, yes_pct_losers=pl * 100, p=2 * norm.sf(np.abs(z)), ok=(yw + yl >= 30) & (nw >= 30) & (nl >= 30))))
    FQ = pd.concat(fq, ignore_index=True); FQ = FQ[FQ.ok].drop(columns="ok"); FQ["q_bh_global"] = bh(FQ.p.values)
    FQ.sort_values("p").to_csv(f"{OUT}/sentence_freq_win_vs_loss.csv.gz", index=False, float_format="%.5g")
    # 2) pairing at primary h: every winner -> nearest loser in same setup: same date first, then nearest date; then Hamming on story Qs; then ticker
    keep = E[f"ex{PRIMARY}"].notna().values; A = A[keep]; E = E[keep].reset_index(drop=True); E["win"] = E[f"ex{PRIMARY}"] > 0
    if os.environ.get("PERMUTE_NULL"):  # audit: shuffle win labels within setup x date (seeded) -> pairing-artifact null
        rng = np.random.default_rng(20261022); w = E.win.values.copy()
        for _, ix in E.groupby(["group", "date"]).indices.items(): w[ix] = rng.permutation(w[ix])
        E["win"] = w
    cbk = set()
    for f in glob.glob(f"{CB}/R*_sample.csv"):
        c = pd.read_csv(f); cbk |= set(c.ticker + "|" + c.date)
    P = []
    Ek = (E.ticker + "|" + E.date.dt.strftime("%Y-%m-%d")).values; Eq = E[SQ].values.astype(np.int8); dn = E.date.values.astype("datetime64[D]").astype(np.int64)
    # FIXED 2026-10-22 (audit): symmetric 1:1 pairing. Old rule (winner-anchored, losers reused, tie-break on story-Q Hamming)
    # produced ~80% "winner favour" for story Qs even with shuffled win labels -> artifact, retracted. Now: same setup, SAME date,
    # winners and losers each ordered by a fixed hash of the ticker, zipped 1:1 without reuse. No tested item is used in matching.
    import zlib
    hk = np.array([zlib.crc32(t.encode()) for t in E.ticker.values], np.int64)
    for (g, d), ix in E.groupby(["group", "date"]).indices.items():
        w = ix[E.win.values[ix]]; l = ix[~E.win.values[ix]]
        w = w[np.lexsort((Ek[w], hk[w]))]; l = l[np.lexsort((Ek[l], hk[l]))]
        for a, b in zip(w, l): P.append((g, a, b, 0, int((Eq[a] != Eq[b]).sum())))
    P = pd.DataFrame(P, columns=["group", "wi", "li", "date_gap_days", "storyq_hamming"]).drop_duplicates(["group", "wi", "li"]).reset_index(drop=True)
    Aw = A[P.wi.values]; Al = A[P.li.values]; both = (Aw > 0) & (Al > 0); dif = both & (Aw != Al)
    fav = dif & (Aw > Al); unf = dif & (Aw < Al)   # winner YES/higher tercile vs loser NO/lower
    ag = []
    for g in RULES:
        m = (P.group == g).values; nf = fav[m].sum(0); nu = unf[m].sum(0); nd = nf + nu
        pv = np.array([binomtest(int(a), int(n)).pvalue if n >= 30 else np.nan for a, n in zip(nf, nd)])
        ag.append(pd.DataFrame(dict(group=g, item=names, source=src, n_pairs=m.sum(), n_differ=nd, winner_yes_loser_no=nf, winner_no_loser_yes=nu, winner_favour_pct=nf / np.maximum(nd, 1) * 100, p=pv)))
    AG = pd.concat(ag, ignore_index=True); AG = AG[AG.p.notna()].copy(); AG["q_bh"] = bh(AG.p.values)
    AG["HINT_candidate"] = (AG.winner_favour_pct > 55) & (AG.n_differ >= 30) & (AG.q_bh < 0.1)
    if os.environ.get("PERMUTE_NULL"): AG.sort_values("p").to_csv(f"{OUT}/pair_item_aggregate_NULL.csv.gz", index=False, float_format="%.5g"); print("null done"); return
    AG.sort_values("p").to_csv(f"{OUT}/pair_item_aggregate.csv.gz", index=False, float_format="%.5g")
    # honesty split: discover on pairs whose winner date is 2020-22, confirm on 2023-24 (same direction, BH over the discovered set)
    yr = E.date.dt.year.values[P.wi.values]; hs = []
    for g in RULES:
        for per, pm in (("disc", yr <= 2022), ("conf", yr >= 2023)):
            m = (P.group == g).values & pm; nf = fav[m].sum(0); nu = unf[m].sum(0)
            hs.append(pd.DataFrame(dict(group=g, item=names, source=src, per=per, nf=nf, nu=nu)))
    HS_ = pd.concat(hs).pivot_table(index=["group", "item", "source"], columns="per", values=["nf", "nu"]).reset_index()
    HS_.columns = ["group", "item", "source", "nf_conf", "nf_disc", "nu_conf", "nu_disc"]
    HS_["n_disc"] = HS_.nf_disc + HS_.nu_disc; HS_["n_conf"] = HS_.nf_conf + HS_.nu_conf; HS_ = HS_[HS_.n_disc >= 30].copy()
    HS_["fav_disc"] = HS_.nf_disc / HS_.n_disc * 100; HS_["p_disc"] = [binomtest(int(a), int(n)).pvalue for a, n in zip(HS_.nf_disc, HS_.n_disc)]
    HS_["q_disc"] = bh(HS_.p_disc.values); D1 = HS_[(HS_.q_disc < 0.1) & ((HS_.fav_disc - 50).abs() > 5)].copy()
    D1["fav_conf"] = D1.nf_conf / D1.n_conf.clip(lower=1) * 100
    D1["p_conf"] = [binomtest(int(a if f > 50 else n - a), int(n), alternative="greater").pvalue if n >= 30 else 1.0 for a, n, f in zip(D1.nf_conf, D1.n_conf, D1.fav_disc)]
    D1["q_conf"] = bh(D1.p_conf.values); D1["holds"] = (D1.q_conf < 0.1) & ((D1.fav_conf - 50) * (D1.fav_disc - 50) > 0) & ((D1.fav_conf - 50).abs() > 5) & (D1.n_conf >= 30)
    D1.sort_values("p_conf").to_csv(f"{OUT}/honesty_split.csv.gz", index=False, float_format="%.5g")
    # per-pair diff table: values of the top-40 aggregate items (per setup) that differ, + count of all differing items
    top = {g: AG[AG.group == g].sort_values("p").item.head(40).tolist() for g in RULES}; col = {n: k for k, n in enumerate(names)}
    code = {0: "NR", 1: "NO", 2: "YES", 3: "T3"}
    rows = []
    for r in P.itertuples():
        wi, li = r.wi, r.li; it = [f"{n}: W={code[A[wi, col[n]]] if not ('[NEW' in n) else 'T' + str(A[wi, col[n]])} L={code[A[li, col[n]]] if not ('[NEW' in n) else 'T' + str(A[li, col[n]])}"
                                  for n in top[r.group] if A[wi, col[n]] > 0 and A[li, col[n]] > 0 and A[wi, col[n]] != A[li, col[n]]]
        rows.append(dict(pair_id=f"{r.group}_{r.Index:06d}", setup=r.group, winner=E.ticker[wi], winner_date=E.date[wi].date(), winner_ex10_pct=round(E.ex10[wi] * 100, 2), winner_net10_pct=round(E.r10[wi] * 100, 2),
                         loser=E.ticker[li], loser_date=E.date[li].date(), loser_ex10_pct=round(E.ex10[li] * 100, 2), loser_net10_pct=round(E.r10[li] * 100, 2), date_gap_days=r.date_gap_days, storyq_hamming=r.storyq_hamming,
                         casebook=(Ek[wi] in cbk) or (Ek[li] in cbk), n_items_both_answered=int(both[r.Index].sum()), n_items_differ=int(dif[r.Index].sum()), top_items_differing=" ; ".join(it)))
    D = pd.DataFrame(rows); D.to_csv(f"{OUT}/pair_diffs.csv.gz", index=False)
    D.to_parquet(f"{TMP}/pairs.parquet")
    # report
    L += ["", f"## Pairs (h={PRIMARY}d primary): symmetric 1:1 winner–loser pairs, same setup and same date, fixed ticker-hash order, no reuse (audit fix; old winner-anchored pairing retracted)", "",
          "| setup | tradable events | winners | pairs | median items differing | casebook pairs |", "|---|---|---|---|---|---|"]
    for g in RULES:
        d = D[D.setup == g]; L.append(f"| {g} | {(E.group == g).sum():,} | {E.win[E.group == g].sum():,} | {len(d):,} | {d.n_items_differ.median():.0f} | {d.casebook.sum()} |")
    def tbl(X, cols, hdr):
        out = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
        for r in X.itertuples(): out.append("| " + " | ".join(str(getattr(r, c)) if not isinstance(getattr(r, c), float) else f"{getattr(r, c):.3g}" for c in cols) + " |")
        return out
    L += ["", "## Per sentence: how often it is YES (top tercile for NEW/grid rows) among winners vs losers (h=10d, tradable setup days; global BH over all items × setups) — `sentence_freq_win_vs_loss.csv.gz`", "",
          f"Tested: {len(FQ):,}; q<0.1: {(FQ.q_bh_global < 0.1).sum():,}. Top 12 per setup (TR `|N` duplicates hidden):", "",
          "| setup | sentence | source | YES % winners | YES % losers | n win / n lose | q (global BH) |", "|---|---|---|---|---|---|---|"]
    for g in RULES:
        for r in FQ[(FQ.group == g) & ~FQ.item.str.contains(r"\|(?:1|3|5|20|60)$")].sort_values("p").head(12).itertuples():
            L.append(f"| {g} | {r.item} | {r.source} | {r.yes_pct_winners:.1f} | {r.yes_pct_losers:.1f} | {r.n_win:,} / {r.n_lose:,} | {r.q_bh_global:.2g} |")
    L += ["", "## Honesty split (pair sign test): discover on 2020–22 pairs, confirm on 2023–24 pairs", "",
          f"Tested in discovery (n_differ ≥ 30): {len(HS_):,}. Discovered (q<0.1 BH, |favour−50| > 5pp): {len(D1):,}. **Still hold on 2023–24** (same direction, >5pp, n ≥ 30, q<0.1 BH over discovered set): **{int(D1.holds.sum()):,}**.", "",
          "| setup | item | source | disc n | disc winner-favour % | conf n | conf winner-favour % | q conf |", "|---|---|---|---|---|---|---|---|"]
    for g in RULES:
        for r in D1[(D1.group == g) & D1.holds & ~D1.item.str.contains(r"\|(?:1|3|5|20|60)$")].sort_values("p_conf").head(12).itertuples():
            L.append(f"| {g} | {r.item} | {r.source} | {int(r.n_disc)} | {r.fav_disc:.1f} | {int(r.n_conf)} | {r.fav_conf:.1f} | {r.q_conf:.2g} |")
    L += ["", "## (b) Items that most often differ in the winner's favour (pair sign test, BH across all items × setups)", "",
          f"HINT candidates (winner-favour > 55%, n_differ ≥ 30, q < 0.1): **{int(AG.HINT_candidate.sum())}** of {len(AG):,} tested.", ""]
    for g in RULES:
        X = AG[AG.group == g].sort_values("p").head(15)
        L += [f"### {g}", ""] + tbl(X, ["item", "source", "n_differ", "winner_yes_loser_no", "winner_no_loser_yes", "winner_favour_pct", "q_bh", "HINT_candidate"], ["item", "source", "n differ", "W yes/L no", "W no/L yes", "winner favour %", "q (BH)", "HINT"]) + [""]
    L += ["## (a2) Item win-rate ranking across all tradable setup days (YES vs NO; NEW rows: top vs bottom tercile), BH across all items × setups × horizons", "",
          f"HINT candidates (>55% win in the better bucket, n ≥ 30, q < 0.1): **{int(R.HINT_candidate.sum())}** of {len(R):,} tests.", ""]
    X = R.sort_values("p").head(25)
    L += tbl(X, ["group", "h", "item", "source", "n_yes_or_top", "win_yes_or_top", "n_no_or_bottom", "win_no_or_bottom", "base_win", "cohen_h", "q_bh", "HINT_candidate"], ["setup", "h", "item", "source", "n YES/top", "win% YES/top", "n NO/bottom", "win% NO/bottom", "base win%", "effect h", "q", "HINT"])
    L += ["", "### Cyrus's NEW rows (chains, 40-bar trend/drawdown, 2-month trend, red:green ratio, last green vs red body, RSI, MACD, RVOL, BB, SMA distance) — best horizon per setup", ""]
    X = R[R.source.str.contains("NEW|grid|path-level")].sort_values("p").groupby(["group", "item"]).head(1).sort_values("p").head(30)
    L += tbl(X, ["group", "h", "item", "n_yes_or_top", "win_yes_or_top", "n_no_or_bottom", "win_no_or_bottom", "cohen_h", "q_bh"], ["setup", "h", "item", "n top", "win% top", "n bottom", "win% bottom", "effect h", "q"])
    L += ["", "Files: `item_ranking.csv.gz` (every item × setup × h), `pair_item_aggregate.csv.gz`, `pair_diffs.csv.gz` (one row per pair; `top_items_differing` lists that setup's top-40 aggregate items where W and L differ: YES/NO, or T1–T3 terciles for NEW rows).",
          "Coverage: sheet items = every row answered by the universe engine for 2020–24 (JG 1,478 ticker rows incl. BUT variants, NB 614, TR 2,808 row|N keys, SHARED 8,176 market rows) + 9 chart-picture story questions; the 6 chart-pass checks are the setup itself. NR answers are skipped, never guessed. SHARED rows rarely differ within a pair because pairs share the date.", ""]
    open(f"{OUT}/RESULTS.md", "w").write("\n".join(L) + "\n"); print("done", len(D))

if __name__ == "__main__": main()

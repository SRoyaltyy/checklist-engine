"""FINDINGS_FREEZE_V1: every item x setup that passed 2020-22 discover AND 2023-24 confirm (fixed 1:1 pairing, global BH),
under the 10-day label and/or Taskforce EXIT_RULE_V1. PRACTICE 2020-24 HINT. Look-alike shape / NN rows excluded (failed)."""
import re, pandas as pd, numpy as np
CB = "/workspace/checklist_brainstorm"
T = pd.read_csv("honesty_split.csv.gz"); V = pd.read_csv("exit_v1/honesty_split.csv.gz")
cols = ["group", "item", "source", "n_disc", "fav_disc", "n_conf", "fav_conf", "q_disc", "q_conf", "holds"]
T = T[cols].add_suffix("_10d").rename(columns={"group_10d": "group", "item_10d": "item", "source_10d": "source"})
V = V[cols].add_suffix("_v1").rename(columns={"group_v1": "group", "item_v1": "item", "source_v1": "source"})
F = T.merge(V, on=["group", "item", "source"], how="outer")
F["pass_10d"] = F.holds_10d.fillna(False).astype(bool); F["pass_exit_v1"] = F.holds_v1.fillna(False).astype(bool)
F = F[(F.pass_10d | F.pass_exit_v1) & ~F.item.str.contains(r"^(?:shape|nn_win)")].copy()
pb = pd.read_csv(f"{CB}/path_bank_v2/PATH_BANK_V2.csv", dtype=str).set_index("id")
ms = pd.read_csv(f"{CB}/master.csv", dtype=str).set_index("id"); md = pd.read_csv(f"{CB}/merged_draft_v8.2.csv", dtype=str).drop_duplicates("id").set_index("id")
mp = pd.read_csv(f"{CB}/map_v5/six_bucket_map_v5_1.csv", dtype=str).set_index("row_id")
GRIDF = {"trend": "close(end)/close(start-1)-1", "redgreen": "#red/#green candles", "gchain_len": "max green-chain length", "rchain_len": "max red-chain length",
         "gchain_move": "max green-chain move", "rchain_move": "max red-chain move (abs)", "voltrend": "mean vol in window / mean vol of 20 bars before", "dist_high": "close(end)/max high in window - 1"}
def defn(it):
    b = it.replace(" [NEW, tercile]", ""); base = b.split("|")[0]
    if b in pb.index: return f"{pb.rule[b]} :: {pb.formula[b]}"
    if b in ms.index: return ms.strict_definition[b]
    if base in md.index:
        d = str(md.strict_definition[base]); n = b.split("|")[1] if "|" in b else None
        return (d.replace("{N}", n) + f" [N={n}]") if n else d
    if b in mp.index: return f"{mp.indicator[b]} ({mp.lens[b]})"
    m = re.match(r"grid_(lgE(\d+)L(\d+)|trL(\d+))_(\w+)", b)
    if m:
        w = f"window ending D-{m.group(2)} lasting {m.group(3)} bars" if m.group(2) else f"window ending D-1 lasting {m.group(4)} bars"
        return f"TOP tercile (vs bottom) of {GRIDF[m.group(5)]}; {w} (LOOKBACK_GRID.md)"
    if b.startswith(("path2_", "new_")): return f"TOP tercile (vs bottom) of {b} — definition in LOOKBACK_GRID.md / new2.py / build.py"
    if b.startswith("sq"): return f"chart-picture v2 story question {b} (state_test/story_q/STORY_QUESTIONS_V1.md)"
    return "see source sheet"
F["definition"] = F.item.map(defn)
F["coding"] = np.where(F.item.str.contains(r"\[NEW"), "top vs bottom tercile over the tradable setup pool", "YES vs NO")
best = np.where(F.pass_10d, F.fav_conf_10d, F.fav_conf_v1)
F["direction"] = np.where(best > 50, "winner-leaning (YES/top more often on the winner)", "loser-leaning (YES/top more often on the loser)")
txt = (F.item + " " + F.definition).str.lower()
F["flag_SURVIVOR_BIAS_RISK"] = txt.str.contains(r"52w|52-week|\blow\b|lows|\bhigh\b|highs|dist_high|disth|distl|dsh|dsl|maxdd|drawdown|ddrun|ddrec|recov|rngpos|\bnh\d|\bnl\d|nh20|nl20|nh60|nl60|max\(h|min\(l|dd126|maxdd40")
F["family_bigmove_highvol_loser"] = (best < 50) & txt.str.contains(r"maxup1d|maxdn1d|gapup|gapdn|natr|atr|volatil|rmove|gmove|bb_width|chain_move|ret_|retq|ret20|c/c\[|return|rngexp|bigvol|voltrend|mfi|up days")
F["q5_longer_base"] = F.item.str.startswith("path2_base_len") & (F.group == "q5_in_all6")
for p in ("10d", "v1"):
    F[f"effect_disc_pp_{p}"] = F[f"fav_disc_{p}"] - 50; F[f"effect_conf_pp_{p}"] = F[f"fav_conf_{p}"] - 50
out = F[["item", "group", "source", "definition", "coding", "direction", "pass_10d", "pass_exit_v1",
         "n_disc_10d", "fav_disc_10d", "n_conf_10d", "fav_conf_10d", "q_conf_10d", "n_disc_v1", "fav_disc_v1", "n_conf_v1", "fav_conf_v1", "q_conf_v1",
         "flag_SURVIVOR_BIAS_RISK", "family_bigmove_highvol_loser", "q5_longer_base"]].rename(columns={"group": "setup"}).sort_values(["setup", "q_conf_10d"])
out.to_csv("FINDINGS_FREEZE_V1.csv", index=False, float_format="%.4g"); print(len(out), out.pass_10d.sum(), out.pass_exit_v1.sum(), (out.pass_10d & out.pass_exit_v1).sum(), out.flag_SURVIVOR_BIAS_RISK.sum(), out.family_bigmove_highvol_loser.sum(), out.q5_longer_base.sum())
print(out.groupby(["setup", "direction"]).size())

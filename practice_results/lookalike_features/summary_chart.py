#!/usr/bin/env python3
"""Summary chart: top items by pair sign test per setup (winner-favour %), de-duplicated across TR |N variants. PRACTICE 2020-24 HINT."""
import os, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
OUT = os.path.dirname(os.path.abspath(__file__)); AG = pd.read_csv(f"{OUT}/pair_item_aggregate.csv.gz")
AG["base"] = AG.item.str.replace(r"\|\d+$", "", regex=True); AG = AG.sort_values("p").drop_duplicates(["group", "base"])
fig, axs = plt.subplots(2, 2, figsize=(13, 9), dpi=100)
for ax, (g, d) in zip(axs.flat, AG.groupby("group")):
    d = d.head(15).iloc[::-1]; ax.barh(d.base, d.winner_favour_pct - 50, left=50, color=["#2a9d4b" if v > 50 else "#d23c3c" for v in d.winner_favour_pct])
    for y, (v, n, q) in enumerate(zip(d.winner_favour_pct, d.n_differ, d.q_bh)): ax.text(max(v, 50) + 0.5, y, f"n={n} q={q:.0e}", fontsize=6, va="center")
    ax.axvline(50, color="k", lw=0.6); ax.axvline(55, color="#999", ls="--", lw=0.6); ax.set_title(g, fontsize=9); ax.tick_params(labelsize=6); ax.set_xlabel("% of differing pairs where the WINNER had YES / higher tercile", fontsize=7)
fig.suptitle("Look-alike pairs: items that most separate winners from losers (10d, tradable only) | PRACTICE 2020–24 HINT", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/summary_top_items.png", dpi=100)

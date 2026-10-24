# The 1,567 unbuilt base questions, and where each family's data comes from

**Generated 2026-10-24 by Kimi** from the engine's own plan logic (`E.tf_plan()` against
`QUESTION_TREE_v2.7.1.csv` @ `487387f`). Full per-column list: `data/unbuilt_base_questions.csv`
(columns: variant, analysis, k, N — the tree's timeframe `k x N`).

- Tree base total: **6,654**; built: **5,087**; **unbuilt: 1,567** (matches §10's "about
  1,262 columns have no data source yet" plus ~300 unwired cutoff/timeframe combos).
- History lever: 8,439 of 8,439 built — not part of this gap.

Three distinct reasons questions are unbuilt, and they matter for prioritisation:

**A. No builder yet, but the data is already in hand (bars/release) — build these first.**
Anchored VWAP, volume profile, prior pivots, unfilled gaps, Fibonacci swing, old ranges,
base-and-run, drawdown, new highs/lows, and many OHLC/EMA/SMA "17 missing" rows are just
unwired timeframe×lookback combos of families that ARE built at other cutoffs. Free source:
**our own bars** (`bars_all_le2024.parquet` + `universe_2020_survivors_le2024.parquet` in the
release). All yes/no or fixed-label, no external feed needed.

**B. External event data — free, dated sources exist.**

| Family (unbuilt cols) | Free dated source | Answer type |
|---|---|---|
| vs_theme_peers (170), vs_sector_peers (170) | SEC EDGAR full-text/index: company SIC from 10-K cover (dated by filing date) → peer groups by SIC2/SIC4; theme tags cross-walked from theme-radar's own shadow_log | fixed peer set → yes/no ("in leader's group") |
| earnings (24) | **`nasdaq_earn_2020-24.tar` already in release data-2020-24-v1** — wire the builder | yes/no + fixed set (surprise sign buckets) |
| form4 (insider, 28) | **`f4tr_insider_tags_2020_24.csv` already in release** + SEC EDGAR Form 4 raw (free, dated) | yes/no |
| halts (24) | Nasdaq Trader LULD halt/halting-history files (free, daily, dated) | yes/no + fixed set (halt reason) |
| short_interest (24) | FINRA short-interest publication (free, ~2×/month, dated) | yes/no + fixed set (decile buckets) |
| checklist_score_path (105) | theme-radar repo's own `research/shadow_log/` daily scores (internal, dated) | fixed set |

**C. No reliable free dated source — flag honestly.**

| Family (unbuilt cols) | Situation |
|---|---|
| analyst_actions (24) | Historical analyst rating/revision feeds are licensed (FactSet/Zacks/Refinitiv). Free web scraps are not point-in-time safe. Leave unbuilt or buy. |
| (remainder of "17 missing" rows) | Pure cutoff wiring for built families — no new data needed, just dial table rows. |

## Recommended order

1. **A-family builders** (pure code on existing bars — biggest win, ~900 cols, zero procurement).
2. **B-family wiring** for the two files already sitting in the release (earnings, form4) —
   ~52 columns for the cost of a parser.
3. SEC SIC peer groups (~340 cols) — one EDGAR bulk pull + quarterly refresh; peer membership
   is point-in-time safe because SIC comes from filings dated ≤ D.
4. Halts + short interest (~48 cols) — small downloads, dated.
5. Analyst actions: hold unless a licensed feed appears.

Every suggested source gives a yes/no or fixed-set answer; none requires reading free text at
answer time. Nothing here touches 2023–24 for scoring or anything from 2025 on.

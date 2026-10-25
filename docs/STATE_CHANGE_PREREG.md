# Pre-registration: the state-change study (probability today vs yesterday)

**Status:** pre-registered BEFORE any Step A results are looked at (2026-10-24).
**Origin:** Cyrus's idea (PR #5) — the day-to-day change in model probability itself is
signal. Yesterday p = 45%, today p = 60%: is that telling us something?

---

## 1. Definition

For stock s and day D (after the combining model is frozen on 2020–22):

> **Δp(s, D) = p(s, D) − p(s, D−1)**, where p is the frozen model's probability
> for the continuity cell (m=20%, h=15d, stop=none) — legacy exit rule v1.

The stock's own recent return is **residualised out first** (regress Δp on the stock's
last-5/10/20-session return; use the residual) so the input is not just momentum in disguise.

## 2. Why 2023–24 only

p only exists once the model is fitted on 2020–22 (§7b). This study is therefore tested on
2023–24 only, alongside the single final combining-model test. No tuning on 2023–24.

## 3. Which changes get tested (fixed in advance)

Grid on the residualised Δp, per stock-day where both p(s,D) and p(s,D−1) exist:

| # | Change type | Thresholds |
|---|---|---|
| 1 | Rise through a band | Δp ∈ {+5, +10, +15, +20, +30} pp |
| 2 | Fall through a band | Δp ∈ {−5, −10, −15, −20, −30} pp |
| 3 | Zero crossing | p < 50% → p ≥ 50%, and the reverse |
| 4 | Persistence | same sign Δp for k sessions, k ∈ {2, 3, 5} |

- 10 band cells + 2 crossing cells + 3 persistence cells = **13 pre-registered cells**.
- Each cell is a yes/no question in the ordinary sense: "did this stock's probability rise
  by ≥10pp since yesterday?" → trade the next open under exit rule v1.

## 4. Extra tries and pass rule

- **Extra tries:** 13 cells (× versions if the exit grid is applied to them later — count
  at that time). Negligible against 650k, but counted and reported per §11.
- **Pass rule:** identical to single questions — expected profit after fees beats the
  same-day benchmark AND clears the 5.4-SE bar with day/stock clustering and the 20-day
  block resample (whichever SE is worst). One test on 2023–24, nothing retuned.
- These cells join the world state as features only if they pass; they are never mined
  further on 2023–24.

## 5. Inputs available from Step A (no model needed)

Per §7b, the raw ingredients are already saved as ordinary questions, so the combiner's
world state includes them from the start:

- **flip counts:** how many questions turned bullish (0→1) vs bearish (1→0) for this stock
  since yesterday;
- **yesterday's price move:** up day / down day / flat as plain yes/no questions.

The state-change study layers the MODEL's probability change on top of those.

---

## 6. Addendum 2026-10-25 (Cyrus correction, 10:00/10:50 HKT): full-grid state changes

**Supersedes nothing above — extends it.** The frozen 13 cells on the continuity cell stay
exactly as registered. This addendum registers the SAME study on the full exit grid,
because the end goal is a probability per parameter tuple, not one number.

Cyrus's corrections this session: (a) no fixed exit rules — every margin 2–30%, every hold
1–30, stop-loss 2–30%+none (26,100 cells), all tested; (b) dynamic exit — sell early when
the price reaches the margin goal any time inside the hold period; (c) the deliverable is a
**state→strategy map**: for every world state, the (margin, hold, stop) tuple with the best
expected profit, plus P(win) per tuple.

Registered extensions (same 13-cell structure, same residualisation, same 2023-24-only
rule, same pass bar, all tries counted per §11):

1. **Δp on the strategy-map cell.** Let (m*,h*,stop*) = argmax-EV cell of the frozen model
   for state (s, D) (the published strategy map). Δp*(s, D) = p*(s, D) − p*(s, D−1), where
   p* is P(win) on that cell. 13 cells as in §3.
2. **Δ-strategy indicator.** yes/no: did the argmax cell change from D−1 to D? And a
   fixed-bucket version: distance moved in (m, h, stop) space ∈ {same, near (≤2 steps in
   any dim), far (>2 steps)}. 13-cell structure does not apply here — these 2 are single
   questions with the ordinary pass rule, counted as extra tries (15 total).
3. **EV-change cells.** Same 13 thresholds on ΔEV* (expected profit of the strategy-map
   cell) instead of Δp*. 13 more cells, counted.

Residualisation (§1) applies to every variant: the stock's own last-5/10/20-session return
is regressed out first, per variant.

Execution note: the strategy map and per-cell P(win) are exactly what combiner-predict
publishes (strategy_map_YYYY.parquet + predict_summary.json), so no new model fits are
needed — only post-processing on published outputs, on 2023–24, after the single frozen
combining-model test.

# Code review: trade scoring and the luck check (Kimi, 2026-10-24)

Scope: `scoring/trades.py` @ `487387f` (engine/v2.7.2.2) and `stats/luck_check.py` @
`origin/stats/luck-check`. Reviewed against METHODOLOGY.md §1, §4, §7. Verdicts below;
formula changes are NOT made here — anything that needs one is flagged as a recommendation.

---

## 1. `scoring/trades.py` — matches the methodology

**Fees (§1).** `FEE = 0.003`, applied both ways: `ret = exit*(1-0.003)/(entry*(1+0.003)) − 1`.
Correct for 30bp each way. A +20% target therefore nets ~+19.28%, not +20% — the tallies are
honest about this. ✔

**Exit rule v1 (§1).** `exit_v1`: fill at +20% the first day `high ≥ target` (a gap through
fills at that day's **open** — the methodology's execution-realism rule); otherwise exit at
the close of day 15. Both legs net of fees. ✔ Matches §4 "gaps fill at the open".

**The "not ready" rule (§4 censoring).** `ticker_trades` requires a bar on **every session
D..D+29** (15-day exit + 30-day outcome window) inside the scored window; otherwise the case
is NOT_READY and excluded, with a per-question tally. This is exactly §4's censoring, applied
uniformly at every boundary including the 2025–26 exam. ✔

**Benchmark (§4).** `add_bench`: same-day equal-weight mean of the same filtered+ready
stocks, same exit rule. SPY is reported alongside, not the bar. ✔ Frozen semantics.

**Survivor/liquidity discipline (§2).** The fullscan liquidity filter and split-fixed $100M
mcap floor are applied point-in-time via `filter_cols` + `mcap_fix` (SEC shares, latest filed
≤ t; split dates used only as units metadata per house rules). Quarantine exclusions always
honored; `mcap_suspect` names get the dollar-volume-only path (553 tickers per §2). ✔

**Concentration guard (§7).** `screen_z` clips excess returns at the 0.5/99.5 percentiles
before the z screen, and score tallies keep "share of profit from top 5% of trades" so a few
huge trades can't carry a result silently. Full `luck_check` only runs when `screen_z ≥ 3.0`,
`n ≥ 30`. ✔ Methodology-compliant and appropriately staged (cheap screen first, expensive
clustered inference only on candidates).

**One nuance, not a bug.** The clipped screen z is a *conservative upper bound* — if a result
passes even after clipping, the unclipped version isn't what carried it. Fine.

## 2. `stats/luck_check.py` — the 5.4 bar and its blind spots

**Is 5.4 right for ~650k tries?** Yes. Bonferroni for 650,660 tries at one-sided α≈1e-7
gives z ≈ 5.13–5.4 depending on the exact α convention; 5.4 is the right neighborhood and
slightly conservative. For the 58,977 default-cutoff cells the right bar is ~5.0 — so 5.4 is
conservative at Step A's resolution. ✔ (Both stated in METHODOLOGY §11.)

**The worst-of-three SE is the right construction.** `score` uses the LARGEST of:
1. naive SE (mean/√n),
2. two-way cluster-robust SE (clustered by ticker **and** by date, CGM-style),
3. a 20-trading-day block bootstrap (500 reps, seed 0, day-resampled blocks).

z = excess / max(three SEs). ✔ Answers METHODOLOGY §7 "Not independent": the same stock on
nearby days and same-day market shocks both shrink the effective sample.

**Can same-day co-movement sneak a false pass?** Mostly no: date clustering + day-block
bootstrap both attack exactly that failure mode — a theme rippling through many stocks on the
same day inflates the clustered SEs, not just the naive one.

**The residual hole (honest limitation):** theme-level correlation at horizons **longer
than 20 days**, and lead-lag structure (stock A leads stock B by a few days), are invisible
to a 20-day block bootstrap and to day-clustering. A theme can therefore contribute many
*overlapping* trades across weeks that look independent to all three SEs. With ~650k tries
and thousands of themes, the tail risk of a false pass is small but not zero.

**Recommendation (no formula change made):**
- Keep the 5.4 bar as-is — it is conservative at both resolutions.
- Add a **post-pass robustness check** for any cell that passes: recompute its SE with a
  60-day block bootstrap and with theme-industry date clustering (GICS sector as a proxy).
  Label the result by which checks it survived (§7's "softer check" labelling already allows
  this). This catches theme-sneak false passes without raising the bar for everyone.
- The exit-policy grid (26,100 cells, COMBINING_PREREG.md §2) multiplies the strategy space;
  per-cell pass claims must recompute the try count, but the state→strategy map stays a
  single-family claim — one test on 2023–24.

## 3. Interaction with the full exit grid

`exit_v1` hardcodes `TARGET=0.20, HOLD=15`. The pre-registered grid needs outcomes for all
(m, h, s) cells. The fill semantics already in `exit_v1` (target hit ⇒ fill at target/open;
window end ⇒ close) carry over parameter-for-parameter; the stop leg adds "low ≤ stop ⇒ fill
at stop/open, counted before target on the same day" (registered in COMBINING_PREREG.md §2
rule 4). This is a new scorer next to `exit_v1`, not a modification of it — Step A results at
v1 stay byte-identical.

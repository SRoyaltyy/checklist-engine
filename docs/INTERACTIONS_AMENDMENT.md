# Amendment A1 (Kimi, 2026-10-25): state × rule interactions so the strategy map varies by world state

**Status:** proposed amendment to `docs/COMBINING_PREREG.md`, committed BEFORE any combining
model is fitted. Requires War-room approval before the first fit. No code or formulas in
`scoring/combine.py` change until approval.

## Why

Stage-5 pre-review (§0c 2026-10-25 ~17:35 HKT) found the combining model as written is purely
additive:

```
pred(t, c) = alpha + trade_score(t) + rf[c] · gamma        # rf = (m/30, h/30, s/30, s_none)
```

Every term that depends on the exit cell `c` is `rf[c] · gamma`, which is **identical for all
trades**. In `surface_summary`, EV(t, c) = ts_r[t] + rf[c] · gamma_r, so the argmax over the
26,100 cells is the same cell for every (s, D). The prereg's central deliverable — the
**state → strategy map** (§7: "for every world state, the suitable exit policy") — degenerates
to one global (m, h, s). P(win) per cell is still valid; the per-state strategy choice is not.

## The amendment

Add a low-rank bilinear state × rule interaction term to both targets (logistic logit and
ridge EV):

```
pred(t, c) = alpha + trade_score(t) + rf[c] · gamma + z(t)ᵀ W rf[c]
```

- `z(t) ∈ R^r` — a per-trade state profile: the per-group score sums already computed during
  the streaming LUT pass. Groups = question partitions by data block / lever-1 family
  (candles, volume, moving_averages, …, events facets, history values), r ≈ 20–40. No new
  features are invented; z reuses the fitted per-question betas, so the interaction is a
  re-weighting of the same state, not new information.
- `W ∈ R^{r × 4}` — the only new parameters (≈ 80–160 floats), fit jointly by the same
  full-batch Adam loop. Gradients: ∂L/∂W[g,k] = Σ_t δ_t · z_g(t) · rf_k[c_t], accumulated in
  the same block passes as the existing sufficient sums. Memory and runtime unchanged
  (the one-hot design matrix is still never materialised).
- Effect: EV(t, c) now differs across cells *per trade* through z(t)ᵀ W rf[c]; argmax over
  cells is trade-dependent — the strategy map varies by world state, per the prereg.

## Discipline (unchanged from the prereg)

- Fit on 2020–21 only; 2022 check once (Brier, calibration, EV vs same-day benchmark, and now
  also: does the chosen cell's distribution vary materially with z?); 2023–24 touched once,
  after freeze. No tuning after the 2022 check.
- The interaction model is still the **single inferential object** (the state → strategy map);
  it receives exactly one 2023–24 test. No per-cell-alone claims are made from the grid.
- Fallback pre-committed: if the interaction term does not improve 2022 check Brier and
  calibration over the additive model, the additive model is frozen and this amendment is
  void — no retry loop on the check year.

## Alternatives considered (rejected for v1)

- Per-cluster gamma (K clusters × 4 params): coarser, non-smooth cluster boundaries, more
  parameters, and a clustering step that itself needs pre-registration. Kept as fallback if
  the bilinear term underfits.
- Full question-level × rule products: millions of parameters, violates the memory design.

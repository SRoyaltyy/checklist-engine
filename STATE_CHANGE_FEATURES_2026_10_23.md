# State-change features: using ΔP and answer flips as inputs — 2026-10-23 (Kimi)

Status: **proposal, green-lit by Cyrus as a two-track item; pre-registration spec still to be written.** Cross-posted as a review comment on PR #5. Companion to [METHODOLOGY_REVIEW_2026_10_23.md](METHODOLOGY_REVIEW_2026_10_23.md). This file is the durable copy for the bots.

Origin: Cyrus asked whether the *change* in the model's own output is informative — "yesterday the probability is 45%, today it's 60% — is that telling us something?" Short answer: yes, and the consecutive-day correlation the idea exploits is real. But ΔP bundles three distinct signals that must be separated, or the study will "find" the wrong one.

## The three things inside "45% → 60%"
1. **Repaged momentum (the trap).** Answers flip because price/volume moved, so ΔP is partly a deterministic transform of recent returns. Part of "P rose 15 points" just means "the stock went up yesterday." Not worthless — but it is a known factor in disguise, and any delta study must control for today's return or the result is unactionable.
2. **Setup confirmation dynamics (the prize).** *Which* questions flipped, and whether fresh confirmations predict *continuation* (momentum at setup level) or *exhaustion* (late entry — the 60% may already be priced in after the move that flipped the answers). Genuinely novel, no off-the-shelf factor equivalent, empirically decidable on the practice split.
3. **Entry timing (the freebie).** Entering on threshold *crossings* (P crosses the line from below) instead of on static levels gives an event-driven sample — one entry per state episode — which incidentally de-duplicates the clustered consecutive-day cases flagged in the methodology review (§1 there). The autocorrelation stops being only a statistical nuisance and becomes a sampling design.

## What the delta features should look like
ΔP is a step function — mostly 0, with jumps when answers flip — so **never regress on raw ΔP**. Use categorical/count forms:
- `delta_p_cat`: down / flat / up (from the combining model, once it exists)
- `n_confirm` / `n_break`: count of confirmed answers that flipped to YES / to NO today
- `streak`: consecutive days the answer bundle is unchanged
- `crossing`: P crosses the frozen threshold from below today (event study)

Test continuation and exhaustion hypotheses **both ways, in advance** — the prior is genuinely ambiguous, so both count against the luck budget.

## Sequencing (important)
- **No engine change needed for the cheap version.** Flip counts, bundle Hamming distance, and streaks are computable from Step A's output panel alone (yesterday's answer = previous row of the same ticker). Optionally add a per-row `bundle_hash` + `bundle_hamming` column at scoring time — negligible cost.
- **The true ΔP features need the combining model**, so they land *after* Steps B/C, as a second-stage study: own small pre-registered hypothesis family (cap at a few dozen cells), own slice of the luck bar, tested on 2020–22 and confirmed on 2023–24 like everything else. Log it in `dials/TAKEAWAYS.csv` as hints now.
- This is the same shape of idea as the HISTORY_LEVER (route/speed/time-since-extreme of one series) and the path bank — but applied at the full-model level. The repo already believes in path-over-snapshot at the single-series level; this extends it to the bundle.

## Track A (testable in Step B, no engine change)
Derivable from Step A output panel:
- per-question flip indicator (answer_t ≠ answer_{t−1}), split by direction
- bundle Hamming distance between consecutive days
- streak of unchanged bundle
- event-study entries on bundle-state changes (one case per episode)

## Track B (after the combiner is frozen)
- `delta_p_cat`, `crossing` events, and their interaction with `n_confirm`/`n_break`
- Event-driven sampling as the default for these cells (fixes clustering by design)
- Both continuation and exhaustion hypotheses pre-registered, both counted in the try budget

## Open items
- [ ] Pre-registered delta-feature spec (capped cell list + exact definitions) frozen before Step A — Kimi to draft.
- [ ] Log Track A/B as hint rows in `dials/TAKEAWAYS.csv`.
- [ ] Decide whether Track A features are scored within Step B's existing luck-bar slice or given their own slice.

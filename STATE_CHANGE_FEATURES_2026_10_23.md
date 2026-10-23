# State-change features: using ΔP and answer flips as inputs — 2026-10-23 (Kimi)

Status: **Track A pre-registered** (see [TRACK_A_STATE_CHANGE_SPEC_2026_10_23.md](TRACK_A_STATE_CHANGE_SPEC_2026_10_23.md)); Track B remains a proposal pending the combining model. Cross-posted as a review comment on PR #5. Companion to [METHODOLOGY_REVIEW_2026_10_23.md](METHODOLOGY_REVIEW_2026_10_23.md). This file is the durable copy for the bots.

Origin: Cyrus asked whether the *change* in the model's own output is informative — "yesterday the probability is 45%, today it's 60% — is that telling us something?" Short answer: yes, and the consecutive-day correlation the idea exploits is real. But ΔP bundles three distinct signals that must be separated, or the study will "find" the wrong one.

## The three things inside "45% → 60%"
1. **Repaged momentum (the trap).** Answers flip because price/volume moved, so ΔP is partly a deterministic transform of recent returns. Part of "P rose 15 points" just means "the stock went up yesterday." Not worthless — but it is a known factor in disguise, and any delta study must control for today's return or the result is unactionable.
2. **Setup confirmation dynamics (the prize).** *Which* questions flipped, and whether fresh confirmations predict *continuation* (momentum at setup level) or *exhaustion* (late entry — the 60% may already be priced in after the move that flipped the answers). Genuinely novel, no off-the-shelf factor equivalent, empirically decidable on the practice split.
3. **Entry timing (the freebie).** Entering on threshold *crossings* (P crosses the line from below) instead of on static levels gives an event-driven sample — one entry per state episode — which incidentally de-duplicates the clustered consecutive-day cases flagged in the methodology review (§1 there). The autocorrelation stops being only a statistical nuisance and becomes a sampling design.

## Track A (pre-registered; testable in Step B, no engine change)
Derivable from Step A output panel — the full spec (definitions, frozen −1 rule, 18-cell list, event sampling, luck accounting) is in [TRACK_A_STATE_CHANGE_SPEC_2026_10_23.md](TRACK_A_STATE_CHANGE_SPEC_2026_10_23.md):
- per-question flip indicators, split by direction (`flip_pos` / `flip_neg`)
- bundle Hamming distance between consecutive days
- streak of unchanged bundle; episode-day-1 event sampling as primary inference
- confirmation burst and churn indicators

## Track B (after the combiner is frozen; spec NOT yet written)
- `delta_p_cat` (down/flat/up), `crossing` events, and their interaction with `flip_pos`/`flip_neg`
- Event-driven sampling as the default for these cells (fixes clustering by design)
- Both continuation and exhaustion hypotheses pre-registered, both counted in the try budget
- **Never regress on raw ΔP** — it is a step function, mostly zero with jumps; categorical/count forms only

## Open items
- [x] Pre-registered Track A spec (capped cell list + exact feature definitions) — done, see TRACK_A_STATE_CHANGE_SPEC_2026_10_23.md.
- [ ] Log Track A/B as hint rows in `dials/TAKEAWAYS.csv`.
- [ ] Decide whether Track A features are scored within Step B's existing luck-bar slice or given their own slice (spec §7 adds 18 cells to the family-wise count; bar unchanged at 5.4σ).
- [ ] Write Track B spec after the combining model is frozen.

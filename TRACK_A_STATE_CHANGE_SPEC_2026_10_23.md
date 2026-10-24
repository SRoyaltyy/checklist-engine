# Track A pre-registration: state-change features from the Step A panel — 2026-10-23 (Kimi)

Status: **PRE-REGISTERED PROPOSAL** — frozen wording for Step B. Companion to [STATE_CHANGE_FEATURES_2026_10_23.md](STATE_CHANGE_FEATURES_2026_10_23.md) and [METHODOLOGY_REVIEW_2026_10_23.md](METHODOLOGY_REVIEW_2026_10_23.md). Track B (true ΔP / crossing features) is a separate later spec and is *not* covered here.

## 0. Why this exists
Cyrus's question: if the model's probability estimate moves (45% → 60%), is the move itself informative? Track A tests the parts of that idea that are computable from the Step A answer panel alone, with **no engine changes and no combining model**. Track A answers: "does the *pattern of checklist answers changing* predict profit?"

## 1. Data and timing semantics (read before anything else)
- Input: the Step A output panel — one row per stock per trading day D, one int8 column per question (−1 = n_a/NOT_READY), plus `ticker`, `date`, `passes_filter`, `split`.
- The engine applies `A.shift(1)`, so **row D contains answers computed from bars strictly before D**. Two design consequences:
  1. The tradeable "today" answer for a trade at day D's open **is row D** (not row D−1). This matches the base-case convention (buy at D open, answers from data < D).
  2. A "flip" between row D−1 and row D reflects information that arrived between the D−1 info-set and the D info-set. **Both rows are point-in-time; no leakage.**
- Universe: rows with `passes_filter = true` only (same tradeable universe as base scoring). Splits: discover_2020_22 for testing, check_2023_24 for confirmation, nothing changes between them.

## 2. Exact feature definitions
For each stock-day D (with row D−1 existing for the same ticker):
- `flip_pos(D)` = number of question columns whose value changed **from anything other than YES to YES** between row D−1 and row D.
- `flip_neg(D)` = number of question columns whose value changed **from YES to anything other than YES** between row D−1 and row D.
- `bundle_hamming(D)` = number of question columns whose value changed in either direction between row D−1 and row D.
- `streak(D)` = number of consecutive days up to and including D on which `bundle_hamming = 0` (resets to 1 on any change day).
- `episode_day1(D)` = 1 if `bundle_hamming(D) > 0` and `bundle_hamming(D−1) = 0` (first day of a new bundle episode), else 0.
- `confirm_burst(D)` = 1 if `flip_pos(D) ≥ 2` and `flip_neg(D) = 0`, else 0.
- `churn(D)` = 1 if `flip_pos(D) ≥ 2` and `flip_neg(D) ≥ 2`, else 0.

### −1 (NOT_READY) rule — frozen
A column contributes to a flip **only if both rows D−1 and D hold a non-−1 value** that differ. Any change involving −1 on either day is invisible to all features (we cannot distinguish "not ready" from a label change). `bundle_hamming` has no denominator: it is a raw count, deliberately.

### YES mapping
Each question column's "YES" is defined by its codebook label set in `codebook.json` at scoring time. For multi-label questions (route, stage, etc.), a change from one non-YES label to another non-YES label counts toward `bundle_hamming` and `streak`/`episode_day1` but toward **neither** `flip_pos` nor `flip_neg`. This is frozen: no attempt to rank labels by bullishness in Track A.

## 3. The pre-registered cell list — 18 cells, capped
Each cell = one feature value (or indicator) × the standard outcome test: expected profit of exit-rule-v1 trades vs the frozen same-day market benchmark, 30bp/side fees, on `passes_filter` rows.

| # | Cell | Feature values tested |
|---|---|---|
| A1a | `flip_pos` | 0, 1, 2, 3+ (4 cells) |
| A1b | `flip_neg` | 0, 1, 2, 3+ (4 cells) |
| A2 | `bundle_hamming` | 0, 1, 2, 3+ (4 cells) |
| A3 | `streak` | 1, 2–5, 6+ (3 cells) |
| A4 | `episode_day1` | =1 (1 cell; event-sampled, see §5) |
| A5 | `confirm_burst` | =1 (1 cell) |
| A6 | `churn` | =1 (1 cell) |

No other Track A cells may be added after results are seen. If a cell looks interesting in hindsight, it goes to `dials/TAKEAWAYS.csv` as a hint and waits for a future registered round.

## 4. Hypotheses and direction — both ways, counted once
The prior is genuinely ambiguous (confirmation could mean continuation *or* exhaustion), so:
- Every cell is tested **one-sided against the market benchmark**, continuation direction only ("does this feature state predict above-market expected profit?").
- The exhaustion hypothesis is the **mirror image of the same cells** (feature state predicts *below*-market profit). It is recorded from the same 18 cells as **negative warnings**, per the repo convention of keeping negative results. No extra cells are spent on it — but a strong negative warning is a first-class finding (same status as the halts / Reg SHO warnings).
- Pass criteria identical to base scoring: clears James's luck bar on discover_2020_22 (with the cluster-robust fix from review item #1 applied to *all* Track A inference), holds unchanged on check_2023_24.

## 5. Independence handling (this is why A4 exists)
- **Primary inference uses event sampling**: only rows with `episode_day1 = 1` enter the Track A significance tests. This enforces roughly one case per bundle episode per ticker, directly addressing the consecutive-day clustering problem (review item #1) by design rather than by correction.
- The full-panel versions of A1–A3, A5, A6 are reported as descriptive tallies (n, mean, distribution) but **do not** carry significance claims unless the cluster-robust bar is also cleared.

## 6. Outcome and benchmark dependencies (explicitly inherited)
Track A tallies reuse the frozen base-scoring definitions. Until those are decided (review items #2 and #3), Track A code must not be run for claims:
- outcome censoring: cases whose exit-rule-v1 or 30-day window would cross the data cut get outcome = NOT_READY and are excluded;
- market benchmark: as frozen in METHODOLOGY.md §1/§4 (pending Cyrus's pick).
Sensitivity runs may compute both candidate benchmarks (filtered-universe equal-weight vs SPY) labelled as sensitivity, not results.

## 7. Try-count accounting
Adds **18 cells** to the family-wise try count: 650,660 + 18 → the luck bar is recomputed and remains **5.4σ** (unchanged to two decimals). If Track B is later registered, its cells are added to the same running count before its results are opened.

## 8. Implementation notes (for Taskforce)
- Pure post-processing on Step A parquet output: `groupby(ticker).diff()`-style computation on int8 columns with a −1 mask. Reference sketch (~10 lines of pandas) can live in the scoring repo; it does **not** touch `engine.py`.
- If Taskforce prefers engine-side columns (`bundle_hash`, `bundle_hamming`, `flip_pos`, `flip_neg`), they are cheap to add, but post-hoc derivation is the registered default — the panel alone is sufficient.
- Track A is invisible to the 2025–26 exam until and unless a Track A cell reaches "holding" status; the exam runs base scoring first.

## 9. Ledger
Add hint rows to `dials/TAKEAWAYS.csv`: one for Track A (state-change features registered, 18 cells), one for Track B (ΔP/crossing study, spec pending, blocked on combiner).

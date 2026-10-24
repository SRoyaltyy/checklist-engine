# Pre-registration: the combining model ("world state" probability)

**Status:** pre-registered BEFORE any Step A results are looked at (2026-10-24).
**Owner corrections folded in (Cyrus, 2026-10-24 ~10:00 HKT):**
1. Exit rules are NOT fixed. A grid of exit profit margins and exit dates is tested.
2. Dynamic exit is the rule, not the exception: within the hold period, if the price reaches the
   target at any point, we sell early — the goal is already achieved.
3. The model's output is a **probability of an aggregate win**: given the world state as of the
   setup cutoff, P(this trade makes money after fees). "Aggregate win" covers both modes —
   high win rate at ordinary margin, OR lower win rate with high win margin. Expected profit
   after fees is the quantity that subsumes both modes, so it is the target.

---

## 1. What the model predicts

For stock s, setup day D, and exit policy (m, h):

> **p(s, D, m, h) = P( trade profit after fees > 0 )**
> under exit policy (m, h), given the world state at the close of D−1 plus pre-open data.

Secondary output (reported, not the pass gate):

> **E[ profit after fees ]** (ridge regression) — captures how big wins are, not just whether.

The methodology's market-beating condition stays a **pass gate on top of the probability**:
a cell/setup only counts if its realized expected profit also beats the same-day benchmark
(equal-weight filtered+ready stocks, same exit policy). SPY is reported alongside, not the bar.

## 2. Exit policies (the grid)

An exit policy is a pair (margin m, max hold h) in sessions:

- **m ∈ {10, 15, 20, 25, 30, 40} %** (profit target)
- **h ∈ {5, 10, 15, 20, 30}** sessions
- 30 cells total. Cell (20%, 15d) = legacy "exit rule v1" — kept as the continuity anchor.

**Dynamic exit semantics (identical to the existing fill logic in `scoring/trades.py`, just
parameterised — no fill-formula change):** sell at +m% the first time the target is reached;
if the stock gaps through the target, the fill is at the open of that day; if the target is
never reached, exit at the close of day h. Fees 30bp each way. All results also reported with
+20bp extra slippage. Censoring (outcome window past end of data ⇒ NOT_READY) applies per cell.

**Why the grid does not need a question re-run:** question answers (the world state) do not
depend on the exit policy. Step A's saved `answers_*.npz` + `trade_base_rows.parquet` + the
bars are sufficient; the grid only changes trade outcomes. Implementation: a scoring-side
pass over the same trade rows, one column of outcomes per cell.

## 3. World state (input features)

- Every non-junk question's yes/no answer for (s, D), straight from the saved answers:
  junk = **>95% blank**, or "yes" on **>95% or <0.5%** of days (§7b junk rule — Step A is
  not a filter; only junk is excluded, failing the 5.4 bar alone does NOT drop a question).
- Derived aggregates built as ordinary questions in Step A (separate spec):
  flip counts (questions turning bullish/bearish vs yesterday) and yesterday's price move.
- Later addition (only exists after this model is fitted): the day-to-day **change in p**,
  residualised on the stock's own recent return — see STATE_CHANGE_PREREG.md.

## 4. Fitting and time discipline (unchanged from §7b)

1. **2020–21:** shortlist + tune (regularisation strength, feature handling) on 2020–21 only.
2. **2022:** one check of named pairs and of the combining model. No further tuning after this.
3. **2023–24:** touched ONCE, for the final test, with a calibration table (predicted p vs
   realised win rate in deciles). Freeze before the 2025–26 shot.

Model form: logistic (primary), ridge on profit (secondary). Plain, regularised, no free
text, no peeking: every feature is as of D−1 close (+ pre-open), enforced by the leak test.

## 5. Win-rate floors

The old fixed floors (35/40/45/50% main 40%) become **reporting bands**, not the target:
- Mode A setups (high win rate) and Mode B setups (high margin, lower hit rate) are both
  winning modes of the same quantity, EV after fees.
- A setup qualifies on **EV after fees > 0 AND beats the same-day benchmark**, full stop.
- Floors are still reported per passing setup (and per market-cap band, per §4 execution
  realism) so nothing with a fragile 51% win rate and tiny margin hides inside an average.

## 6. Multiple testing (luck bar) accounting

- The 5.4-SE bar applies only to single-question-alone claims (unchanged).
- Exit grid: 30 cells on the SAME saved answers. Cells are correlated, but we still count
  them: the combining-model family claim must clear the bar computed with 30× the cells.
- Every pair we could have tried counts toward the bar (§7b); the named-pairs list is fixed
  in advance on the 2022 check, not mined afterwards.
- Adding flip/yesterday/state-change studies recomputes the try count per §11.

## 7. Deliverable

For every (s, D) in 2022 check and 2023–24 test: p(s, D, m, h) per cell, plus realised
outcome per cell. The "world state" readout: given everything we know at the cutoff, the
probability this trade — placed HERE — wins, for whichever exit policy we choose.

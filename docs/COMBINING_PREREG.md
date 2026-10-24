# Pre-registration: the combining model ("world state" probability)

**Status:** pre-registered BEFORE any Step A results are looked at (2026-10-24).
**Owner corrections folded in (Cyrus, 2026-10-24):**
1. Exit rules are NOT fixed and NOT a sparse grid — test every margin 2–30%, every hold
   1–30 sessions, and a stop-loss dimension (every stop 2–30% or none): 29×30×30 = 26,100
   cells. No cherry-picked points anywhere.
2. Dynamic exit is the rule, not the exception: within the hold period, if the price reaches the
   target at any point, we sell early — the goal is already achieved.
3. The model's output is a **probability of an aggregate win for every parameter tuple**:
   given the world state as of the setup cutoff, P(this trade makes money after fees) using
   margin A, hold B, stop C. "Aggregate win" covers both modes — high win rate at ordinary
   margin, OR lower win rate with high win margin. Expected profit after fees ranks the
   strategies; P(win) is the reported chance.
4. End goal: the **state → strategy map** — the suitable exit policy for every possible
   world state.

---

## 1. What the model predicts

For stock s, setup day D, and exit policy (m, h, s) — margin, max hold, stop:

> **p(s, D, m, h, s) = P( trade profit after fees > 0 )**
> under exit policy (m, h, s), given the world state at the close of D−1 plus pre-open data.

The probability is **not one number** — it is a chance for every parameter tuple: a
26,100-point surface over the strategy space for every stock-day (Cyrus: "find the suitable
strategy for every possible state").

Secondary output (reported, not the pass gate):

> **E[ profit after fees | state, m, h, s ]** (ridge regression) — needed to CHOOSE the
> strategy: rank cells by expected profit after fees, report P(win) as the chance. A cell
> with 45% wins at +20%/−2% beats one with 55% wins at +4%/−15%; only EV sees that.

The end goal is the **state → strategy map**: for each stock-day, the exit policy that
maximises expected profit after fees given its world state. The methodology's market-beating
condition stays a **pass gate on top**: a cell/setup only counts if its realized expected
profit also beats the same-day benchmark
(equal-weight filtered+ready stocks, same exit policy). SPY is reported alongside, not the bar.

## 2. Exit policies (the FULL grid — no cherry-picked points)

An exit policy is a triple (margin m, max hold h, stop s), all three swept exhaustively
(Cyrus 2026-10-24: "test all margins, not just a few numbers"; same for sell dates; add
stop-loss). **No sparse grid anywhere — every value is tested.**

- **m ∈ {2, 3, …, 30} %** — profit target, every integer from 2 to 30 (29 values)
- **h ∈ {1, 2, …, 30}** sessions — max hold, every value (30 values)
- **s ∈ {2, 3, …, 30} % ∪ {none}** — stop loss, every integer from 2 to 30 plus "no stop" (30 values)
- **29 × 30 × 30 = 26,100 cells.** Cell (20%, 15d, none) = legacy "exit rule v1" — continuity anchor.

**Dynamic exit semantics (identical in spirit to the existing fill logic in `scoring/trades.py`,
parameterised — no fill-formula change):** walk the hold window day by day in order —

1. If the day's **low ≤ stop s** first: sell at s (a gap through the stop fills at that day's open).
2. Else if the day's **high ≥ target m**: sell at m (a gap through the target fills at that day's open).
3. If the window ends with neither hit: exit at the close of day h.
4. Same-day stop-and-target both possible: count the **stop first** (conservative — the stop
   is the fill you would actually get without knowing the day's high came after the low).
5. Fees 30bp each way. All results also reported with +20bp extra slippage. Censoring
   (window past end of data ⇒ NOT_READY) applies per cell.

**Why the full grid is affordable:** the world state (answers) does not depend on exit policy,
so no question re-run — the grid only re-derives trade outcomes from bars. Computationally it
is ~26k cells over the same 2.85M trade rows, but the three parameters collapse: for each
(m, s) pair (841 of them) one vectorised pass over the 30-day path matrix finds each trade's
first-above-target day and first-below-stop day; every hold h then resolves analytically
(hit before h, censored at h, or stopped). Total work ≈ 841 passes, minutes not weeks.

**Multiple-testing accounting (important, §11):** 26,100 correlated cells. They are NOT
26,100 separate "works alone" claims — no per-cell-alone claims are made from the grid at
all. The grid is the strategy space; the single inferential object is the **state →
strategy map** (below), which gets its one test on 2023–24. Cells still count toward the
try ledger for any claim that a SPECIFIC cell works.

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
- The 26,100-cell exit grid is the strategy space, not 26,100 hypotheses: no per-cell-alone
  claims are made from it. Any claim that one SPECIFIC cell works counts it toward the bar.
- The single inferential object is the state → strategy map. It gets exactly one test on
  2023–24 (after the 2022 check), same discipline as the combining model itself.
- Every pair we could have tried counts toward the bar (§7b); the named-pairs list is fixed
  in advance on the 2022 check, not mined afterwards.
- Adding flip/yesterday/state-change studies recomputes the try count per §11.

## 7. Deliverable

For every (s, D) in the 2022 check and the 2023–24 test: the full surface
p(s, D, m, h, s) and E[profit | state, m, h, s] over all 26,100 cells, plus the realised
outcome per cell. Read two ways:

- **Chance surface:** given everything known at the cutoff, the probability this trade —
  placed HERE — wins, for every margin, hold, and stop we might choose.
- **Strategy map:** for every world state, the suitable exit policy — the (m, h, s) that
  maximises expected profit after fees — so the scanner outputs not just "buy?" but
  "buy, and manage it THIS way."

# Proposed §0b entry for the War room to paste into METHODOLOGY.md

> **2026-10-24 ~10:50 HKT (Cyrus, via Kimi): exit rules and the combining target.**
> - Exit rules are NOT fixed and NOT a sparse grid. Sweep everything: profit margins every
>   integer 2–30%, max holds every session 1–30, stop loss every integer 2–30% plus "none"
>   = 29×30×30 = 26,100 exit-policy cells. Dynamic early exit throughout: sell the moment the
>   target or stop is hit (gap-through fills at open); stop counts before target on the same
>   day; unhit windows exit at the close of day h. Cell (20%, 15d, none) = legacy exit v1.
>   No question re-run needed: answers don't depend on exit policy; the grid only re-derives
>   trade outcomes from bars (first-hit-day pass per (m,s); h resolves analytically).
> - The combining model outputs a probability PER PARAMETER TUPLE: given the world state at
>   the cutoff, P(trade profit after fees > 0 | margin A, hold B, stop C). Not one number —
>   a 26,100-point chance surface per stock-day. Expected profit after fees ranks cells (a
>   45%-win/+20% cell can beat a 55%-win/+4% cell); P(win) is the reported chance. "Aggregate
>   win" = EV after fees > 0, covering both modes (high win rate OR high margin, lower hit
>   rate). Win-rate floors become reporting bands. Market-beating stays a pass gate.
> - End goal: the **state → strategy map** — the suitable exit policy for every possible
>   world state. The 26,100 cells are the strategy space, not 26k hypotheses; the map gets
>   one test on 2023–24.
> - Full specs: docs/COMBINING_PREREG.md and docs/STATE_CHANGE_PREREG.md on branch
>   `kimi/pre-register` (pre-registered before any Step A results are examined).

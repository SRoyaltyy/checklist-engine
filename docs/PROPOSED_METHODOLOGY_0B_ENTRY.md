# Proposed §0b entry for the War room to paste into METHODOLOGY.md

> **2026-10-24 ~10:00 HKT (Cyrus, via Kimi): exit rules and the combining target.**
> - Exit rules are NOT fixed. We test a grid of exit profit margins
>   {10,15,20,25,30,40}% × max holds {5,10,15,20,30} sessions (30 cells), all with dynamic
>   early exit: if the target is reached at any point inside the hold, sell — fill at target
>   (gap-through fills at open). Cell (20%,15d) = legacy exit rule v1, kept for continuity.
>   No question re-run needed: answers don't depend on the exit policy; the grid only changes
>   trade outcomes (scoring-side pass over saved answers + trade rows + bars).
> - The combining model's output is the "world state" probability: given all inputs as of the
>   setup cutoff, P(this trade makes money after fees). "Aggregate win" = expected profit
>   after fees > 0, which covers both modes (high win rate OR high margin at lower hit rate).
>   Win-rate floors become reporting bands, not the target. Market-beating stays a pass gate.
> - Full specs: docs/COMBINING_PREREG.md and docs/STATE_CHANGE_PREREG.md on branch
>   `kimi/pre-register` (pre-registered before any Step A results are examined).

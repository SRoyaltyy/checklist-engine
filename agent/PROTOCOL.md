PROTOCOL — the wake loop

Standard. Follow in order, every wake.

1. Orient (no writing yet)
Read agent/STATE.md.
Read agent/PROGRESS.md.
Read TODO.md on main, the ## Venice section only. That is your lane and it is authoritative.
Read agent/MEMORY.md.
2. Ascertain
Compare PROGRESS.md against TODO.md. Correct PROGRESS.md where reality moved: a row claiming done with no proof becomes unproven.
If the lane in TODO.md differs from STATE.md, the lane changed. Journal it, reset STATE.md, start there.
Finish or explicitly abandon a half-done item before starting another.
3. Choose one item

First unticked row in PROGRESS.md that matches the lane. One only. Too large for one wake means split it and do the first part.

4. Work

Branch venice/<slug>. Never main. Read the docs the item names before writing code. Keep committed files marker-free.

5. Prove

Run it. A green run ID or a commit is the only proof. It goes in the PR body. No proof, the row stays unproven.

6. Record
JOURNAL.md — one line: date UTC | item | action | sha | result.
STATE.md — rewrite: lane, exact next step.
PROGRESS.md — tick or mark unproven, with evidence.
MEMORY.md — anything durable: gotchas, decisions, why a path was abandoned.
7. Stop

Stop when the item is proven, or when compaction is due. Do not start a second item to fill time.

Hard rules
Never push main. Never merge without instruction.
No CUT or BODY markers in committed files.
Tool unavailable? Use the console route. Never skip the work.
Blocked? Journal the blocker, set STATE.md to it, stop. Do not thrash.

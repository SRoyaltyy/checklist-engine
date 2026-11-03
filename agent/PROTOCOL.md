PROTOCOL — the wake loop

Standard. Follow in order, every wake. Deviating loses state.

1. Orient (no writing yet)
Read agent/STATE.md.
Read agent/PROGRESS.md.
Grep METHODOLOGY.md for your lane and for Venice. Note the lane and any new constraint.
Read TODO.md on main, ## Venice section only.
Read agent/MEMORY.md.
2. Ascertain
Compare PROGRESS.md against TODO.md. Correct PROGRESS.md where reality moved: a row claiming done with no proof becomes unproven.
If the lane in METHODOLOGY.md differs from STATE.md, the lane changed. Write that in JOURNAL.md, reset STATE.md to the new lane, and start there.
If a previous wake left an item half-finished, finish or explicitly abandon it before starting another.
3. Choose one item

First unticked row in PROGRESS.md that matches the current lane. One only. If it is too large for one wake, split it and tick the first part.

4. Work
Branch venice/<slug>. Never main.
Read the docs the item names before writing code.
Write with @@PUT. Keep committed files marker-free.
Run it. A green run ID or a commit is the only proof.
5. Prove

Put the proof in the PR body: run ID, commit sha, coverage number. No proof means the row stays unproven.

6. Record
JOURNAL.md — append one line: date UTC | item | action | sha | result.
STATE.md — rewrite: lane, exact next step.
PROGRESS.md — tick or mark unproven, with evidence.
MEMORY.md — append anything durable: gotchas, decisions, why a path was abandoned.
7. Stop

Stop when the item is proven, or when the payload is near budget and compaction is due. Do not start a second item to fill time.

Hard rules
Never push main. Never merge without instruction.
No @@CUT or @@BODY markers in committed files.
If a tool is unavailable, use the console route. Never skip the work.
If blocked, journal the blocker, set STATE.md to the blocker, stop. Do not thrash.

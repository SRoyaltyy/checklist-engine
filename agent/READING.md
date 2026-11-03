READING — what to read, and why

Read on the first wake of a new chat. Then per the protocol.

Always
File	Why
agent/STATE.md	where the work stands
agent/PROGRESS.md	lane rows, what is done and what is unproven
agent/MEMORY.md	durable notes from previous wakes
METHODOLOGY.md (grep)	authoritative lane assignment, owned by James, changes without notice
TODO.md on main, ## Venice	current orders for the lane
agent/PROTOCOL.md	how to work
Before writing code
File	Why
docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md	the plan for this lane
docs/SEC_RETAINED_IDENTITY_MAP_V1.md	retained CIK set; the .md, never the 5.3 MB JSON
docs/CBOE_SOURCE_LOCATIONS_V1.json	options source locations
docs/NO_AI_DATA_PIPELINES_V1.md	lane summary doc, also an item
existing nai-sec-* workflows	what already exists and why it 403s
When something breaks
File	Why
agent/FAILURES.md	sixteen faults with causes; check before debugging blind
agent/RECOVERY.md	console fixes for each failure mode
agent/INFRA.md	mechanics, if the fault is in the machinery
agent/PREREQS.md	what must exist; a missing binding looks like a code fault
Coordination

Other agents own other lanes and the master Gantt. Read their rows in TODO.md and GANTT_ROWS.md to avoid collisions. Never edit another lane's files. PRs from other lanes are listed in TODO.md — leave them alone.

Rules

Grep METHODOLOGY.md, never read it whole. Same for GANTT_ROWS.md if it grows. Anything over 100 KB is a grep target, not a read.

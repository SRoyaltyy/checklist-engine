REPO MAP

Where things live. Read before navigating blind.

Your files
Path	Purpose
agent/	the loop's own state and code. Yours.
agent/STATE.md PROGRESS.md JOURNAL.md MEMORY.md	state and memory
agent/BRIDGE.user.js DOORMAN.worker.js DEPLOYER.worker.js LOADER.user.js	machinery
agent/WAKE.json WAKE_PROMPT.md COMPACT.md HALT.json	loop control
agent/BRIEF.md STANDING_ORDERS.md QUEUE.jsonl TEST_LOG.txt GANTT_ROWS.md	prompt inputs
docs/	lane documentation, shared
.github/workflows/	Actions; nai-sec-* are this lane
Not yours

METHODOLOGY.md — James owns it. Read, do not edit.
TODO.md — coordination file on main. Read.
outside_calendar.py, calendar tests — parked lane, do not touch.
Any venice/calendar-announce-ledger content after dca969a.

Branches

main — protected in practice, PR only.
venice/sec-options-pipelines — current work.
venice/calendar-announce-ledger — parked, still holds pre-roll sources.

Release assets

Bulk data lands as release assets, not in git. Parquet per source, per period. Keep the repo light.

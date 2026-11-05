CONTEXT2 - the payload does not inline this file, so read it from the repo.

Supersedes the assumptions in CONTEXT.md, which was written 2026-11-03 before the harness faults.

Read order, every wake

METHODOLOGY.md, then TODO.md Venice, then STATE.md, then this file, then MEMORY2.md, then JOURNAL2.md. The payload is a stale snapshot; GitHub wins.

Where things stand, 2026-11-05T16:12Z

Loader 1.11 is written and NOT pasted. That is the gate. The paste is manual and the code is in the chat. Until it happens every wake is a holding action: the old loader still rolls a healthy bridge back every two minutes, old directives still re-run, and no scrape can be relied on.

Three faults were diagnosed and recorded. Two are fixed in 1.11. The third, wakes re-sending off a pending flag, is open.

File paths, because the originals stopped accepting writes

MEMORY.md, JOURNAL.md, PROGRESS.md and STATE.md each accepted exactly one write on 2026-11-05 and then silently refused every later one. A read of STATE.md at 16:11Z returned the 16:08 version, proving a 16:10 write was dropped. Live paths are MEMORY2, JOURNAL2, STATE2, PROGRESS and CONTEXT2. When one refuses, take the next number. Never fight a path.

Two human answers still outstanding

Whether the Tampermonkey dashboard holds an entry with "Bridge" in its name and no "Loader" — if yes it must be disabled, two instances erase each other's marker. And what the badge reads. If it does not read LOADER v1.11, the paste did not take.

Lane

TODO.md is narrowed to a thin poke: watch for a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error in a PR comment or issue, stop. Do not own the pipelines, do not push collectors, do not burn scrape quota. Calendar #96 parked. Item L1 is blocked on the harness, which is why harness work is in front.

No markers. Never push main. Never merge without instruction.

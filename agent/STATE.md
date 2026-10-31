@@BODY
State - read first on every wake

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96. Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 17:25: the doorman now takes a write in the request body. A 40,000 character file wrote and read back byte-exact, so file size no longer matters. A list op also works, and agent/ turns out to hold BRIEF.md, GOAL.md, QUEUE.jsonl, STANDING_ORDERS.md and WATERMARK.json that no wake ever carried.

Script is v3.4: writes go through the body, dispatch omits branch so it lands on main, dispatch hash includes position, and TEST_LOG.txt is in the wake reads.

Lane code is DONE. Run 41221144242 passed 19/19 and §0c cites it. Remaining: James re-reviews #96. Nothing merges before he passes. #87 separately.

put takes path, branch, text (body or query). edit takes find, replace. list takes path. Auth is k.

web_scrape exhausted. Read the repo log, never the 403 job log.

Main 162447d2.

State - read first on every wake

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96. Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 17:00: DONE with the code. Run 41221144242 passed 19/19. §0c carries the entry, the run id, the counts and the Gantt row tag. Workflow log step changed to if: always() and now pushes to the lane branch, so green runs keep their proof.

Dispatch is a console call with no branch param, which lands on main. The script sends branch=BR and so hits the stale branch workflow. The Worker put reads only the query; use op=edit with find/replace for any file too big for a URL (METHODOLOGY.md is 361KB).

Remaining: ask James to re-review #96 against the six leak-trap tests. Nothing merges until he passes. #87 merges separately after.

put takes path, branch, text. edit takes path, find, replace. Auth is k.

web_scrape exhausted. Read the repo log, never the 403 job log.

Main 3ae33db2.

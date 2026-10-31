State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 12:58: doorman contract found in the Worker source. put takes path, branch and text; content param is text, not c or content. That was the whole bug. Script is v3.1 with the real names.

Workflow restored with content at 12:56 after five runs died on a zero-byte file. Runs 41198235471, 41198595221, 41199358550, 41200533563, 41201733751 are all blank-file failures and prove nothing.

Likely cause of the original 41193103387 failure: three tests import world_timeframes, which is neither installed nor in the repo. Expect ModuleNotFoundError. Confirm from agent/TEST_LOG.txt before editing code.

web_scrape still exhausted. Only the seven READS files are readable.

Main 6638e47f, contents unread.

State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 11:47: doorman put returns {"error":"path is required"} for both POST and GET. Reads are fine. v2.7 sends a JSON body with path/content/branch plus the query aliases.

Likely cause of run 41193103387: three tests import world_timeframes, which is neither installed nor in the repo. Expect ModuleNotFoundError. Confirm from agent/TEST_LOG.txt before editing code.

Workflow written whole from the real file; deps, build and artifact steps preserved; Unit tests tees to agent/TEST_LOG.txt and commits it on failure.

web_scrape still exhausted. Only the seven READS files are readable.

Main c2137c9e, contents unread.

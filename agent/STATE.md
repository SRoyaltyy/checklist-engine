State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 11:52: doorman put takes path from the JSON body and content from the c query parameter. A v2.7 put returned 200 with no content and truncated the workflow file to zero bytes; v2.8 sends both and refuses empty writes. Confirm the workflow is not empty before dispatching.

Likely cause of run 41193103387: three tests import world_timeframes, which is neither installed nor in the repo. Expect ModuleNotFoundError. Confirm from agent/TEST_LOG.txt before editing code.

Workflow carries deps, unit tests with the tee, the failure commit, the build and the artifact steps.

web_scrape still exhausted. Only the seven READS files are readable.

Main c2137c9e, contents unread.

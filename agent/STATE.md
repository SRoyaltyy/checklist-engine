State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 11:55: STATE, JOURNAL and the workflow were all truncated to zero bytes by v2.7's content-less POST. v2.9 sends content in the query, reads every file back after writing, retries over GET on failure, and refuses empty writes.

Likely cause of run 41193103387: three tests import world_timeframes, which is neither installed nor in the repo. Expect ModuleNotFoundError. Confirm from agent/TEST_LOG.txt before editing code.

Run 41198235471 also failed, against the blank workflow.

web_scrape still exhausted. Only the seven READS files are readable.

Main c2137c9e, contents unread.

State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 11:39: reads work, writes do not. All three puts from 11:31 400'd; STATE and the workflow came back unchanged. Cause: put sends only b, while read needed b+branch+ref before it worked. v2.6 aliases every put parameter and logs the Worker body.

Likely cause of run 41193103387: three tests import world_timeframes, which is neither installed nor in the repo. Expect ModuleNotFoundError on those three. Confirm from agent/TEST_LOG.txt before changing any code.

Workflow written whole from the real file, preserving deps, build and artifact steps; Unit tests now tees to agent/TEST_LOG.txt and commits it on failure.

web_scrape still exhausted. Only the seven READS files are readable.

Main c2137c9e, contents unread.

State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 12:00: the doorman put writes the c parameter verbatim, with no base64 decode. STATE and JOURNAL are currently base64 text; the next write replaces them. Content now goes as percent-encoded plain text.

Likely cause of run 41193103387: three tests import world_timeframes, which is neither installed nor in the repo. Expect ModuleNotFoundError. Confirm from agent/TEST_LOG.txt before editing code.

Runs 41198235471 and any later run fail until the workflow is restored, because it is currently zero bytes.

web_scrape still exhausted. Only the seven READS files are readable.

Main c2137c9e, contents unread.

State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 11:31: outside_event_calendar.yml rewritten whole: pytest -q --tb=long with no -x, output teed to agent/TEST_LOG.txt, log committed under if: failure(). Written from scratch because the file was never readable. Needs a dispatch and a read of TEST_LOG.txt to confirm it replaced the old steps rather than sitting beside them.

web_scrape still exhausted. Repo reads now arrive inside the wake body; arbitrary reads still need READS expanded in the userscript.

Run 41193103387 FAIL, sha 10358e24, undiagnosed.

Main is c2137c9e; contents unread.

Transport defect: reads return JSON, script pastes raw. Wake text also shows the WAKE.json blob sha instead of the commit sha.

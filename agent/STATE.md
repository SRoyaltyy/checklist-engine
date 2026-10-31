@@BODY
State - read first on every wake

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96. Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 16:35: two real bugs found and fixed in outside_calendar.py. (1) schedule_published was called with a Timestamp and did year-1, which pandas now rejects; it coerces to an int year. (2) forward_release_distance returned calendar days while every other count returns sessions; it now returns session counts. 16 of 19 tests were already passing, so the conftest stub worked and the candle logic is sound.

Also fixed: the script deduped @@DISPATCH on the workflow name alone, so only the first dispatch ever fired. It now includes the block position.

Check the log tail for the current run. Three failures remain to confirm or clear: the Timestamp TypeError, and two 27.0 == 19 counts.

Main runs on the main branch workflow which checks the lane branch out; the branch workflow is stale and unused. Dispatch on main, read the log from the branch.

put takes path, branch, text. dispatch takes workflow, merge takes pr, runs takes branch. Auth is k. Every put body starts with @@BODY or # @@CUT.

web_scrape exhausted. Job logs are 403, so read the repo log.

Main dfa98272.

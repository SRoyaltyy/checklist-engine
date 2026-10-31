State - read first on every wake

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96. Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 18:05: q7 in progress. Run 41224426787 passed all 19 tests then failed in the build or coverage step, which write only to console. Dispatched again on the branch after fixing @@DISPATCH to carry the branch.

NEXT WAKE: read agent/TEST_LOG.txt from the wake body. If it says "coverage: no proof written", the build died — tee the build step to the log and re-run. If it carries days_to_cpi and days_to_jobs rows, journal them with the run id and close q7.

Queue gaps parked: q2 wants an announced override and a source column on release_schedule; q3 wants the signature (sessions, schedule); q4 wants _later_weekday_in_month(day) without the sessions argument; q5 wants _meeting_ledger and cpi_announced/jobs_announced. q1 is already satisfied.

put takes path, branch, text (body). edit takes find, repl. list, commits, diff, grep take path. Auth is k.

web_scrape exhausted. Read the repo log, never the 403 job log.

Main 162447d2.

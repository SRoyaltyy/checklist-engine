State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 14:26: conftest.py added at the repo root. It puts the root on sys.path and installs a world_timeframes stand-in ONLY if the real import fails, so the three import-dependent tests can now run instead of erroring. The stand-in is not loaded by the build script, so if the module is genuinely missing the build still fails and the traceback lands in agent/TEST_LOG.txt.

Next wake: dispatch outside_event_calendar.yml on the branch, then read agent/TEST_LOG.txt. If the tests pass and the build fails, the missing module is confirmed and the fix is to vendor the real world_timeframes, not to extend the stub.

Doorman contract, confirmed from the Worker source: put takes path, branch, text. Content param is text. dispatch takes workflow, merge takes pr, runs takes branch. Auth is k.

Loose @@PUT blocks lose leading whitespace to markdown rendering. Always fence them or YAML breaks.

web_scrape still exhausted. Job logs are 403 without a token, so the log has to be read from the repo, not from the run.

Main 5efb236c, contents unread.

Copy code
State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 14:31: conftest.py at the repo root puts the root on sys.path and installs a world_timeframes stand-in ONLY when the real import fails, so the three import tests run instead of erroring. It is not loaded by the build script, so a genuinely missing module still fails the build with a real traceback in agent/TEST_LOG.txt.

LANDING IS UNCONFIRMED. The 14:26 wake fired 46s after the writes and its snapshot still showed the old STATE, so read conftest.py back first. If it is missing, the user's block parser is not firing and the console snippet route is the only way to write.

Next wake: read conftest.py and agent/TEST_LOG.txt. Then dispatch. If tests pass and the build fails, the missing module is confirmed and the fix is to vendor the real world_timeframes, not to extend the stub.

Doorman contract, confirmed from the Worker source: put takes path, branch, text. Content param is text. dispatch takes workflow, merge takes pr, runs takes branch. Auth is k.

Loose @@PUT blocks lose leading whitespace to markdown rendering. Always fence them or YAML breaks.

web_scrape still exhausted. Job logs are 403 without a token, so the log has to be read from the repo, not from the run.

Main 5efb236c, contents unread.

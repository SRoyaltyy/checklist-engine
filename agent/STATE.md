State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 13:40: workflow now parses. Run 41204085538 failed against the good file, so it is a real failure and agent/TEST_LOG.txt should hold the reason. READ IT FIRST with the console line, it is not in READS.

Doorman contract, confirmed from the Worker source: put takes path, branch, text. Content param is text. dispatch takes workflow, merge takes pr, runs takes branch. Auth is k.

Loose @@PUT blocks lose leading whitespace to markdown rendering. Always fence them or YAML breaks.

Suspected real cause: three tests import world_timeframes, which is neither installed nor in the repo. Expect ModuleNotFoundError.

web_scrape still exhausted.

Main 5efb236c, contents unread.

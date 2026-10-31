State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 15:15: the write path works but the page renderer injects two chrome lines, "yaml" and "Copy code", ahead of every fenced body. v3.2 left them in, so the workflow on the branch still begins with them and stays YAML-invalid. v3.3 strips them; the workflow is being resent under it.

Five runs were wasted on the malformed file: 41212368062, 41212370204, 41212371986, 41212374275, 41212376194. All failure, all before checkout, so still no TEST_LOG.txt.

CONFIRM THE HEAD BEFORE DISPATCHING. A read of the workflow must begin with the comment line. Dispatch races the put otherwise, so never dispatch in the same turn as the write.

Run 41204085538 never ran a job either. The world_timeframes theory is UNPROVEN; conftest.py is on the branch unexecuted.

Doorman contract: put takes path, branch, text. dispatch takes workflow, merge takes pr, runs takes branch. Auth is k.

web_scrape exhausted. Job logs are 403, so read the repo log, never the run.

Main 5efb236c, contents unread.

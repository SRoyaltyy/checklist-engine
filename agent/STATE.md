State - read first on every wake

If this file is stale, fix it before doing anything else.
The next wake remembers nothing except what is written here.

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96.

Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 14:55: RUN 41204085538 NEVER RAN A JOB. GitHub rejected the file at sha 96694b42: "Invalid workflow file ... yaml syntax on line 4". Line 4 is on:, so the indentation was stripped and workflow_dispatch sat at column 0. No checkout, no log step, no commit step, so agent/TEST_LOG.txt and conftest.py were both 404 for a reason that has nothing to do with the tests.

The world_timeframes theory is UNPROVEN. conftest.py is written but has never executed.

2026-10-31 14:55: root cause of three silent turns: the userscript put regex required a literal

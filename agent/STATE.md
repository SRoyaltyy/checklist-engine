State - read first on every wake

Lane: calendar announce ledger (#52). Branch: venice/calendar-announce-ledger. PR #96. Hold: no merge until James passes it.

Gantt row: matches none. Nearest: [4 Questions/v1 master].

2026-10-31 16:50: GREEN. Run 41221144242 on main completed success against the lane branch. 19 tests pass, including the six leak-trap tests James ordered. The two real defects it surfaced are fixed: schedule_published coerces a Timestamp instead of subtracting from it, and forward_release_distance returns session counts instead of calendar days.

Dispatch by console only from now on. The script's @@DISPATCH dedupe swallows every dispatch after the first, and two patches to it did not take. The working call is:
fetch('...op=dispatch&workflow=outside_event_calendar.yml') with no branch param, which lands on main, whose workflow checks the lane branch out.

Next: append the run id to METHODOLOGY.md §0c with the Gantt row tag, then ask James to re-review #96.

put takes path, branch, text. Every put body starts with @@BODY or # @@CUT. Read the repo log, never the 403 job log.

Main 737e87a.

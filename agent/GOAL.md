# Goal

Finish the announcement-ledger migration on venice/calendar-announce-ledger until tests/test_outside_calendar.py is green and the outside-event-calendar workflow passes.

James failed PR #96 at ab5a395 with four leak findings:

1. is_month_end = rank == size marks a half-finished month as month-end, then changes later.
2. days_to_fomc counts toward unscheduled meetings before they were announced.
3. release_schedule invents an announcement date from the previous release, so cancellations look known too early.
4. forward_releases filters once at the build date instead of per row.

The model that replaces them: every event carries the date it became public. Scheduled events are announced on the publication date of the annual schedule. Unscheduled FOMC meetings are announced on the day they are called. Cancellations are separate records with their own announcement date. Forward counts filter per row.

Already on the branch: the docstring, the heapq import, the schedule publication constants, and parse_fomc_historical carrying unscheduled and announced.

Do not merge. James reviews after a green run.
@@BODY

Journal - append only, newest last

One line per action: date UTC | item | action | sha | test result.

2026-10-31 16:10 | ci | first real run reached pytest: 3 failed, 16 passed | n/a | FAIL
2026-10-31 16:20 | ledger | schedule_published coerces a Timestamp to an int year | branch | fixed
2026-10-31 16:20 | ledger | forward_release_distance now returns session counts, not calendar days | branch | fixed
2026-10-31 16:30 | infra | @@DISPATCH dedupe keyed on workflow name alone; patched twice, never took | n/a | workaround
2026-10-31 16:45 | infra | dispatch moved to a console call; the block route is abandoned | n/a | works
2026-10-31 16:50 | ci | run 41221144242 completed SUCCESS, 19 passed, 0 failed | main 737e87a | PASS
2026-10-31 16:50 | ledger | lane work matches no Gantt row; nearest [4 Questions/v1 master] | n/a | n/a

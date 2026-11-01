Journal - append only, newest last

One line per action: date UTC | item | action | sha | test result.
This is the memory that survives compaction. Write the line in the same turn as the action.

2026-10-31 08:15 | ledger/1 | release_schedule docstring to the July block model | 6f406f7e | not run
2026-10-31 08:45 | infra | wake script rewritten: localStorage dedupe, draft and busy guards, pause badge, standing-orders wake text | 0934274c | n/a
2026-10-31 08:45 | infra | standing orders written | 96af37fc | n/a
2026-10-31 09:00 | infra | worker rewritten whole: heartbeat interval, UTF-8 safe encode, env repo and branch | 919c6143 | n/a
2026-10-31 09:38 | audit | first heartbeat wake; 4 GPT commits audited, row 1 65%, row 4 38% | watermark a35541a2 | n/a
2026-10-31 09:38 | infra | gantt row list and watermark written | f1806bd6, a35541a2 | n/a
2026-10-31 09:56 | ledger/2-3 | schedule_published and _cancellation_rows added; release_schedule stamps from the publication block | b71cd9f7, 9b3a76b2 | not run
2026-10-31 09:56 | ledger/4 | forward_release_distance added, per-row, heap walk | aba211b6 | not run
2026-10-31 10:02 | audit | RSI/MACD and Stochastic merges audited; row 1 corrected to 71.6% on the build-only denominator | n/a | n/a
2026-10-31 10:02 | infra | STATE.md resume file added | 7a4766ea | n/a
2026-10-31 10:12 | ledger/5 | _month_end_sessions and _later_weekday_in_month added; is_month_end reads the full index | 0e25f55a, b04a5dd1 | not run
2026-10-31 10:12 | audit | wake repeated sha 30dfc519, no new main commit; freshness window 20min > heartbeat 15min causes duplicates | n/a | n/a
2026-10-31 10:18 | infra | wake text now three steps: resume, audit, work | 43a09a8e | n/a
2026-10-31 10:19 | infra | standing orders order of operations added | 93a6a4e2 | n/a
2026-10-31 10:24 | infra | worker reports main movement only on a real sha change, stores last_main_sha | 9224e78b, 7ee59ab5 | n/a
2026-10-31 10:25 | ledger/6 | parse_fomc_calendars carries unscheduled and announced; fomc frame columns widened | 01dbc02a, 2c275933 | not run
2026-10-31 10:25 | ledger/7 | build_calendar wires forward_release_distance; one-shot filter removed | 8250f33f, 738f3675 | not run
2026-10-31 10:30 | tests/1 | stale cancellation-premise test replaced with three: publication weekend roll, cancellation override, half-built month | 10358e24 | not run
2026-10-31 10:31 | dispatch | outside_event_calendar.yml dispatched on the branch; run id not yet listed | n/a | pending
2026-10-31 10:44 | dispatch | run 41193103387 exists and FAILED at the Unit tests step; job 124513743987, sha 10358e24 | n/a | FAIL
2026-10-31 10:44 | infra | job logs are 11 403 unauthenticated; no log op in the doorman, so the failure is undiagnosed | n/a | n/a
2026-10-31 11:24 | infra | userscript v2.3: doorman reads inlined into the wake body, write blocks parsed from replies | n/a | reads work
2026-10-31 11:31 | infra | v2.4: key alias, cooldown bypass on manual wake, no silent returns | n/a | works
2026-10-31 11:31 | ci | outside_event_calendar.yml rewritten with pytest tee and failure commit | n/a | put 400
2026-10-31 11:39 | infra | v2.6: put aliases p/path/file, b/branch/ref, c/content/text/body | n/a | put 400
2026-10-31 11:47 | infra | v2.7: JSON body for put, no content in query | n/a | put 200, zero bytes
2026-10-31 11:52 | ci | STATE, JOURNAL and workflow truncated to empty by the content-less POST | n/a | FAIL
2026-10-31 11:55 | infra | v2.9: content in query, readback verification | n/a | wrote base64
2026-10-31 12:00 | infra | v3.0: plain text instead of base64 | n/a | zero bytes
2026-10-31 12:34 | ci | five runs died on the zero-byte workflow: 41198235471, 41198595221, 41199358550, 41200533563, 41201733751 | n/a | FAIL
2026-10-31 12:58 | infra | Worker source read: content param is text, path is path, branch is branch, dispatch is workflow, merge is pr. v3.1 | n/a | contract known
2026-10-31 12:58 | ci | workflow restored with content by console write, sha 4eb2a8e4 then rewritten | n/a | restored
2026-10-31 13:20 | ci | workflow restored with indentation inside a fence; log step moved first, commit step widened to if failure() | n/a | parses
2026-10-31 14:26 | tests | root conftest added: repo root on sys.path plus a guarded world_timeframes stand-in so the three import tests can run; real module still wins when present | see readback | not run
2026-10-31 14:26 | audit | all rows unchanged, no new main commit readable; TEST_LOG.txt still unread, so the stub is the test of the leading hypothesis | n/a | n/a

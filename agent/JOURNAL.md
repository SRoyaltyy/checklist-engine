Journal - append only, newest last

One line per action: date UTC | item | action | sha | test result.

2026-10-31 17:35 | q7 | branch workflow repaired after the repl fallback bug deleted the step name; log step now if: always() | 9405a3a7 | n/a
2026-10-31 17:36 | q7 | dispatched on the branch per BRIEF; run 41224766845 completed success | d73747af | PASS 19
2026-10-31 17:38 | q7 | coverage rows absent from the log: the build writes them only to the proof artifact; added a step that prints days_to_cpi and days_to_jobs | n/a | pending
2026-10-31 17:38 | infra | Worker edit takes repl per BRIEF but pick("replace") returns an empty body on GET, so repl is ignored; replace= works | n/a | known

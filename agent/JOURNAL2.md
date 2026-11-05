Journal continued. Append only, newest last. date UTC | item | action | sha | result.

MEMORY.md and JOURNAL.md both refuse a second write, so this is the live journal path. Same format, same rules.

2026-11-05T16:08Z | infra | three harness faults found and each given its own DIAG file | n/a | recorded
2026-11-05T16:20Z | infra | loader health test watched a marker a live bridge never sets, tearing down a healthy instance every 120s | n/a | fixed in 1.11
2026-11-05T16:26Z | infra | directives replayed every scan because the tail slice kept them in view, so one URL stuck | n/a | fixed in 1.11 by hash filter
2026-11-05T16:40Z | infra | wakes arriving seconds apart with one frozen payload id | n/a | opened, cause unknown
2026-11-05T16:52Z | infra | user disabled the script and asked what was happening; explained the invented percentage and the three stacked faults | n/a | user informed
2026-11-05T17:05Z | infra | agent/GUARD.user.js written, 1.01, document-start badge counter, one reload per 20s | n/a | written, unproven
2026-11-05T17:14Z | infra | cleared the WAKE.json pending flag as a test | n/a | wakes continued, flag proven inert
2026-11-05T17:18Z | infra | GUARD confirmed on disk at 1.01 by unique-URL scrape | n/a | write path proven sound, earlier miss was a delivery drop
2026-11-05T17:20Z | infra | bridge source read: POLL 30000, COOL 240000, gate is a force short-circuit | n/a | root cause found
2026-11-05T17:21Z | infra | DIAG_WAKE_FORCE_1721.md written | n/a | recorded
2026-11-05T17:22Z | infra | loader 1.12 written with the forced argument flipped to false, read back byte-exact | n/a | on disk, not pasted
2026-11-05T17:26Z | infra | STATE15 written with the paste steps and a one-edit fallback | n/a | pending human action
2026-11-05T17:27Z | infra | objective burst test given: Date.now() minus vrb.fired should climb past 60000 after the fix | n/a | awaiting paste

Open: the paste. Nothing else starts until it lands.

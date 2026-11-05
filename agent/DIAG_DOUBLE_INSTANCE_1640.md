DIAG - two bridge instances in one tab. 2026-11-05T16:40Z

Evidence, from the console paste at 16:38Z

Every wake logs "wake go: heartbeat: interval elapsed" twice in a row. Every scan that is blocked logs "bail: generating" twice. The loader logs "patched 2 spot(s)" in pairs, with a single "bridge started" early in the boot and further pairs after it. One tab, two live bridges.

Why it matters

The one-shot filter added in 1.11 keeps its marks in a single shared set on the page. With two instances, instance A marks a directive line as seen, instance B's scan then sees a line that is already marked, and B either skips it or blanks it under A. Either way the mark is consumed by the wrong instance and the net effect is the replay that 1.11 was written to remove, or a directive that fires once and then vanishes before either instance acts. Two instances also both answer the same wake, so the chat gets two prompts per heartbeat.

Probable cause

The loader has a boot-sequence guard for its own health timers but nothing that stops a second copy of the bridge body from being evaluated and started in the same page. Every re-patch that also re-starts produces another instance. A second Tampermonkey entry would do the same from outside, and that is the still-unanswered dashboard question.

Planned fix

Single-instance guard, newest boot wins. The loader stamps a fresh token into the patched body; the bridge reads it into a closure and every scan-loop iteration checks it against the live value. A stale token means a newer boot exists, so that instance stops cleanly instead of continuing to scan. Newest wins rather than first wins, because a reload or re-patch must be able to take over from a wedged instance.

Test for the fix: console shows one "wake go" per wake and one "bail" per blocked scan, and a manual reload still leaves exactly one live instance.

Open, and now blocking a clean test: whether the Tampermonkey dashboard holds a second entry with Bridge in its name and no Loader. The guard makes that entry harmless, but a clean baseline is worth having before the test.

Note on DIAG_WAKE_PAYLOAD_1141. 2026-11-05T16:55Z

WAKE.json id changed for the first time all session: 2026-11-05T16:24:43.563Z to 2026-11-05T16:40:42.585Z, set_at matching. So the pending flag was never permanently stuck. It is being rewritten by the instance that consumes a wake, and with three instances each one re-arms it, which is why wakes arrive seconds apart and why "resend stranded" appears between them.

Correction to earlier framing: "pending never clears" is wrong. The accurate statement is that pending is re-armed faster than the interval and by more than one writer, so the payload id at any wake is a snapshot of whichever instance stamped last, and the file bodies in it lag by minutes. Staleness is a symptom of the instance count, not a separate defect.

Consequence: the single-instance guard is expected to slow the wake rate back to the configured interval as well as restore the one-shot filter. Watch the id cadence after the guard lands; if wakes still arrive seconds apart with one instance, the flag is a real second defect and gets its own diagnosis.

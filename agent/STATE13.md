State 13 - read first on every wake.

Lane unchanged, from TODO.md ## Venice: thin poke. Notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error, stop. GPT owns the fix. Calendar #96 parked.

Gate: cleared. Orange LOAD v1.11 badge hides on health pass.

Fault, worsening: wakes accelerate. Gaps 17:18:44, 17:19:54, 17:20:27, 17:20:33 = 4 min, 70 s, 33 s, 6 s. WAKE.json has not been rewritten since 17:14:42 and pending stays true, so the flag is set and never cleared, and each scan submits again. The cooldown is not the lever; vrb.cool at 180000 did not hold. Do not retest the flag, it was already tested at 16:56Z and did nothing.

Consequence: each turn is cut off before its write lands. Stop writing state files every wake until this is fixed. One file per three or four wakes is enough.

Next step: read the wake function in agent/BRIDGE.user.js, delivered at 17:20Z. Look for the submit path and the pending write. The fix is to clear pending after a submit, or to gate the submit on a last-sent timestamp that survives the scan. Patch the smallest thing that stops a second submit inside the same cycle.

Known from the loader source, useful: the loader rewrites the wake call to wake(reason || 'heartbeat', true), so the second argument is the force flag. The bridge's wake() is therefore already the patched path, not the original.

Second item queued, do not start: agent/GUARD.user.js exists at 1.01, verified on disk, uninstalled. It needs a paste.

Prior state STATE.md, STATE4-12. This supersedes them.

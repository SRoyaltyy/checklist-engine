State 14 - read first on every wake.

Lane unchanged, from TODO.md ## Venice: thin poke. Notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error, stop. GPT owns the fix. Calendar #96 parked.

Loader 1.12 is on disk and verified. Readback at 17:22Z confirmed the version line, healthy(t0), unwrap(), and the get() status check. It is not installed. The paste is the only remaining step.

What 1.12 changes: the wake patch now passes false, so the bridge's 240s cooldown applies instead of being short-circuited. That is the whole burst fix. The file was also rebuilt where the earlier delivery had eaten hash(), the FILTER string, get(), and refresh().

Pass criteria after the paste: console shows patched 3, then bridge started. Badge reads LOAD v1.12. Wakes settle toward four minutes. patched 2 is acceptable, the third is the cosmetic version header. WARN filter, or EVAL FAIL, means re-paste.

Fallback if 1.12 misbehaves: the loader rolls back to last good by itself after two silent settles, so a bad paste is recoverable and leaves the current behaviour in place.

Second item queued, not started: agent/GUARD.user.js at 1.01 exists on disk and is uninstalled. With the cooldown fixed it is belt and braces rather than the main fix.

Third: read-back logging. The bridge already logs OK or MISMATCH from readback(); the loader should surface it too. Small.

Prior state STATE.md, STATE4-13. This supersedes them.

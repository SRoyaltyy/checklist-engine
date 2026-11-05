State 10 - read first on every wake.

Lane unchanged, from TODO.md ## Venice: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error, stop. GPT owns the fix. Do not own the pipelines. Calendar #96 parked.

Gate: cleared on evidence. The orange LOAD v1.11 badge hides only after healthy() passes, so its absence is the pass.

Loop health, 17:18Z: improved. One wake arrived, four minutes after WAKE.json armed, instead of three wakes seconds apart. That is consistent with the duplicate entry being gone and the cooldown of 180000 being honoured. Still to confirm from the human: whether a duplicate was found, what the installed loader version reads, and whether the gap holds across two more cycles. Do not assume 1.11 is installed until the version is reported.

Fault 1, fix in flight: three bridge instances became one, but the underlying defect stands. stopOld() finds the placeholder stop handle the loader installs on the next line, and the bridge publishes no window.__vrb.stop, so a future second boot still cannot be stopped. agent/GUARD.user.js covers that: document-start, counts instance badges, reloads the tab above one, throttled to one reload per twenty seconds.

Fault 2, partly diagnosed: wakes fired in bursts. Closed result: the pending flag does not gate a wake. I set pending false at 16:56Z and wakes continued; the bridge rewrote WAKE.json at 16:58:42 with a fresh id. Open: the cooldown key does gate it, on the evidence above. If a burst returns, read vrb.cool first.

Fault 3, open: the GUARD scrape emitted at 16:55:48Z never landed; FETCH.md still reads 2026-11-04T17:24Z. Re-issued at 17:18Z with a fresh URL.

Next step, exact

Read the GUARD delivery from FETCH.md. 200 with code means the write landed and the guard exists. 404 means writes are being lost and the write path is the problem, not the code.
If it exists, paste it: Tampermonkey, plus, new script, replace all, save, reload the Venice tab once.
Two more wake cycles. Pass is one badge, one wake go, one bail: generating.
Then the read-back check, which is the piece that makes a write trustworthy: the worker already returns a status and byte count, so compare and log OK or MISMATCH instead of guessing.

Still unanswered: duplicate entry, installed loader version, and the two-cycle gap.

Prior state STATE.md, STATE4-9. This supersedes them.

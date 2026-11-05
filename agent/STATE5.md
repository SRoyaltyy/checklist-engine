State 5 - read first on every wake.

Lane unchanged, from TODO.md ## Venice: thin poke only. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error, stop. GPT owns the fix. Do not own the pipelines. Calendar #96 parked.

Gate: cleared on evidence, not assumption. The loader badge is orange LOAD v1.11 and hide() runs only after healthy() passes, so its absence from the screen is the pass. The green wakeg15 v51 badge is the bridge's own element and never carries a loader version. Stop watching it.

Live fault: three bridge instances in one tab. Loader stopOld() is defeated twice over - it finds the placeholder stop handle the loader installs one line later, and the bridge publishes no window.__vrb.stop for a real handle to exist. Result: every wake logs wake go and bail: generating three times, and the composer sends three times.

Fix chosen, loader-side only. The loader creates its own intervals, so it can keep them in a registry that survives injection, publish a real stop handle, and have stopOld() clear every prior instance's timers and remove its badge before boot. No bridge edit, so no whole-file bridge reconstruction, which is where the last several wakes were sinking.

Next step, exact

Read the fresh LOADER4.user.js delivery from FETCH.md.
Find every setInterval and setTimeout the boot creates and the badge node it appends.
Add a window-level registry that appends each handle and node instead of overwriting.
Rewrite stopOld() to walk the registry, clearInterval, clearTimeout, remove the node, then empty it.
Delete the placeholder stop-handle line.
PUT agent/LOADER4.user.js whole, readback must read N/N OK, then confirm the console shows one wake go and one bail per wake.

Finding worth keeping: scrape raw.githubusercontent.com, never blob HTML. Raw returns JS verbatim with angle brackets intact; blob HTML converts them and truncates. Earlier deliveries were approximate for that reason, not because the channel caps.

Also unanswered, asked three times: is there a second Tampermonkey entry with "Bridge" in the name and no "Loader"? If yes, disable it.

Current files: PROGRESS.md reconciled to the narrowed lane at 16:06, landed. STATE.md rewritten, then superseded here. JOURNAL.md last line 2026-11-04T17:19Z and unconfirmed since.

While the fault stands: prefer writes over reads, do not re-send a URL inside 60s, keep the closing marker inside the message, vary a URL to defeat the debounce.

No markers in committed files. Never push main. Never merge without instruction.

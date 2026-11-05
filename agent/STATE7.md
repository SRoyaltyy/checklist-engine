State 7 - read first on every wake.

Lane unchanged, from TODO.md ## Venice: thin poke. Keep the tab and the bridge alive, notice a failed nai-sec-* or nai-occ-oi-daily run, post the run ID and the error, stop. GPT owns the fix. Do not own the pipelines. Calendar #96 parked.

Gate: cleared on evidence. The loader badge is orange LOAD v1.11 and hide() only runs after healthy() passes, so its absence from the screen is the pass. The green wakeg15 v51 badge is the bridge's own element and never carries a loader version. Stop watching it.

Fault: three bridge instances in one tab. Every wake logs wake go and bail: generating three times; the composer sends three times. Cause: stopOld() finds the placeholder stop handle the loader installs on the following line, and the bridge publishes no window.__vrb.stop, so no live handle is ever stopped.

Fix in flight: agent/GUARD.user.js, a separate document-start userscript. It counts instance badges in the DOM and reloads the tab when more than one is present, throttled to one reload per twenty seconds through sessionStorage. A reload kills every instance at once. It does not prevent the second boot, it collapses the result.

Next step, exact

Confirm GUARD.user.js landed: the PUT readback must read N/N OK and the file must be at 1.01.
Paste it: Tampermonkey, plus, new script, replace all, save, reload the Venice tab once.
Watch one full wake cycle. Pass is one wake go and one bail: generating per wake, and one badge.
If it holds past two minutes the harness gate is clear and lane item L1 is unblocked: post a failed nai-sec-* or nai-occ-oi-daily run ID and error, or record that probe_result.yml does not exist and that is why.
If duplicates return, the second boot is real and the loader needs the registry fix: keep interval handles on a window list, have stopOld() clear them, delete the placeholder line.

Also unanswered, asked five times: is there a second Tampermonkey entry with Bridge in the name and no Loader? If yes, disable it. It defeats every fix here.

Delivery finding, keep: scrape raw.githubusercontent.com, never blob HTML. Blob converts angle brackets and both truncate, but raw damages less.

Prior state files: STATE.md, STATE4.md, STATE5.md, STATE6.md. This one supersedes them.

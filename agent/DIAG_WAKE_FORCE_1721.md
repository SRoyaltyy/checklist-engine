DIAG - wakes fire on every scan because force bypasses the cooldown

2026-11-05T17:21Z, from the BRIDGE.user.js delivery at ?v=1720.

The mechanism

Bridge constants, verbatim:

var POLL = 30000, COOL = 240000, DEAD_LIMIT = 3, STUCK_MS = 300000, BOOT_MAX = 2, ESC_COOL = 90000, SCRAPE_MAX = 12000;

Wake gate, verbatim, first lines of function wake():

function wake(reason, force) {
if (busy) { console.log('[bridge] bail: busy'); return false; }
if (generating()) { console.log('[bridge] bail: generating'); return false; }
if (load('vrb.paused') === '1') { console.log('[bridge] bail: paused'); return false; }
if (!force && Date.now() - num('vrb.cool') < COOL) { console.log('[bridge] bail: cool'); return false; }

Loader patch, verbatim from LOADER4.user.js:

if (out.indexOf("wake(reason || 'heartbeat', false)") !== -1) { out = out.replace("wake(reason || 'heartbeat', false)", "wake(reason || 'heartbeat', true)"); n++; }

So the loader makes every heartbeat wake forced. The cooldown line short-circuits on force and is never reached. Every POLL tick submits a wake. That is the 30-second cadence, and it matches the observed 33-second gap. The 4-minute gap before it was the tail of the previous cooldown; the 6-second gaps are almost certainly a second instance polling on its own timer.

Consequence: vrb.cool is written after every send and never read. Setting it by hand cannot throttle anything while force is on. Two earlier conclusions were therefore wrong and are corrected here: the flag is not the lever, and the cooldown key is not the lever either. The force argument is.

Fix, preferred, one character, loader-side

In agent/LOADER4.user.js, in patch(), change the replacement string only:

from "wake(reason || 'heartbeat', true)"
to "wake(reason || 'heartbeat', false)"

The search string stays as it is, so the patch still matches and the count still reads 2. force becomes false, the cooldown check runs, and wakes settle to COOL = 240 seconds.

Why the loader rather than the bridge: the bridge calls wake('resume', true) itself after a bootstrap, and the loader patch does not touch that call, so rollover recovery stays immediate while periodic wakes get throttled. Patching the bridge instead would have to preserve that distinction and would need a whole-file bridge PUT.

Fix, alternative, bridge-side, if the loader is ever rebuilt for other reasons

Replace !force && Date.now() - num('vrb.cool') < COOL
with Date.now() - num('vrb.cool') < (force ? 180000 : COOL)

That keeps a forced floor so a forced wake cannot stack on a fresh one.

Not the fix: clearing WAKE.json pending (tested 16:56Z, no effect). Setting vrb.cool by hand (bypassed). Pausing (stops work entirely).

Status: written, not applied. Both files need a whole-file PUT and both deliveries are truncated, so the edit is blocked on reconstruction. The loader is the smaller file and has already been round-tripped once at 7113/7113 OK.

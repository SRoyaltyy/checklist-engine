Patch spec - single-instance guard. Apply when the loader body is in FETCH.md. 2026-11-05T16:41Z

Principle: newest boot wins. A newer boot must be able to take over from a wedged one, so the guard compares tokens rather than counting instances. Only the holder of the current token scans.

Three edits, all in the loader. The loader already carries a boot sequence for its health timer, so extend that variable rather than introducing a second one. Call it BOOT.

Edit 1, at the top of the boot function, before the fetch

var BOOT = Date.now() + '-' + Math.random().toString(36).slice(2);
window.__vrbBoot = BOOT;

Edit 2, immediately after the patch string is built and before eval

Prefix the patched body with the opener below and append the closer after it. The body is an IIFE, so wrapping is safe.

Opener, prepended to the patched text

;(function(){var T=window.__vrbBoot;

Closer, appended to the patched text

})();

Edit 3, inside the bridge scan loop, at the top of each iteration, before the tail slice is read

if (window.__vrbBoot !== T) { console.log('[bridge] stand down, superseded by ' + window.__vrbBoot); return; }

Placeholder stop handle: stamp the same BOOT value on the tagged placeholder the loader already installs, so the health timer only ever clears its own generation.

Test, and what failure looks like

Pass: exactly one "wake go" per wake, exactly one "bail" per blocked scan, and a manual reload still leaves one live instance. Stand-down line appears once per superseded boot and no more.

Fail cases to watch. If the token is read outside the closure the guard never trips, so T must be captured inside the wrapper. If the opener is prepended after the FILTER patch, string offsets shift and the FILTER line itself must not be counted as a patch spot. If the body already ends with a return at top level, the closer lands after it and is dead code, which is harmless but means the guard is not running — check for the stand-down line in a deliberate double-boot before calling it proven.

Reason this is worth doing at all: two instances share one directive hash set, so each erases the other's one-shot marks and the filter looks broken from outside. Until this is in, a directive test result is not trustworthy.

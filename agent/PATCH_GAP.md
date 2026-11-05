Missing region needed before the bridge can be PUT whole. 2026-11-05T17:40Z

The three insertions in PATCH_BRIDGE_INSTANCE.md are ready and their anchors are exact. What is missing is the middle of wake()'s step() function, clipped out of the delivery.

What I have, in order: function step() { then var set = load('vrb.compact') === '1' ? COM and then the clip. Text resumes at (e) { fail('read ' + p + ' ' + e); } followed by } and function finish() {.

What I need: everything between those two points, verbatim, however long. It is the loop that walks the read set and pushes chunks, so it is short — probably a dozen lines including the COM/COMPACT selection, the read, the fence push and the catch.

Why it cannot be approximated: the health test only checks that the bridge talks. A wrong step() still talks, so no rollback fires, and the failure would surface later as a malformed wake prompt with no obvious cause.

Second gap, smaller, same file: hash() arrives as for (i = 0; i >> 0; return h.toString(36) and the body of hash is eaten. Same class of loss, same fix needed if the file is ever PUT whole.

Plan once filled: PUT agent/BRIDGE.user.js with the three insertions and both repaired regions, let the loader adopt the new hash, reload once. Old instances carry old code and cannot stand down, so the reload is part of the fix, not optional.

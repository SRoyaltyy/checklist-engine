State 18, 2026-11-05T17:37Z.

Two write attempts failed before this one. Both were sent inside the sandbox renderer; a sandbox is an iframe, so its text never reaches the page innerText the bridge reads. Plain text from now on. A third attempt was truncated mid-body by the turn ending, so it had no closing marker and wrote nothing.

Verified by read: agent/LOADER4.user.js on GitHub was still sha 20a79a3, size 7005, base64 decoding to @version 1.12, and the patch line still replacing the search string with an identical string. 1.12 is a no-op; the wakes stayed 30s.

1.13 changes one character of meaning: the replacement is heartbeat comma false with no space, so it differs from the search and applies. Version and badge bumped. patch() now logs WARN force flag did not take when the replacement is missing, so a silent no-op self-reports. sanitize() asterisks restored to \s* and [a-zA-Z]* because the scrape channel eats asterisks.

Gate is still closed. Badge LOAD v1.13 and vrb.fired climbing past 60000 is the pass. The one-edit fallback on the installed copy remains heartbeat true to heartbeat comma false, no space.

Never push main. No markers.

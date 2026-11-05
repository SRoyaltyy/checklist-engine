Journal entry, loader 1.11 escaping bug. Append to JOURNAL.md when it accepts a write again.

2026-11-05T16:24Z | harness | loader 1.11 eval-failed on paste: SyntaxError Invalid or unexpected token at column 144, the raw.split call. Cause: FILTER is a JS source string in double quotes, so single-escaped \n and \b were consumed by the outer quotes and became a real newline and a backspace before the bridge saw them, leaving an unterminated string. The loader logged patched 2 spot(s) first, so the patch text itself was malformed, not the bridge. | n/a | diagnosed

2026-11-05T16:30Z | harness | fixed by rewriting only the FILTER line with doubled backslashes, split, join and word-boundary all doubled, edited in place in the Tampermonkey editor. No reinstall, because reinstall had already clobbered the working build and would have pulled the broken filter back from the repo. User reports loaded. | n/a | installed

2026-11-05T16:38Z | harness | corrected loader PUT to agent/LOADER4.user.js with @updateURL and @downloadURL, so a future reinstall or auto-update cannot reintroduce the single-escaped filter. | pending | awaiting readback

Note for the next reader: the filter logic was never wrong, only its escaping inside a quoted string. Note also that a wrongly escaped \b fails silently, the filter simply never matches, so a directive-replay regression can look like a filter that is present and working.

Proven: the build parses and boots. Not proven: that the filter still fires, and that the health test passes.

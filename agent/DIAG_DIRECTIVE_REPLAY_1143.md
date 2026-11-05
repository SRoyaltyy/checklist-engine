Fault - old directives re-execute on every scan, 2026-11-05T11:43Z

Evidence. LOADER2 scrape deliveries at 11:38:18, 11:38:24, 11:38:26, 11:38:37, 11:39:59 and 11:40:15 — roughly every 15 seconds — while a different URL emitted at about 11:39:40 never ran at all. The URL fetched is always the one from my first message, never the latest.

Mechanism. The loader patches the scan to read only the last 20000 characters of body text. That fixed the earlier rewrite storm, which re-wrote files from stale messages far up the page. It does not stop re-execution of directives still inside the window. My first directive has not scrolled out, so every scan re-reads it and issues it again.

Why the debounce does not save us. MEMORY.md says scrape debounces 60s per URL. Deliveries arrive 15 seconds apart on an identical URL, so either the debounce keys on something that varies per scan or a re-scan bypasses it. Either way it cannot be relied on to make a directive one-shot.

Consequences. A directive is not a one-shot instruction, it is a standing subscription until it scrolls away. Emitting a second directive does not replace the first, it adds to the set. The loop therefore cannot choose what to read, which is worse than being unable to read at all. Combined with a frozen wake payload, state can only be written, never confirmed.

What to do while this stands. Assume every directive stays live. Do not emit one unless repeating it is harmless. Prefer writes over reads. When a specific read matters, make the URL unique per attempt so the queue cannot collapse onto the old one, and expect the old URL to keep firing alongside it.

The real fix, not yet written. Either the bridge should mark directives it has already executed for the current message set and skip them, or the scan window should shrink far enough that a directive scrolls out after a turn or two. The first is more reliable because it does not depend on message length. Until then, a directive must be treated as idempotent by design.

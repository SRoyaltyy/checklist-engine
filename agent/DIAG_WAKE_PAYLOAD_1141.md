Fault - the wake loop is blind, 2026-11-05T11:41Z

Three separate faults, stacked, each hiding the next.

One. The payload is frozen. Wakes at 11:39:15.285Z, 11:39:16.799Z and 11:39:31.092Z all carry the same WAKE.json id, 11:34:42.774Z, and identical file bodies. MEMORY.md was rewritten at about 11:39:20Z and still appears in its old form in every payload since. The poller replays one wake rather than building a new one, so the snapshot is older than the work and cannot be trusted as state.

Two. The delivery queue is stranded and starving. Four consecutive LOADER2 scrapes were delivered, the last at 11:39:59Z, none of them the URL asked for. A scrape of MEMORY.md emitted at about 11:39:40Z did not execute. Parked deliveries carry their whole text, and MEMORY.md says parked items starve fresh small requests — that is what is happening.

Three. The 60s per-URL debounce drops repeats, so re-asking immediately does nothing.

Consequences. Reads are unreliable, so verification by scrape is unavailable until the queue drains. Payload state is stale by minutes, so any fact taken from a payload may already be wrong. The rollback loop also keeps re-booting the bridge, which re-parks work.

What to do. Prefer writes over reads while the queue is backed up; a write lands immediately and survives. Do not re-emit the same URL inside 60s. Vary the host or path when a read is genuinely needed, and prefer raw.githubusercontent over the blob view so the delivery is text without the GitHub chrome.

Untested. Whether the stranded LOADER2 deliveries drain on their own or need the bridge to be restarted. Watch for a delivery whose URL is not LOADER2; that means the queue cleared.

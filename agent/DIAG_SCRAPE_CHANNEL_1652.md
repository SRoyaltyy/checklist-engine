DIAG - scrape delivery no longer reaches the payload. 2026-11-05T16:52Z

Console at 16:50Z shows the fetch pipeline working: "scrape 200 -> agent/fetch/mrelaw.md", "resolving agent/fetch/mrelaw.md", "scrape delivered 5778 from https://raw.githubusercontent.com/.../agent/LOADER4.user.js". The fetch succeeded and was delivered.

It was delivered to the chat, not into the payload. Wake payloads still inline agent/FETCH.md, which now holds a body from 2026-11-04T17:24Z. So the protocol step "the next wake inlines agent/FETCH.md" is no longer true: deliveries land in agent/fetch/<slug>.md and are shown to the human, and nothing puts them where the next wake reads.

Consequence: every read now needs the human to paste, or needs the delivery path fixed. Writes are unaffected and still landing with matching readbacks, so the loop can still record, it just cannot see.

Second finding, from the same line

Delivered 5778 bytes against 7113 on disk. Deliveries are capped, so the tail is cut. Patching a file from a delivery risks losing its last section.

Guard plan change

Drop the in-loop token check. It required patching the loader and the bridge, and both bodies are only reachable through a capped channel. Instead the loader calls any existing window.__vrb.stop before booting a replacement. Old instance dies, new one takes over, no token, no bridge edit, nothing to keep in sync. Newest still wins.

Open question for the channel: whether the wake builder can be pointed at agent/fetch/<slug>.md, or whether the payload should inline the newest delivered file instead of FETCH.md. Until one of those, ask for a paste when a read is needed.

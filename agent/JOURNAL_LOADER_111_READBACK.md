Readback proof, 2026-11-05T16:52Z. Append to JOURNAL.md when it accepts a write again.

put agent/LOADER4.user.js returned 200 with readback 7113/7113 OK. The corrected filter is in the repo byte for byte, so reinstall and auto-update are now safe. Also corrects my own expectation: the loader patches 2 spots, not 3. Two is right, the filter is one of the two, and the build boots with it, so the parse fault is closed.

Open, and now with evidence: every wake logs wake go and bail: generating twice in a row, and the loader logs its patch in pairs. Two bridge instances are live in the same tab. Two instances share one directive hash set, so each one's one-shot marks erase the other's, and the filter looks broken again from the outside. They also both consume the same wake.

Gate still open on one fact: whether the badge hid itself. Not visible in this paste.

MEMORY — durable notes

Append only. Things a future wake must not have to rediscover.

2026-11-03 — lane
Work on venice/sec-options-pipelines. The calendar branch is parked; ignore it after dca969a.
Item order is in PROGRESS.md and matches the lane. Item 1 is the 403 fix, not the tickers workflow.
SEC blocks GitHub runner IPs and often Cloudflare's too. Two routes, then stop and journal the headers.
2026-11-03 — write path
A file body containing a literal END directive is truncated at that line. Describe directives in words inside files.
Writes only land while the page is open and mutating. If the bridge is paused, they are inert text.
2026-11-03 — bootstrap gap, open
The bootstrap does not inline agent/FETCH.md. A scrape result is written to disk and then shown to nobody, so a fresh chat can write but cannot observe any read. web_scrape is dead, so there is no in-turn read either. Read results only become visible if FETCH.md is added to the bootstrap template, or if a human opens the file. Gen 10 and gen 11 both lost their read-back to this. Fix the template before relying on any read.
2026-11-03 — infrastructure
Parse before writing. Byte counts prove nothing: thirty missing plus signs and a missing brace all passed size checks.
The wake function had dead code after its return, so the busy flag stuck true forever. Hoisted the var and called step first.
The loader must pass GM_xmlhttpRequest into the Function constructor; page scope has no GM functions.
Deploys wipe bindings unless keep_bindings is sent. It has cost a full credential set once.
The putprobe op replaces the doorman with a one-line stub. Restore via the deployer directly.
Cloudflare caps the request line at 32,000 characters. Long bodies go in a POST body.
The sandbox iframe cannot reach workers.dev. about:blank plus console is the read and write path.

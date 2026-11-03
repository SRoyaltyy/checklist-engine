MEMORY — durable notes

Append only. Things a future wake must not have to rediscover.

2026-11-03 — infrastructure
Parse before writing. Byte counts prove nothing: thirty missing + and a missing brace all passed size checks.
wake() had dead code after return true so busy stuck true. Hoisted the var, called step() first.
Loader must pass GM_xmlhttpRequest into new Function; page scope has no GM_*.
Deploys wipe bindings unless keep_bindings=plain_text,secret_text is sent. It has already cost a full credential set once.
op=putprobe replaces the doorman with a one-line stub. Restore via the deployer directly, never through the doorman.
Cloudflare caps the request line at 32,000 chars. Long bodies go in a POST body, never a query param.
The sandbox iframe cannot reach workers.dev. about:blank plus console is the read and write path.

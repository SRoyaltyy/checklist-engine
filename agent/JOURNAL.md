Journal - append only, newest last. date UTC | item | action | sha | result.

2026-11-02 | infra | tooling branch created from main; lane staged | n/a | no work yet
2026-11-03T09:41Z | 1 | TODO.md re-read, lane and item 1 confirmed; workflow dir listing scrape emitted | n/a | pending
2026-11-04T16:35Z | infra | scrape result arrived in wake payload via FETCH.md, no web_scrape, no human paste | n/a | proven
2026-11-04T16:35Z | infra | markdown was eating asterisks from directive bodies; bodies now fenced, file restored to 4.5 | n/a | proven
2026-11-04T16:36Z | infra | scrape delivery arrived as its own chat message, capped and wrapped | n/a | proven
2026-11-04T16:37Z | 1 | doorman Worker egress to sec.gov company_tickers.json | n/a | 403, 500 bytes, route two gone
2026-11-04T16:41Z | 1 | SEC block page text recovered: Request Rate Threshold Exceeded | n/a | not an IP ban; rate or undeclared agent
2026-11-04T16:41Z | 1 | doorman forwarded no User-Agent on scrape | n/a | fixed, contact UA plus backoff deployed, bindings kept
2026-11-04T16:48Z | infra | deliveries arrived as envelopes, tab still on 4.5 | n/a | reload outstanding
2026-11-04T16:50Z | infra | scrape of api.github.com 403, op fetches unauthenticated and shared IP limits are gone | n/a | fix pending, not blocking
2026-11-04T17:11Z | infra | Copy code line from the chat UI broke eval with a SyntaxError | n/a | fixed in 4.9, loader sanitises too
2026-11-04T17:12Z | infra | loader 1.5 adds post-swap health check, marks a bad version, rolls back to last good | n/a | written, unproven
2026-11-04T17:12Z | infra | repo state verified clean: bridge 4.9, version 4.9.1 | n/a | confirmed by read
2026-11-04T17:19Z | infra | scrape marks were permanent, so a URL could only ever be fetched once. Now a 60s debounce | n/a | fixed in 5.0, proven by SEC re-fetching
2026-11-04T17:19Z | infra | delivery now resolves the envelope and delivers page text | n/a | proven
2026-11-04T17:19Z | 1 | SEC retry with contact UA, Accept, identity encoding, five backoff attempts via Worker | n/a | still 403, new Reference ID 0.5e711102.1793812678.1edce412
2026-11-04T17:19Z | infra | two concurrent scrapes both write FETCH.md, so both deliveries resolve the same file | n/a | defect open
2026-11-06T11:47Z | infra | nai-probe.yml arrived with every leading space stripped, workflow_dispatch at column 0, invalid | n/a | run 42210301200 died same second, no job
2026-11-06T11:59Z | infra | flow style, one line, zero indentation, written to a fresh path nai-probe2.yml | n/a | landed byte-exact
2026-11-06T12:15Z | infra | nai-probe2 green twice, runs 42216183221 and 42214233882 | n/a | proven: bridge-written workflows run when flow style
2026-11-06T12:15Z | infra | nai-probe.yml still flat: the replayed old directive rewrites the indented body over any newer one | n/a | defect open, use fresh filenames
2026-11-06T14:30Z | L1 | verdict collector and poster both green; issue 215 carries run 41413529249 with job, step and log tail | n/a | L1 proven, three duplicate comments
2026-11-06T14:45Z | L1 | branch TODO.md found stale against main's narrowed lane; Venice section replaced, poke item ticked with evidence | n/a | corrected, unproven until pushed
2026-11-06T14:45Z | L1 | PR opener written to fresh paths, unproven | n/a | landed corrupted, see 15:05
2026-11-06T15:05Z | infra | NEW WRITER DEFECT found by reading back: leading markdown is stripped from body lines, # and ## and - all removed, lone asterisks eaten, so open_pr.sh arrived with its comment line gutted and %%/* mangled to %%/ | n/a | defect open, fenced bodies plus no comment lines and no asterisks in code
2026-11-06T15:05Z | L1 | opener rewritten as scripts/nai/open_pr2.sh with cosmetic-only corruption surface, caller .github/workflows/nai-pr2.yml | n/a | written, dispatch next wake

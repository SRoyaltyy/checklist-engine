# Item 1 — BLOCKED on evidence, lane moves to item 4

Recorded 2026-11-04T18:30Z. Proof run: 41885769483 (nai-sec-bulk), failed, first run after
the doorman contact-UA fix was deployed.

## Both sanctioned routes now have a post-fix failure

- Runner direct, pre-fix: 41413529249, 41413535355, 403.
- Worker egress, pre-fix: 403 with block page, refs 0.a10f0317..., 0.5e711102.1793812678.1edce412.
- Worker egress, post-fix: 41885769483, failed. The contact User-Agent, Accept,
  Accept-Encoding identity and five backoff attempts did not clear it.

## Conclusion

The threshold is on the egress IP range, not on headers. Cloudflare's pool is shared and hot.
No header or pacing change on either route will fix it. This matches the block page's own
wording, "Request Rate Threshold Exceeded", and the fact that it names a threshold rather than
an address.

## Consequences kept for the record

fetch/sec_client.py now accepts either raw bytes or a JSON envelope and takes status out of the
envelope, printing RELAY_STATUS with an excerpt so attribution survives. Correct and unused until
a route exists. The scrape op already takes url=, so relay_target() needs no change.

## Lane now

Item 4, options open interest: probe free daily per-stock OI from OCC volume/OI reports and Cboe
daily stats, daily cron collector plus backfill of whatever history exists, honest depth in
docs/OPTIONS_OI_FREE_V1.md. Needs no sec.gov. Row [1 Data / Options + money-flow #165].
Items 5 and 6 are also non-SEC and remain available.

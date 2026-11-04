# SEC 403 — item 1 status

Lane venice/sec-options-pipelines. TODO Venice item 1. Row [1 Data / SEC].
State: BLOCKED on both sanctioned routes (runner direct, relay Worker).
Egress retry through the doorman is in flight; verdict pending.
A runner dispatch of nai_sec_bulk.yml was issued 2026-11-04T17:38Z, first since the doorman
User-Agent fix. Verdict pending.

## Established

- Block page recovered verbatim: "Request Rate Threshold Exceeded", reference IDs
  0.a10f0317... and 0.5e711102.1793812678.1edce412. This is a rate threshold, not an IP ban.
- Failing runs: 41413529249, 41413535355. Both 403.
- Runner-side headers were already correct, so header format is not the defect:
  scripts/nai/common.py sends a Name email@domain User-Agent, Accept-Encoding identity,
  Accept */*, 0.15s pacing and retries; fetch/sec_client.py does the equivalent with gzip.
- The relay Worker was the actual defect: it issued its fetch with no User-Agent at all, so
  sec.gov saw Cloudflare's default UA. Now sends a contact UA, Accept, identity encoding and
  five backoff attempts. Redeployed with bindings kept.

## Not established

- Whether the fixed doorman egress clears SEC at all.
- Whether the runners' shared IPs are rate-limited independently of egress. If they are,
  no header change on the runner side will ever help.

## Routing contract mismatch — read before wiring

fetch/sec_client.py cannot simply be pointed at the doorman:

- It is relay-only. get_bytes() raises DIRECT_SEC_REQUEST_FORBIDDEN without
  PRIMARY_ACTION_RELAY_URL, and _request_bytes() re-raises if the host is any sec.gov name.
- relay_target() appends the source as a url= query parameter. The doorman scrape op uses a
  different parameter name, so the value is dropped and the Worker fetches nothing.
- _request_bytes() expects raw response bytes and gunzips when the first two bytes are
  0x1f 0x8b. The doorman scrape op returns a JSON envelope. json.loads() on that envelope
  parses the envelope, not the SEC document.
- error_evidence() expects an HTTPError carrying SEC's block page in the body. Through a
  relay envelope the status is the relay's, not SEC's, so 403 attribution is lost.

Closing item 1 therefore needs one of:
  a) a doorman op that accepts url= and streams the upstream bytes and status through, or
  b) sec_client.py taught to unwrap the envelope and read the status out of it.

Option (a) is cleaner: it keeps one client contract and leaves attribution intact.

## Rule applied

If the dispatched run or the spaced retry returns the block page, item 1 is recorded blocked
on both routes and the lane moves to item 4 (options open interest), which never touches
sec.gov.

## What closes item 1

- A green run ID on the SEC workflow.
- The relay contract above satisfied, then ci/sec_route_probe.py green before any dispatch.
- Green run ID cited in the PR to main.

## Debt noted

Two stacks duplicate the same job: scripts/nai/* (direct-first, relay fallback) and
fetch/sec_client.py (relay-only). Collapse to one once routing lands.

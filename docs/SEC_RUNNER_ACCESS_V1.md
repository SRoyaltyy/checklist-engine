# SEC runner access diagnosis and bounded proof

Price tasks 1–4 are merged and read back on main. This is the next SEC access
task; bulk acquisition and historical joins are not claimed here.

The latest reviewed scheduled Form 3/4/5 run,
[42156926867](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42156926867)
(2026-11-06), fails on the official index page. Its job 127693199421 logs a
direct HTTP403 followed by a relay HTTP403. The [OCC run41906860199](https://github.com/SRoyaltyy/checklist-engine/actions/runs/41906860199)
cited in TODO instead fails while parsing empty `OCC_LIMIT`, before any download;
that separate fix belongs to the later Options task.

## Client change

The no-AI collectors now use the existing SEC relay consistently, matching the
longstanding `fetch.sec_client` routing rule. A missing relay fails before any
SEC request. The client sends a declared contact User-Agent, takes it from
`SEC_USER_AGENT` (or legacy `SEC_UA`) when configured, paces requests at least one
second apart, and stops on HTTP403/429. A denial records the public source URL,
route name, status, attempt count and redacted response excerpt. It never logs
the relay URL or token. Large responses continue streaming atomically to disk;
partial files are removed on failure.

The three existing scheduled SEC workflows pass the optional repository variable
`SEC_USER_AGENT`. An empty variable retains the previously documented contact
identity. These changes do not prove the upstream Worker preserves that header.
The [SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
asks automated clients to identify themselves with a contact email and limits
requests to ten per second. The [API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
recommends the nightly bulk archives for large acquisitions.

## Upstream header evidence

The published [fullscan relay source on main](https://github.com/SRoyaltyy/fullscan/blob/main/relay/worker.js)
replaces the caller's User-Agent with a fixed identity containing no contact email.
Its [open PR642](https://github.com/SRoyaltyy/fullscan/pull/642), head
`467cfcf994df7bee830f912db6449c89f64fccab`, instead sends
`Fullscan filing parser research@sroyaltyy.github.io`.
The [one-line patch](SEC_RELAY_CONTACT_HEADER_V1.patch) reproduces that existing
candidate header change. This is a concrete deployment candidate for the owner
of the configured Worker, not evidence of its deployed configuration.

**Inference:** a caller-only header edit cannot repair a Worker that replaces it.
The actual deployed Worker and its upstream request headers are not observable
from the checklist client. No fullscan merge, Worker deployment, secret change
or alternate-proxy routing is performed by this PR.

## Proof and acceptance

`nai-sec-access` runs 19 synthetic transport/schema/publication tests without installing
dependencies. The one-shot request then permits exactly six official reads on
the authorized runner, one attempt each and at most10MB per response:

1. `company_tickers.json` — nonempty CIK/ticker schema.
2. `company_tickers_exchange.json` — nonempty CIK/ticker/exchange schema.
3. Form3/4/5 index — actual official ZIP links from2020 onward.
4. Form13F index — actual official ZIP links from2020 onward.
5. AAPL submissions — matching CIK and nonempty filing accessions.
6. AAPL Assets concept — matching CIK and nonempty numeric facts.

The workflow publishes a new `sec-runner-access-v1-<run>-<attempt>` release with
its receipt even when access fails, then exits nonzero on any failed endpoint.
It never interprets an HTML denial or an empty index as success. A green result
proves only this source-access scope; complete bulk downloads, coverage and PIT
joins remain later tasks. The one-shot request is disabled after review.

Actual [run42254420545/attempt1](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42254420545),
source `adc606c30d579d03588dd2fd323532b58c2f5574`, confirms **four www.sec.gov
HTTP403 failures and two data.sec.gov successes** (1,005 submission rows and148
numeric concept observations). Each endpoint was attempted once. The initial
release-publication call then failed on an unsupported wrapper option. The receipt
survived as Actions artifact13521383839, whose ZIP SHA256
`06df53b1e6d17e81a7a172cb2dabe7fa1a2206d0adb935c08edb21e47226e35f`
was independently checked after download through the GitHub connector. Its exact
[6,558-byte receipt](SEC_RUNNER_ACCESS_PROOF_V1.json) is preserved here with SHA256
`26ba89c2f4d35a013d68b6a49a8f999b143d4d98974c9f23a5be93e138625c85`.
No public release was created by that failed publication call. The unsupported
option is removed and a regression check exercises the real release-wrapper
parser. The supplied upstream header patch also passes `git apply --check`
against the published Worker source.

The one-shot request is reset FALSE. **Task5 remains unchecked, world gate
NOT_PROVEN, scoring CLOSED.** The next dependency is a contact-bearing deployed
Worker or another explicitly configured authorized SEC egress route. Cyrus has
been given the exact one-line Cloudflare edit; no deployment is claimed and no
further SEC requests are made until that external configuration changes.

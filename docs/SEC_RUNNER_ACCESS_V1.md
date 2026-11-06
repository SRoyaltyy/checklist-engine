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

`nai-sec-access` runs 18 synthetic transport/schema tests without installing
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

Actual runner evidence is pending. **Task5 remains unchecked, world gate
NOT_PROVEN, scoring CLOSED.** The next dependency, if the same upstream denial
persists, is a contact-bearing deployed Worker or another explicitly configured
authorized SEC egress route. No secret value should be posted in git or chat.

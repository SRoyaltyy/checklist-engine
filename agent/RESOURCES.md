RESOURCES — concrete URLs and snippets
Repo and files
https://github.com/SRoyaltyy/checklist-engine
https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/PATH
https://github.com/SRoyaltyy/checklist-engine/tree/venice/sec-options-pipelines/agent
raw.githubusercontent.com/OWNER/REPO/venice/sec-options-pipelines/PATH takes the branch unencoded. It 500s from Tampermonkey and works in a browser.

Lane sources
https://github.com/SRoyaltyy/checklist-engine/blob/main/TODO.md
https://github.com/SRoyaltyy/checklist-engine/blob/main/METHODOLOGY.md
TODO.md decides the lane. Grep METHODOLOGY.md if you need the wider method; never read it whole.

Lane docs
https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/docs/SEC_INDEPENDENT_BULK_SOURCE_PLAN_V1.md
https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/docs/SEC_RETAINED_IDENTITY_MAP_V1.md
https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/docs/CBOE_SOURCE_LOCATIONS_V1.json
https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/docs/NO_AI_DATA_PIPELINES_V1.md
The worker
Base: https://venice-doorman.fullscan-relay.workers.dev/?k=KEY&op=OP

Ops: ops branch ref read list commits diff search grep put edit pr pr-edit runs dispatch merge deploy scrape

Examples:

...&op=ops
...&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FSTATE.md
...&op=grep&branch=venice%2Fsec-options-pipelines&path=METHODOLOGY.md&q=Venice
...&op=list&branch=venice%2Fsec-options-pipelines&path=agent
The deployer
https://venice-deployer.fullscan-relay.workers.dev/?k=DEPLOYKEY&op=deploy&branch=venice%2Fsec-options-pipelines
https://venice-deployer.fullscan-relay.workers.dev/?k=DEPLOYKEY&op=bindings
Cloudflare
https://dash.cloudflare.com/7e956804300ca03332805f1675f2f141/workers-and-pages
Reads when the scrape tool is exhausted
Blank about:blank tab, no CSP:

fetch(W+'read&branch=B&path=P').then(r=>r.json()).then(j=>console.log(j.text))
Writes when the scrape tool is exhausted
fetch(W+'put&branch=B&path=P',{method:'POST',headers:{'Content-Type':'text/plain'},body:text})
Never GET a long body: Cloudflare caps the request line at 32,000 characters.

Parse before writing JS
let acorn = await import('https://cdn.jsdelivr.net/npm/acorn@8/dist/acorn.mjs')
acorn.parse(text,{ecmaVersion:2022})
Local keys
vrb.gen vrb.fail vrb.sha vrb.cool vrb.paused vrb.halt vrb.bootPending vrb.compact vrb.fired vrb.v

Clear vrb.sha to force a wake. Clear vrb.halt by hand after a halt.

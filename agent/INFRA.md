INFRA — the components, their roles, and how to reach them

Read this before touching anything. Each piece exists because something failed.

Component inventory
1. venice-doorman — Cloudflare Worker, the transport

Base: https://venice-doorman.fullscan-relay.workers.dev

Role: does GitHub reads and writes on the loop's behalf, so no web_scrape is needed. Also holds the cron that sets the wake flag.

Reach it: every call needs ?k=<DOORMAN_KEY> and &op=<op>.

Copy code
https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=ops

Ops: ops branch ref read list commits diff search grep put edit pr pr-edit runs dispatch merge deploy scrape

Bindings: GITHUB_REPO, WAKE_BRANCH, DEPLOYER (plaintext); GITHUB_TOKEN, DOORMAN_KEY, DEPLOY_KEY (secrets). Cron on the Triggers tab, 15 minutes.

Never reach it from the sandbox iframe — CSP blocks it. Use the page console, or a blank about:blank tab.

2. venice-deployer — Cloudflare Worker, the repair path

Base: https://venice-deployer.fullscan-relay.workers.dev

Role: redeploys the doorman from agent/DOORMAN.worker.js on a branch, so the loop can fix its own transport. Separate from the doorman so a broken doorman can still be replaced.

Reach it: ?k=<DEPLOY_KEY>&op=deploy&branch=<branch>

Copy code
https://venice-deployer.fullscan-relay.workers.dev/?k=19055789d&op=deploy&branch=venice%2Fsec-options-pipelines

Also op=bindings to list current bindings. Always deploys with keep_bindings=plain_text,secret_text; a deploy without it wipes every variable and secret.

3. Bridge userscript — agent/BRIDGE.user.js

Role: the agent's body in the page. Polls WAKE.json, assembles a prompt from state, types it into the composer, submits it, scans replies for directives, and rolls the chat when it dies.

Runs under Tampermonkey, injected by the loader. Reach it: it is already running. It executes the @@PUT blocks you write. Badge bottom-right; single click pauses, double click forces a wake.

4. Loader userscript — agent/LOADER.user.js

Role: fetches the bridge from the repo, compares BRIDGE_VERSION.json, re-executes on change. This is how the bridge is updated without a human reinstalling anything.

Runs under Tampermonkey. It passes GM_xmlhttpRequest into the bridge explicitly, because page scope has no GM_*.

5. GitHub repo — SRoyaltyy/checklist-engine

The durable store. Everything survives here: state, code, lane work. Branch venice/*, PR to main.

The wake cycle
Cron sets agent/WAKE.json pending with a reason.
tick() polls every 30 s.
If the reason carries an unseen sha, composer empty, not paused, past 240 s cooldown — wake() runs.
Reads nine state files, appends the TODO.md Venice lane, prepends WAKE_PROMPT.md, fills, submits.
Directives the bridge executes
Directive	Effect
@@PUT path …

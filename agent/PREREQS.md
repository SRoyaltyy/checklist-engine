PREREQS — what must exist for the loop to run

If any of these is missing the loop fails, usually silently.

Cloudflare, on venice-doorman

Plaintext variables:

GITHUB_REPO = SRoyaltyy/checklist-engine
WAKE_BRANCH = venice/sec-options-pipelines
DEPLOYER = https://venice-deployer.fullscan-relay.workers.dev

Secrets:

GITHUB_TOKEN — Contents read and write
DOORMAN_KEY
DEPLOY_KEY

Cron trigger on the Triggers tab, 15 minutes. Without it there is no heartbeat.

Cloudflare, on venice-deployer
CF_ACCOUNT, SCRIPT_NAME = venice-doorman, CF_TOKEN, DEPLOY_KEY, GITHUB_REPO

The deployer preserves bindings via keep_bindings. A deploy from any other path wipes them.

Browser
Tampermonkey installed
Loader script installed and enabled
Old Venice Repo Bridge disabled — both enabled doubles every prompt
Site access allowed for venice.ai
Repo

Files that must exist or the wake degrades to [unavailable 400]:

BRIEF.md STANDING_ORDERS.md QUEUE.jsonl STATE.md PROGRESS.md JOURNAL.md TEST_LOG.txt GANTT_ROWS.md WAKE.json WAKE_PROMPT.md COMPACT.md BRIDGE.user.js DOORMAN.worker.js DEPLOYER.worker.js LOADER.user.js BRIDGE_VERSION.json BRIDGE_GEN.json HALT.json

Verification
Copy code
<doorman>?k=<KEY>&op=ops

All seventeen ops. Then a read of agent/STATE.md. If that 400s, a binding is missing.

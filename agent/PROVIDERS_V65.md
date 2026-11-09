# Shared Venice / DeepSeek repository bridge, runtime 6.5.5

The existing Cloudflare doorman/deployer and GitHub protocol are reused. The common loader now matches venice.ai and chat.deepseek.com; no raw shared keys are included in repository source.

## Provider behaviour
- Venice keeps its existing vrb6 state/owner/cache keys. DeepSeek uses drb6 keys. Each provider's request history, cooldown and fallback cache are separate.
- Browser Web Locks prevent duplicate execution within an origin. The server task lease prevents two provider owners from mutating the same active assignment.
- DeepSeek is passive in ordinary personal tabs. Activate a dedicated task tab with https://chat.deepseek.com/?repo_bridge=1 or the userscript menu. Activation stays in that tab's sessionStorage across navigation; it does not activate unrelated conversations.
- DeepSeek selectors were inspected in the live interface: textarea placeholder Message DeepSeek; role=button with ds-button--primary and ds-button--circle; ds-button--disabled when inactive; final response container ds-assistant-message-main-content. Reasoning text is excluded from tool parsing. File-write/edit packets must be in a fenced code block to prevent rendered Markdown from altering source text.
- Completed final JSON uses the existing venice-v6 wire schema. The agent reads the current assignment, claims ownership, uses the same typed GitHub tools, checkpoints progress/pitfalls and restores state on rollover. Directory-entry and branch identities are retained as proof; each prompt lists the exact accepted checkpoint identities.
- Visible human verification stops the runtime and requires user handling. Provider usage notices retain their cooldowns.

## Pacing and Venice mode policy
- Normal request-start spacing is randomized between 4 and 5 minutes, with 15 attempts per rolling hour. Pending model responses and explicit backoff/cooldowns can extend actual spacing.
- Failed/unacknowledged send attempts count. Manual wake, rollover and reload preserve the budget. Successful repair restores normal spacing; schema errors do not cause provider backoff. Explicit provider penalties, active generation and technical failures can extend spacing.
- Venice prefers Agentic. Two technical response timeouts can trigger a mode switch, with a 30-minute switch cooldown. An explicit provider usage cooldown prevents both preferred-mode navigation and fallback switching.
- DeepSeek has no automatic cross-service quota-routing policy; it is a separately activated provider adapter.

## Validation
87 browser/loader/ownership/pacing/adapter/mode checks passed locally.
Live verification on 2026-11-09:
- Loader 2.2.0 installed in the existing Tampermonkey script, retaining its saved key. Both sites loaded the new runtime; DeepSeek's loader promoted 6.5.5 to its healthy fallback after a completed checkpoint.
- DeepSeek answered a compatibility probe, autonomously loaded the active assignment, used GitHub read tools, and moved into a fresh chat with the task context preserved.
- The model requested a rewrite of docs/venice-audit-v1/PROGRESS.json on venice/repo-hierarchical-audit-v2. The bridge verified commit 055b1e3440432f60755614e6e5b324e3556088d1 and blob 19a64f70e38e94d39887b7bac81611811901fe8e; independent GitHub readback confirmed task_id repo-hierarchical-audit-v2 and current_subtask t3.
- Write receipt: agent/runtime/receipts/mw98hrv5-rzim04sg.0.json@6d74bbaac36a2723c9d98c24083bd56a233a4dba (status done, verified true).
- Durable session: agent/runtime/tasks/repo-hierarchical-audit-v2/sessions/mw98hrv5-rzim04sg.json@3d652d11eaf3cb3daeeb7eb1962ba5809891b79b, saved 2026-11-09T12:29:29.785Z. Runtime records are on the maintenance branch.
- The next automatic model prompt contained the write result. DeepSeek acknowledged the returned commit/blob and proceeded to inspect the workflow and matrices before building the hierarchy.
- Live tests exposed and fixed incomplete evidence tracking, model handoff formatting, lingering recovery delays and a malformed-action retry loop. Unambiguous flattened parameters are now wrapped into args; genuinely invalid actions request correction before execution. Source mutations require fenced JSON to preserve literal file contents.
- Venice's existing provider cooldown remains respected. The displayed local controller wait was until approximately 23:25 HKT; provider reset timing remains approximate. Its Agentic/Classic technical fallback is covered by simulations, not a claim of live successful Venice inference during that cooldown.
- This proves a bounded read/write/checkpoint/continue round trip. It does not prove indefinite uptime, task completion, successful long-horizon chart generation, or a merged v2 audit.
The current active task remains repo-hierarchical-audit-v2; provider expansion does not change its permitted paths or token permissions.

## Limits
A web UI adapter remains sensitive to provider DOM changes and provider restrictions. Venice's current terms prohibit scripted web-interface requests; slower scheduling does not establish permission or unlimited usage. DeepSeek's API is its documented programmable integration. No paid API, new account, purchase or token-scope expansion is activated here.

## Offline checks
Run from the extracted package directory with Node.js; no network or account keys are needed:

```text
node browser-tests.cjs
node browser-tests.cjs --classic
node loader-tests.cjs
node ownership-tests.cjs
node pacing-tests.cjs
node deepseek-tests.cjs
node deepseek-loader-tests.cjs
node mode-tests.cjs
```

The package includes the common browser runtime, loader, both current Worker source snapshots, test harnesses and a SHA manifest. The 87 checks cover browser/loader coordination, pacing and provider adapters; they are not 87 live model sessions. Shared keys and underlying service tokens are excluded.

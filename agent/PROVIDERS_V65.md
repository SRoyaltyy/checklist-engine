# Shared Venice / DeepSeek repository bridge, runtime 6.5.0

The existing Cloudflare doorman/deployer and GitHub protocol are reused. The common loader now matches venice.ai and chat.deepseek.com; no raw shared keys are included in repository source.

## Provider behaviour
- Venice keeps its existing vrb6 state/owner/cache keys. DeepSeek uses drb6 keys. Each provider's request history, cooldown and fallback cache are separate.
- Browser Web Locks prevent duplicate execution within an origin. The server task lease prevents two provider owners from mutating the same active assignment.
- DeepSeek is passive in ordinary personal tabs. Activate a dedicated task tab with https://chat.deepseek.com/?repo_bridge=1 or the userscript menu. Activation stays in that tab's sessionStorage across navigation; it does not activate unrelated conversations.
- DeepSeek selectors were inspected in the live interface: textarea placeholder Message DeepSeek; role=button with ds-button--primary and ds-button--circle; ds-button--disabled when inactive; final response container ds-assistant-message-main-content. Reasoning text is excluded from tool parsing.
- Completed final JSON uses the existing venice-v6 wire schema. The agent reads the current assignment, claims ownership, uses the same typed GitHub tools, checkpoints progress/pitfalls and restores state on rollover.
- Visible human verification stops the runtime and requires user handling. Provider usage notices retain their cooldowns.

## Pacing and Venice mode policy
- Normal request-start spacing is randomized between4and5minutes, with15attempts per rolling hour. Pending model responses and explicit backoff/cooldowns can extend actual spacing.
- Failed/unacknowledged send attempts count. Manual wake, rollover and reload preserve the budget.
- Venice prefers Agentic. Two technical response timeouts can trigger a mode switch, with a30-minute switch cooldown. An explicit provider usage cooldown prevents both preferred-mode navigation and fallback switching.
- DeepSeek has no automatic cross-service quota-routing policy; it is a separately activated provider adapter.

## Validation
77 browser/loader/ownership/pacing/adapter/mode checks passed locally.
Live status at this publication: a harmless DeepSeek compatibility prompt returned BRIDGE_DEEPSEEK_OK. Loader installation and an end-to-end GitHub read/write/checkpoint round trip are pending and must be observed before claiming live activation.
The current active task remains repo-hierarchical-audit-v2; provider expansion does not change its permitted paths or token permissions.

## Limits
A web UI adapter remains sensitive to provider DOM changes and provider restrictions. Venice's current terms prohibit scripted web-interface requests; slower scheduling does not establish permission or unlimited usage. DeepSeek's API is its documented programmable integration. No paid API, new account, purchase or token-scope expansion is activated here.

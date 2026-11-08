# Venice web-agent infrastructure: technical handoff for James

Audit date: **2026-11-09, approximately 00:03 HKT (UTC+08:00)**.

Repository: **SRoyaltyy/checklist-engine**. Runtime maintenance branch: **venice/sec-options-pipelines**.

This describes the implemented system, including its limitations. It is an external controller around an ordinary authenticated Venice web chat. Model inference runs in Venice's web service; Cloudflare supplies GitHub tools and deployment transport; GitHub stores instructions, work products, and durable checkpoints; GitHub Actions supplies optional execution. There is no local coding daemon, general desktop agent, installed cloud-drive client, or model API inference service in this implementation.

No credentials are included. Legacy credential exposure remains a separate unresolved operational concern; see section 13.

## 1. Executive assessment and assignment implications

The system has demonstrated authenticated file writes with exact readback, serial tool execution, GitHub Actions dispatch/download/artifact production, persistent state, real unattended failure reporting, browser-source hot updates, Worker deployment, and continuation after fresh-chat rollover.

It has **not** demonstrated a substantial autonomous coding feature through independent acceptance tests and reviewed PR. The harness enables that experiment; it does not establish model-level engineering competence. Its percentage is a weighted evidence-referenced checklist, not an independent correctness score.

The active assignment is still the **main/TODO.md Venice section**: monitor failed nai-sec-* / nai-occ-oi-daily jobs, report run ID and actual error, then stop. SEC/options implementation belongs to GPT; definitions belong to Kimi; calendar #96 is parked. METHODOLOGY.md begins by delegating active task lists to TODO.md. A trial requires an explicit updated Venice assignment there; creating an issue alone does not feed its full contents into this agent.

Use a dedicated venice/* work branch based on the approved current base, explicit permitted paths, an available CI entry point, measurable acceptance criteria, resource limits, and a stop condition at a reviewable PR. Keep runtime maintenance on its existing branch. The model remains a single serial worker; Actions jobs may use their own parallelism.

## 2. Topology and trust boundaries

~~~mermaid
flowchart TD
    U[Authenticated Chrome profile / Venice Classic Chat]
    L[Tampermonkey loader 2.1.0]
    R[Browser runtime 6.2.3 / DOM state machine]
    D[venice-doorman / protocol v6]
    G[GitHub checklist-engine / instructions, code, state, receipts]
    A[GitHub Actions / explicit runner workflows]
    P[venice-deployer / v10 / fixed doorman target]
    C[Cloudflare deployment API]
    U --- L
    L -->|authenticated source fetch / explicit factory| R
    R -->|JSON tools and checkpoints / Bearer auth| D
    D -->|server-held GitHub token| G
    D -->|dispatch / inspect| A
    A -->|configured download and upload code| G
    D -->|immutable commit / separate Bearer key| P
    P -->|server-held CF token| C
    C -->|replace fixed doorman script| D
~~~

**The browser is the scheduler and model runner.** Closing/discarding its tab or sleeping the PC stops that component. Cloudflare's scheduled marker is not a replacement model worker.

**The doorman is a typed API adapter.** It is not a general shell, proxy, arbitrary URL scraper, or unbounded GitHub API console. Unsupported actions fail.

**GitHub Actions is the execution plane.** Code execution, large downloads, binary processing, test execution, and artifact/release uploads must be implemented in a suitable workflow with appropriate permissions.

**Code updates are privileged.** Runtime source executes with the injected Tampermonkey functions, and deployed Worker source executes with its bound credentials. Mutable maintenance source is therefore an operational trust root, not an untrusted-plugin sandbox.

## 3. Inventory, locations, versions, source identities

All four sources below are on venice/sec-options-pipelines:

| File | Role / version | Audited Git blob SHA |
|---|---|---|
| agent/LOADER6.user.js | Installed script named Venice Bridge Loader; 2.1.0 | 05981bce4b9bb8ee41eaa4c1b29b57db5ef233b0 |
| agent/BRIDGE6.js | Remotely loaded browser runtime; 6.2.3 | 75b3df3b2f829e0101eeb92b52e498aa9cf86e5a |
| agent/DOORMAN.worker.js | Active typed transport/checkpoint service; protocol v6 | 60dda161303adbc96684c667bbec3777c5140018 |
| agent/DEPLOYER.worker.js | Fixed-target deployment service; v10 | 5e6915a6a902f0e7f3f28a2e9f496a6606d2732d |

Service endpoints:

- https://venice-doorman.fullscan-relay.workers.dev/
- https://venice-deployer.fullscan-relay.workers.dev/

The authenticated live check returned doorman HTTP 200 / version 6, runtime source SHA 75b3df3b2f829e0101eeb92b52e498aa9cf86e5a, context branch venice/sec-options-pipelines, and deployer HTTP 200 / v10 / target venice-doorman. Source equality for the live browser source endpoint was checked. Cloudflare dashboard revision IDs, current cron expression, token scope inventory, and GitHub branch-protection settings were not independently re-audited.

Existing standalone Tampermonkey **Venice Repo Bridge** was disabled. Do not run it alongside the loader. The scripts do not pin a model ID. Final interactive checks used **Classic Chat with DeepSeek V4.1 Flash (1017)** as selected in the UI. Agentic mode has adapter/mock coverage and earlier use; the final startup/rollover acceptance pass used Classic.

Browser entry point: https://venice.ai/chat/classic . Tampermonkey matches https://venice.ai/* and starts at document-idle. Chrome's Performance setting now contains venice.ai under **Always keep these sites active**. This addresses Memory Saver discarding; it does not guarantee unthrottled background timers or prevent OS sleep.

## 4. Credentials, bindings, and available authority

### Browser / loader

Granted APIs: GM_xmlhttpRequest, GM_getValue, GM_setValue, GM_registerMenuCommand. The declared cross-origin connect host is the doorman Worker. There is no GM_download grant, local filesystem daemon, or native desktop-control API.

CONFIG contains worker URL, maintenance branch, and the local key retrieved from **vrb6.key**. The key is supplied in an Authorization header; it is not embedded in the current published loader.

### Doorman bindings expected by the deployed system

| Name | Purpose |
|---|---|
| GITHUB_TOKEN | Server-side GitHub API authority |
| DOORMAN_KEY | Authenticates browser/API callers |
| DEPLOY_KEY | Authenticates doorman-to-deployer calls |
| GITHUB_REPO | Must equal SRoyaltyy/checklist-engine |
| WAKE_BRANCH | Runtime/state/source branch; configured maintenance branch |
| DEPLOYER | Must resolve to the fixed deployer origin |

### Deployer bindings read by its code

| Name | Purpose |
|---|---|
| DEPLOY_KEY | Incoming deployment authentication |
| CF_TOKEN | Cloudflare script/settings API authority |
| CF_ACCOUNT | Target Cloudflare account |
| SCRIPT_NAME | Must equal venice-doorman |
| GITHUB_REPO | Must equal SRoyaltyy/checklist-engine |

These are binding names and code requirements, not a new claim that all bindings are secret_text or that token scopes were minimized. The successful deployment path preserves existing binding types. Credential values and authoritative scope configuration are not in this document.

Direct repository writes are limited by server code to venice/* branches. The only repository target is checklist-engine. There is no direct merge, file-delete, arbitrary repository, token-export, or arbitrary proxy operation.

This is **not** an end-to-end security sandbox: the same system permits workflow source edits and runner execution. Runner permissions/secrets and code deployed into the Worker have their own authority. A branch restriction on the direct tool cannot prove that arbitrary dispatched code is incapable of making other changes with a separately available token.

## 5. Loader: boot, hot update, fallback, and controls

The loader GETs doorman ?op=source at startup and every 60 seconds, with a cache-busting timestamp, Authorization: Bearer <local key>, and a 30-second request timeout. Source responses contain text and blob identity; the current implementation also returns the underlying file's base64 representation, which the loader does not need.

It compiles source using:

~~~javascript
new Function(
  'GM_xmlhttpRequest', 'GM_getValue', 'GM_setValue',
  'window', 'document', 'CONFIG',
  source
);
~~~

BRIDGE6.js is a **function body with a top-level return**, not a standalone script that should be pasted into a page unchanged. It returns a lifecycle handle. Injection is explicit; the loader no longer rewrites function source with ad hoc string patches.

Hot-update rules:

1. Unchanged blob SHA causes no restart.
2. A remembered bad SHA is skipped.
3. An existing runtime must report canUpgrade: true: not pumping and phase idle.
4. Candidate syntax is compiled before stopping the existing runtime.
5. The candidate must return stop() and health(); otherwise it is rejected.
6. A 10-second loader watchdog promotes a candidate to vrb6.lastgood after at least 30 seconds, a fresh runtime heartbeat (<90 seconds), ready=true, and a completed checkpoint at/after boot.
7. A runtime heartbeat older than 150 seconds is stopped and blacklisted by SHA; a different cached healthy source is restored if present.
8. A gap >120 seconds in the loader's own watchdog is treated as browser resume; that sample does not blacklist the runtime.
9. A source fetch failure can boot the local healthy cache if there is no active runtime.

Cache keys include vrb6.lastgood and vrb6.badSha. This is a single healthy fallback, not an unlimited version archive. Syntax/heartbeat/one completed checkpoint are functional checks, not semantic code review or an automated feature-test gate. There is no overall candidate-progress deadline if its pump remains alive but never completes useful work.

Tampermonkey menu controls:

- Configure Venice bridge key: stores locally, then reloads.
- Wake Venice now: sets next wake due and enables the runtime.
- Continue in a fresh chat: sets a rollover request.
- Venice runtime status: bounded version/phase/ownership/enabled/heartbeat/next-wake/last-completed-turn diagnostics.

The green runtime badge toggles pause/resume on left click and requests fresh chat on right click. The gold loader badge shows testing/healthy/update/error status. A newly loaded known source can display testing until its next checkpoint.

Loader source/metadata itself is updated through Tampermonkey's normal update mechanism. Pushing LOADER6.user.js is not the same as an immediate live reinstall. New extension permissions, credential changes, arbitrary browser settings, or repair of a broken loader require operator involvement.

## 6. Browser runtime: ownership, DOM adapter, state machine, scheduling

### Ownership and local state

The runtime stores its in-flight JSON under **vrb6.runtime**. Only the owner writes that store. It requests the same-origin Web Lock **venice-bridge-runtime-v6** with ifAvailable:true. Temporary contention is retried after five seconds; the latest persisted state is reloaded on acquisition. Without Web Locks it falls back to single-tab operation.

This is ownership within the browser's relevant origin/storage context. It is not a distributed lease across machines, independent profiles, or different installations sharing the GitHub branch.

The returned handle exposes version, health(), status(), stop(), wake(), and rollover(). health reports ready, lastTick, lastCompletedAt, phase, enabled, owner, and canUpgrade. stop clears runtime timers, aborts tracked requests where possible, releases the lock, and removes its badge. It cannot undo a server mutation already accepted.

The handle is also assigned to window.__venice6 in the userscript execution environment. Page-console access from a different isolated world was not reliable; use the loader menus/handle rather than assuming the normal page console can see it.

### DOM adapter

- Composer lookup checks the Agentic input test-id subtree, textarea, then visible contenteditable elements.
- Textareas use the native value setter plus an input event; contenteditables use selection/insertText with a textContent fallback.
- The sender prefers Agentic input actions, then the composer form/dropzone, then visible page buttons.
- Labels and send/arrow-up SVGs identify the send button. The bridge's own badge is explicitly excluded.
- Generation detection uses visible stop-generation button labels/test IDs.
- Only outermost **.assistant** message roots are parsed.
- The baseline assistant count is saved before sending; old assistant history is not eligible as the current reply.
- JSON is read from code/pre blocks or the new assistant text. It must have bridge=venice-v6, the exact current turn ID, and actions as an array.

These are DOM heuristics. A Venice UI change can break them. They are not native Venice tool integration, general browser automation, or an official stable Venice web API.

### State machine and timing

~~~text
idle -> composing -> sending -> waiting -> executing -> checkpointing -> idle
                  retry if send unacknowledged      |
                                      transport error -> retrying
idle -> rolling -> idle/new chat -> composing
~~~

| Condition | Implemented behavior |
|---|---|
| Runtime pump | Every 2 seconds, subject to browser scheduling |
| Idle completed/no-action turn | Next turn after 300,000 ms |
| Completed turn with actions and done=false | Continue after 3,000 ms |
| Composer unavailable, busy, or draft present | Wait 15,000 ms before preparing again |
| Worker request | 90,000 ms client timeout |
| Send not acknowledged | After 15,000 ms, return to composing |
| Valid completed reply | Must be stable for >5,000 ms and not generating |
| Invalid settled reply | After >25,000 ms, request another structured continuation |
| Repeated invalid replies | Two failures request rollover |
| Response timeout | After >360,000 ms, request rollover after 15,000 ms |
| Transport-uncertain tool | Retry after 30,000 ms using the same action ID |
| Checkpoint/execution exception | Retry after 30,000 ms |
| Other pump exception | Return to idle with 30,000 ms delay |
| Rollover navigation not confirmed | After 45,000 ms, request another attempt after 30,000 ms |

The five-minute interval begins **after** execution/checkpoint completion. Browser background scheduling, network latency, model generation, and state-machine transitions add time. Observed background intervals of roughly eight to nine minutes are not a configured SLA. There is no hard total-turn or total-cost budget.

Pause blocks new prompts and starting subsequent actions. An already-submitted request can complete, and its receipt/checkpoint may still be saved. User drafts are not overwritten intentionally. A permanently changed composer or missing new-chat control can still prevent progress.

## 7. Prompt construction and model response contract

Before preparing each turn, the runtime requests fresh context. The prompt contains identity, task authority, the tool catalog, one JSON schema example, working rules, latest raw tool results from local state, and a compact current GitHub snapshot.

Rules explicitly request: one subtask at a time; orient/act/inspect/verify/checkpoint; preserve the plan unless evidence/instructions change; use returned proofs; do not invent progress; use report_failure for SEC/OI reporting; distinguish skipped from failed; retain concise notes; change approach or record a blocker after repeated failure; never emit legacy @@ envelopes or require a human to execute the listed tools.

The runtime omits duplicate PROGRESS.md Markdown from the model snapshot, truncates old state.summary to 4,000 characters in that snapshot, and preserves full current local tool results for the next turn. Raw file/log results are not duplicated wholesale into durable STATE summaries.

Example response:

~~~json
{
  "bridge": "venice-v6",
  "turn": "<exact-current-turn-id>",
  "summary": "Factual work completed so far; distinguish planned from verified.",
  "next": "Inspect the returned result, then perform one exact next step.",
  "notes": "Durable file map, decisions, failed approaches and open questions.",
  "plan": {
    "goal": "Specific assigned task",
    "why": "How it advances the project",
    "gantt_row": "[exact assigned row]",
    "current_task": "t1",
    "tasks": [{
      "id": "t1",
      "title": "One concrete subtask",
      "acceptance": "Observable passing condition",
      "status": "doing",
      "weight": 1,
      "evidence": [],
      "blocker": ""
    }]
  },
  "actions": [{
    "tool": "read_file",
    "args": {"path": "path/to/file.py", "branch": "main"}
  }],
  "done": false
}
~~~

At most **four actions per packet**, executed serially. The action ID is generated by the controller as <turn>.<zero-based-index>; the model does not choose it. A non-transport failed action stops the remaining batch. Its result is checkpointed and supplied to the next model turn. No successful tool call by itself proves the packet's pre-written summary is accurate.

Implementation detail: a special repair flag is set on invalid JSON but reset in prepare() before prompt construction; the extra repair-specific sentence therefore is not a dependable mechanism in 6.2.3. The normal schema instructions are repeated, and repeated invalid responses still trigger rollover.

## 8. Doorman HTTP protocol

All normal operations require **Authorization: Bearer <DOORMAN_KEY>**. Query-string keys do not authenticate. OPTIONS returns CORS headers without authentication. The CORS origin is https://venice.ai; methods GET, POST, OPTIONS; headers Content-Type and Authorization. CORS is not a substitute for authentication.

| Request | Purpose / result |
|---|---|
| GET /?op=ops | Version, supported operations, fixed repository, branch-write policy |
| GET /?op=source | Runtime file text, blob SHA and base64 from the configured maintenance branch |
| GET /?op=context | Fresh instructions, checkpoint, notes, available evidence and relevant run metadata |
| POST /?op=tool | JSON command envelope; typed tool result |
| POST /?op=checkpoint | Persist plan, human progress, optional notes and final state |

Mutation endpoints require POST with JSON. The Worker rejects raw request text longer than 300,000 JavaScript string characters. Endpoint validation/exceptions normally return HTTP 400 with ok:false. Tool execution errors inside runtimeTool normally return HTTP 200 with ok:false and an error; failed mutation results are also retained in their receipt. Missing authentication returns 401.

Tool envelope:

~~~json
{
  "id": "<stable-action-id>",
  "action": "write_file",
  "args": {
    "branch": "venice/example-task",
    "path": "example.py",
    "text": "exact UTF-8 source text",
    "expected_sha": "<blob-sha-from-read>"
  }
}
~~~

IDs must be 8–120 characters from letters, digits, dot, dash, underscore. Unknown actions fail. Safe paths reject leading slash, backslash, query/hash/control characters and dot/dot-dot path segments. Branch writes must match venice/* and cannot contain '..'.

### Complete model-visible tool surface

Read tools default to main. Write/deploy tools default to the maintenance branch unless an explicit branch is supplied. **A trial should supply its dedicated branch explicitly on every write and on branch-specific run queries.**

| Tool | Arguments / behavior / significant limits |
|---|---|
| read_file | path; branch=main; start_line=1; end_line defaults to start+249; optional character offset. Returns text, sha, line/character counts, offset, next_offset, truncated. Text capped at 12,000 characters per response; follow next_offset for a complete read. Text decoding is not a binary-file transport. |
| list_files | path optional for root; branch=main. Contents listing reduced to first 150 entries: path/type/size/sha. No continuation cursor. |
| grep | path, query, branch=main. Case-insensitive literal substring search in one file; first 30 matching lines. No regex or repository-wide code search. |
| write_file | path, text, branch, optional message, optional expected_sha. Exact whole-file replacement/creation; maximum 250,000 string characters; SHA concurrency check if provided; exact post-write readback. Unchanged text is a no-op result with blob_sha. |
| edit_file | path, find, replace, branch, optional message. find must be nonempty and match exactly once; replacement uses the just-read blob SHA for concurrency checking. |
| create_branch | branch must be venice/*; base defaults to main and is a branch ref, not an arbitrary detached commit interface. Returns new branch and SHA. Existing branch yields an API error. |
| runs | branch=main. First 30 recent runs, with ID/path/name/status/conclusion/URL/head SHA. No pagination or filter parameters beyond branch. |
| run_status | run_id. Status, conclusion, URL, head SHA, branch for one run. |
| run_jobs | run_id. First 30 jobs, each with ID/name/conclusion/URL/check-run URL and step name/conclusion. No pagination. |
| annotations | check_run_id. First 30 annotations; no pagination. |
| job_log | job_id, optional run_id for constructing the displayed job URL. Full log fetched internally; returns final 9,000 characters plus up to 15 extracted error/traceback lines and total size/truncation metadata. |
| report_failure | run_id. Specialized SEC/OI failed-run report with deterministic facts, issue/correction posting and per-run deduplication; details below. |
| create_issue | title, body, optional dedupe_key. Adds action/dedupe markers. Dedupe checks only the first 100 issues from creator=@me; this is not an unbounded indexed search. |
| comment_issue | issue number, body. Adds action marker. Per-action receipt protects ordinary retries; no general semantic cross-turn dedupe_key behavior for comments. |
| create_pr | title, body, branch. Base is hardcoded to main. Adds action marker. There is no base argument, PR-update, review, merge, or general existing-PR lookup tool. Pushing to an existing PR's head branch updates that PR through normal GitHub behavior. |
| dispatch | workflow filename matching *.yml or *.yaml, venice/* branch, optional inputs. Calls workflow_dispatch. Returns acknowledgment/workflow/branch, **not the dispatched run ID**. Correlate subsequent runs by branch/source/time and a task-specific input/artifact if supported. |
| deploy_worker | branch must be the configured maintenance branch. Resolves immutable HEAD via authenticated GitHub and asks the fixed deployer to deploy doorman source. Cannot select arbitrary Workers. |

Absent direct tools include: arbitrary issue/PR-body/comment/diff reads, repo-wide search, terminal/exec, file deletion/rename, merge, rebase, close/review PR, workflow cancellation, artifact download/upload, release CRUD, secret administration, arbitrary HTTP fetch, browser navigation outside the chat adapter, and PC/cloud-drive filesystem access. A suitably authorized runner workflow can implement additional processing, but that is explicit code with separate permissions, not a preexisting generic tool.

### Context snapshot details

The Worker loads:

- Full main/TODO.md, extracting only the Venice section up to the next level-two heading. Missing Venice section fails closed.
- Full main/METHODOLOGY.md internally, exposing only the first 22 lines / at most 6,000 characters plus guidance to read task-specific rules explicitly.
- agent/runtime/PROGRESS.md, STATE.json, NOTES.md on the maintenance branch.
- First 50 main-branch Actions runs, then filters SEC/OI paths/names and retains at most 15.
- Available evidence identities for the current TODO.md and METHODOLOGY.md blobs.

Historical methodology assignments are deliberately not automatically reintroduced. A detailed issue or task-specific document must be reproduced in a readable file or be made accessible by an additional explicit workflow/tool. A large volume of unrelated main CI runs can push relevant failures outside the fixed snapshot window; these listing limits do not prove an exhaustive historical sweep.

## 9. Receipts, idempotency, exact writes, and checkpoint consistency

Mutation receipts live at agent/runtime/receipts/<id>.json on the maintenance branch. They store **action arguments** as well as status/result and time. Never include credentials or sensitive payloads in arguments: this repository's receipts are not a secret vault.

Execution protocol:

1. If a receipt exists, action and JSON.stringify(args) must exactly match.
2. A done receipt returns the stored result plus replayed:true.
3. A non-done receipt returns uncertain:true; the caller must reconcile GitHub state/run history instead of blindly replaying the mutation.
4. For a new mutation, save a running receipt before the action.
5. Execute the action and save a done receipt containing success or failure.

Read tools do not create receipts, although any existing same-ID receipt is checked. The browser retries a transport-uncertain action using its original ID. Action arguments with different property ordering can fail the exact-string comparison.

This is **best-effort durable deduplication**, not a database transaction or proven global exactly-once execution. A request can fail after the side effect but before final receipt publication. Multiple independent callers can race between receipt lookup and claim. The browser lock reduces ordinary local duplication but is not a distributed server lock. Some operations also have content/SHA guards or specialized report markers.

Exact write details: read existing blob; optionally require expected_sha (null can require absence); use GitHub's current blob SHA for PUT; read back and compare complete text. Conflicts/error responses are surfaced. This protects write integrity, not whether the new code is correct. An unchanged result has blob_sha but no new commit; the browser's generic evidence collector does not automatically turn every blob_sha-only no-op into a file@SHA proof.

### Durable checkpoint layout and limits

| File | Contents |
|---|---|
| agent/runtime/STATE.json | Version=6, UTC at, turn_id, summary, next, normalized plan, compact tool_results, blockers, accumulated evidence, done |
| agent/runtime/PLAN.json | Goal, why, Gantt row, current task, normalized weighted tasks, computed percentage |
| agent/runtime/PROGRESS.md | Human-readable goal/rationale/task table/latest work/exact next step/blockers/evidence |
| agent/runtime/NOTES.md | Concise durable file map, decisions, failures, proven fixes and open questions |
| agent/runtime/receipts/*.json | Mutation claim/result records |
| agent/runtime/reports/<run-id>.json | Persistent specialized failed-run reporting result |

Per checkpoint, the Worker writes PLAN, PROGRESS, optional NOTES, then STATE, as separate verified GitHub writes/commits. Identical files are no-ops; timestamps/summary changes commonly produce new commits. STATE is the last-written completion marker, but the bundle is **not atomic**: partial failure can leave newer plan/progress/notes with an older STATE. There is no checkpoint generation transaction across all files.

Limits: summary 10,000 characters; next 4,000; notes 10,000; at most 25 tasks; task title 300; acceptance 500; goal/why 2,000 each; Gantt row 300; blocker 500; task weights clamped to 1–20; last 100 unique accumulated evidence entries retained. Accepted task statuses: todo, doing, done, blocked.

Percentage = floor(100 * weight of done tasks / total task weight). Done tasks lacking any evidence string in the accumulated known pool are downgraded to doing. The pool combines previous evidence and supplied current evidence; the controller collects returned commits, URLs, file@SHA read identities and run/job URLs.

**This is reference bookkeeping, not independent verification of task semantics.** The Worker does not fetch every cited URL to prove the acceptance criterion or validate that a green run exercised the intended code. Model summaries can still be false. It is not a time-based Gantt scheduler, critical-path calculation, calibrated effort estimate, or measure of the whole project's completion.

The browser forwards task-level blocker fields inside plan, but does not forward an arbitrary top-level packet.blockers into checkpoint data. Use plan.tasks[].blocker; the remote top-level blockers array will ordinarily be empty through this client.

Raw tool results remain in local GM state for the next model turn; remote tool_results are compact metadata/facts, not a complete raw result archive. After a crash/new installation, re-read required files/logs instead of assuming the entire previous tool response survives remotely.

Keep rolling plans compact; the 25-task cap truncates the tail. There is no receipt garbage collector or automatic Git-history compaction.

## 10. Rollover and long-horizon continuity

Proactive rollover is requested before the next turn when completed chatTurns >=10 or accumulated prompt+reply character count >=100,000. These are heuristic thresholds, not measured Venice context tokens or its provider's absolute chat limit.

It also requests rollover after a six-minute response timeout or repeated invalid structured responses. It clicks a visible New chat/New conversation/Start new control. It confirms a different pathname, a composer, no generation, and an empty assistant history. Empty Classic/Agentic landing pages have a special fresh-landing case. It does not delete the previous conversation.

The next prompt reloads current instructions, plan/state and notes. Existing in-flight local state can survive a browser reload. Large attachments and the whole conversation are not migrated; only written summaries, notes, links and explicit file re-reads provide durable context.

There is no guarantee that a model will preserve all important details in its notes. Unexpected manual navigation, cleared GM storage, revoked sessions, or changed message DOM can require recovery. Thresholds were exercised live in Classic; unlimited provider chat availability has not been established.

## 11. Specialized failure-reporting path

report_failure(run_id) is intentionally narrower and more deterministic than general model prose:

1. Return a saved per-run report result immediately if present.
2. Fetch the actual run and require conclusion=failure plus SEC/OI workflow naming/path match.
3. Fetch first 30 jobs and examine at most the first three failed jobs.
4. Read each failed job log. GitHub's log redirect is handled manually; only approved HTTPS signed-log host patterns are followed, without forwarding Authorization to the signed host.
5. Extract up to the final 15 traceback/Error/Exception/##[error] lines from the complete fetched log **before** truncating the displayed tail.
6. Report actual failed/skipped step conclusions. If the log is unavailable, explicitly say so and infer no root cause.
7. Search the first 100 issues for a per-run marker or an existing run link, excluding PRs. Inspect first 100 comments for a verified marker. Create one issue or one verified correction comment.
8. Save the canonical URL/facts in reports/<run-id>.json for cross-turn/chat deduplication.

The tool establishes recorded run/log facts, not a complete root-cause analysis. Its finite job/issue/comment windows and durable-file/race caveats still apply. It is not a generic report tool for every workflow family. The model's notes contain some deliberately-unreported historical run IDs; that policy is not a server-side universal suppression list and should be reviewed against the current assignment.

## 12. Runner execution, downloads, and storage destinations

The browser/Worker does not expose a terminal. A workflow is the explicit execution contract:

1. Create/update code on the permitted work branch.
2. Trigger an existing appropriate workflow or allow an approved PR/push check to run.
3. Discover/correlate the run and inspect its jobs/logs/results.
4. Have workflow code publish useful structured receipts/artifacts.
5. Read/check the result before claiming acceptance.

During commissioning, a new workflow absent from the default branch could not be dispatched (404). The successful transport test used the already-registered impact_diff.yml workflow path **only on isolated branch venice/bridge-transport-proof-20261107**, replacing that branch's copy with a three-minute read-only download test. Main's production impact workflow was untouched. This was a transport test, not the recommended permanent test-runner architecture.

For a new trial, James should identify/register an appropriate workflow with defined branch inputs and permissions. A dispatch acknowledgment does not include a run ID or prove tests passed. Avoid uncorrelated polling of main when the trial runs on another branch.

| Destination / operation | Current support |
|---|---|
| Public internet download in a runner | Demonstrated for repo TODO.md; other sources depend on their actual access/rate/size restrictions |
| Runner disk | Temporary job workspace; persistence requires upload |
| GitHub job artifacts | Demonstrated with actions/upload-artifact@v4 |
| Ordinary repo files | Direct UTF-8 text writes; large datasets/binaries should use another storage path |
| GitHub release assets | Implementable in a suitably permitted workflow; no direct release CRUD/upload tool exposed |
| PC disk | No installed arbitrary local file agent or download-to-PC tool; operator can download produced artifacts |
| Drive/Dropbox/S3/R2/other cloud storage | No configured generic connector/bucket tool; requires explicit workflow integration and credentials |
| Authenticated vendor data | Requires existing permitted access/credentials; this setup does not bypass authentication or source restrictions |

The artifact in the proof workflow has **three-day retention**. Do not treat it as permanent data storage. There is no built-in artifact downloader in the model-visible bridge. Use a separate runner step or operator download when required. No global storage budget, download policy engine, or dataset completeness validator has been implemented.

## 13. Worker maintenance, deployment, and unresolved credential risk

### Browser runtime update

Write agent/BRIDGE6.js on the fixed maintenance branch. The loader discovers and activates it at an idle boundary. A successful functional checkpoint promotes it locally. This path was exercised live across 6.2.x updates.

### Doorman deployment

Write agent/DOORMAN.worker.js on the maintenance branch, then call deploy_worker. The doorman resolves branch HEAD to an immutable 40-character commit and POSTs to the fixed deployer origin with its separate deployment key.

Deployer v10:

- Requires Bearer deployment authentication and POST.
- Pins repo, maintenance branch and target **venice-doorman**.
- Requires an immutable 40-character lowercase hexadecimal commit.
- Fetches that commit's source and the current fixed branch's source from raw.githubusercontent.com and requires exact text equality.
- Accepts source length 500–150,000 characters.
- Reads current Worker settings and requires GITHUB_TOKEN, DOORMAN_KEY, DEPLOY_KEY, GITHUB_REPO, WAKE_BRANCH, DEPLOYER binding names.
- Preserves existing binding **types** with keep_bindings; carries compatibility date/flags and observability in submitted metadata.
- Removes global_fetch_private_origin and ensures global_fetch_strictly_public, which fixed the observed Worker-to-Worker Cloudflare 1042 failure.
- Uploads a module Worker and re-reads settings to verify each prior binding name/type remains.

The post-check verifies names/types, not secret values or every Cloudflare setting. This is not a complete account backup, arbitrary settings editor, automatic rollback service, test-gated release pipeline, or self-deployer-update operation. Only the fixed doorman can be deployed through this route. Updating deployer code itself or adding/changing bindings requires a separate operator deployment path. Fresh GitHub raw mirrors have produced temporary source-mismatch responses; later retries worked.

### Security qualification James must retain

Legacy supplied/published material exposed shared bearer keys. **Rotation has not been confirmed. Treat those legacy credentials as compromised until rotation is completed.** Current source avoids hardcoded key values and query-string authentication, but that does not revoke old exposed values.

Do not include real keys in task specs, prompts, repo files, CI output or receipts. The doorman key authorizes mutations and maintenance-code changes; maintenance source can execute with server credentials after deployment. CORS and venice/* direct-write checks do not neutralize a stolen authenticated maintenance path. Before expanding access or using confidential data, coordinate equivalent rotation of Worker secrets and the local GM key and assess legacy publication/history cleanup.

## 14. Scheduling residue and legacy diagnostics

The active doorman includes a scheduled(event,env,ctx) handler. On a Cloudflare scheduled event it reads agent/WAKE.json and writes pending=true, timestamp ID/set_at and reason=scheduled heartbeat, unless its prior set_at is less than **840,000 ms (14 minutes)** old.

The **current v6 browser runtime does not consume or acknowledge WAKE.json**. Its own timer drives model turns. The configured Cloudflare cron expression was not queried in this audit. A recent WAKE.json write proves scheduled events are occurring; it does not prove a second independent model scheduler. This residue adds GitHub writes and should be reviewed as an infrastructure cleanup task.

Two legacy diagnostic workflows on the maintenance branch, nai-verdict.yml and nai-verdict2.yml, previously ran on every push, repeatedly fetching old run 41413529249 and changing only collected_at in agent/RESULT.json / RESULT2.json. This caused unnecessary runner jobs on routine checkpoints.

Both are now **workflow_dispatch only**, with required explicit run_id and no default old run. The readback-confirmed changes are commits c065ed9fe815bde161f16b4335109f11370f9b68 and 82d02e1c2e75994d0a474c3996020e42f283320f. Main and the assigned production SEC/options pipeline files were not changed. Already-started helper jobs could finish after the edit; automatic future push triggers were removed.

Legacy agent/PROGRESS.md, WAKE.json and RESULT*.json are distinct from the authoritative v6 agent/runtime/ checkpoint files. Do not infer current progress from a timestamp-only legacy result.

## 15. Evidence and verification coverage

### Live checks and real operation

- Exact write/read/replay proof: commit **a089ee8ac06ad75112451d56543736dcb6393b0b**.
- Runner dispatch + download + artifact: [run 42375131645](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42375131645), artifact venice-bridge-download-proof; isolated proof workflow blob a6c96d990159ca0abc633ad12cc7f06aac34c249. Artifact ID 13574922358; digest sha256:bfe6508921b932491a4d378c7cb08de6770eb2d75605a8fe40e3828a9a8597ea.
- Worker self-deployment returned success with bindings_preserved=true on multiple executions, including source guard 60dda161303adbc96684c667bbec3777c5140018 and resolved commit 8cffe05a5fd718832400211f5f162823e824eb16.
- Fresh-chat restoration followed by corrected model file write: commit **8f1cbd8c36321a47dee6192d8e8ed47440fa0a56**.
- Unassisted checkpoints at **2026-11-08 01:24:27 and 01:33:08 HKT**; fresh-page startup checkpoint **01:38:59**, followed by proactive new-chat checkpoint **01:39:45**.
- A later real failed run **42399694729** was reported as [issue #223](https://github.com/SRoyaltyy/checklist-engine/issues/223) at **2026-11-08 02:11:26 HKT**, approximately four minutes after its logged exception. It correctly reports failed occ_oi_daily.py, skipped oi_probe.py and the exact ValueError.
- Earlier inaccurate model reports were corrected using exact logs: [#220 canonical correction](https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739), [#221 canonical correction](https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770). These are limitations of prior model reasoning, not successes to hide.
- Audited saved STATE at **2026-11-08 23:53:27 HKT**, turn **mw80e1y7-zvyzijmx**, records another no-new-reportable-failure sweep and normalized plan 100%. This demonstrates later continued operation, not a proof of uninterrupted availability throughout the entire interval.

### Automated tests

**49 assertions/checks pass** across these dependency-free Node scripts:

| Command | Count | Coverage |
|---|---:|---|
| node runtime-tests.cjs | 17 | Transport auth, current context, exact writes, receipts, stale SHA, paging, checkpoint/notes/progress, factual reporting/dedup, rejected legacy endpoints, factory compilation |
| node browser-tests.cjs | 10 | Agentic-style mocked DOM adapter, current reply/turn, serial tool/checkpoint cycle, pause/resume, evidence collection, rollover, stale reply rejection, stop |
| node browser-tests.cjs --classic | 10 | Classic fallback adapter including own-badge exclusion |
| node deployer-tests.cjs | 3 | Binding types/flags, immutable/source match, fixed target |
| node loader-tests.cjs | 6 | Functional promotion, unchanged-source no restart, idle update, sleep/resume tolerance, controls |
| node ownership-tests.cjs | 3 | Ownership retry/acquisition, avoiding context fetch without composer, stop cancels retry |

These are mocked transport/DOM/control tests plus separately documented live checks. They are not 49 real-world coding tasks, a full browser end-to-end suite, a security audit, or a proof that arbitrary future changes pass.

The accompanying offline verification ZIP contains the four exact audited source snapshots under the filenames expected by these scripts, the scripts, a SHA manifest and instructions. It uses dummy mock credentials only, performs no live network calls, and was run with Node **v24.22.1**. Git blob hashes are checked against section 3 before testing.

## 16. Known operating gaps and trial risks

1. No direct general issue/PR reader: put complete assignment requirements in TODO and readable files; do not rely on an issue title/number.
2. No direct terminal, artifact/release/cloud storage tool: define runner workflow, outputs and permissions before assignment.
3. No independent off-browser watchdog or restart/login capability. PC sleep, tab shutdown, session expiration, provider limits and network outages remain external dependencies.
4. Browser selectors and model formatting are fragile interfaces. There is no official Venice web agent API integration.
5. Listing limits are finite, and no general pagination exists outside file offset reads. Absence from a run window does not prove no missed execution/failure.
6. A prompt rule to change approach after two failures is not a hard semantic loop detector. Repeated unproductive but valid JSON can continue.
7. The receipt protocol and checkpoint bundle are not atomic/distributed transactions. Inspect uncertain mutations before issuing new IDs.
8. Source auto-updates do not require CI/review. A syntactically valid but semantically wrong runtime can still be adopted.
9. Progress proof references can be irrelevant to the acceptance criterion; no independent semantic/test-result validator exists.
10. Raw history/attachments do not roll over. Important facts omitted from notes can be lost.
11. There is no global quota, spend, artifact-retention, task-priority, context-token, or repository-growth controller. Frequent checkpoints and receipt commits consume API calls/history.
12. No full task queue, scheduler DAG, true Gantt dependency model, distributed lease, multi-agent delegation, or independent reviewer is built in.
13. The visible model remains responsible for reasoning and task selection within its lane. The harness does not improve model weights or guarantee engineering competence.
14. Legacy bearer-key exposure remains unresolved; do not confuse source hardening with credential revocation.

## 17. Assignment contract for a useful long-horizon trial

James should explicitly update main/TODO.md's Venice section and name a readable spec file. A suggested structure:

~~~yaml
task_id: VENICE-TRIAL-001
goal: One useful, bounded project deliverable
gantt_row: Exact existing project row
spec_file: docs/VENICE_TRIAL_001_SPEC.md
base_branch: main
base_commit: Reviewed starting commit
work_branch: venice/trial-001
allowed_paths:
  - Explicit implementation paths
  - Explicit test paths
protected_paths:
  - Runtime/deployer/credentials unless infrastructure is the assigned task
acceptance:
  - Deterministic observable behavior
  - Relevant tests, including important failure cases
  - Actual CI run tied to the submitted source
  - Reproducible output/receipt where data are involved
execution:
  workflow: A registered, reviewed workflow filename
  inputs: Explicit inputs/correlation identity
  timeout: Bounded job duration
  network_and_storage: Approved sources and output destination
  permissions: Minimum required job permissions
resource_limits:
  retries: Explicit task-level limit
  downloads: Explicit size/source scope
  infrastructure_changes: Excluded unless needed by this task
stop_condition: Open a PR with exact commit, test results, evidence and unresolved limits
review_owner: James
~~~

This is an assignment template, **not a schema the current Worker enforces**. The current server only enforces its actual tool/branch/path/size rules.

For task switching, allow the current turn to finish or pause first; inspect pending receipts before changing scope. A new assignment is read at the next prepare step, not retroactively before an already-submitted operation.

For this trial, the supervising Codex chat should follow the actual branch/commits, checkpoint freshness, source-matched CI results, output receipts and PR, and independently verify acceptance. No off-browser supervisor automation has been installed. Judge success by a completed useful deliverable, not the number of chat turns, checkpoints or green transport tests.

The current monitoring task may be retained as a secondary duty only if James explicitly prioritizes it relative to the trial. Do not let the agent revive superseded calendar/data ownership from historical methodology entries.

## 18. Operator runbook and emergency recovery

- Normal use: open the Classic Chat entry point in the existing authenticated Chrome profile; loader enabled; old standalone bridge disabled; badge ON. No manual wake prompt is required. A saved future nextAt can delay initial activity.
- Inspect: read STATE.json at/summary/next, PLAN.json, NOTES.md and latest receipts. Compare source-matched Actions results and branch changes; timestamps alone do not establish progress.
- Pause: badge click; wait for accepted operations to finish or become an uncertain receipt. Pause is not rollback.
- Force continuation: loader Wake Venice now menu; fresh-chat menu/right click when appropriate.
- Browser reload: local in-flight state and healthy source cache are reused if preserved. Re-read remote state if local storage was cleared.
- Failed mutation: reconcile affected file/issue/PR/run/deployment before issuing a new action ID; never blindly repeat an uncertain dispatch/write.
- Broken runtime update: inspect loader status/bad SHA/cache and restore a reviewed runtime source on the maintenance branch. The loader can adopt a new SHA at a safe boundary, but a broken loader itself needs operator repair.
- Broken Worker/deployer/credentials: use a separate authenticated operator deployment/configuration path. This system cannot guarantee repair when its own control path is unavailable.
- Storage/publication: keep large binary data off ordinary text commits; define durable artifact/release/bucket retention explicitly; do not put secrets in public task arguments or receipts.

## 19. Source and proof links

- [Loader source](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/LOADER6.user.js)
- [Runtime source](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/BRIDGE6.js)
- [Doorman source](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/DOORMAN.worker.js)
- [Deployer source](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/DEPLOYER.worker.js)
- [Current assignment](https://github.com/SRoyaltyy/checklist-engine/blob/main/TODO.md#venice)
- [Master methodology and delegation to TODO](https://github.com/SRoyaltyy/checklist-engine/blob/main/METHODOLOGY.md)
- [Runtime state](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/runtime/STATE.json)
- [Runtime plan](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/runtime/PLAN.json)
- [Durable notes](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/runtime/NOTES.md)
- [Human progress](https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/runtime/PROGRESS.md)
- [Runner transport proof](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42375131645)
- [Organic failure report](https://github.com/SRoyaltyy/checklist-engine/issues/223)

Repository source and active state links are mutable. Use the audited blob SHAs and the exact source snapshots in the verification package when reproducing this specification.
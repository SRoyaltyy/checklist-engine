# Venice persistent web runtime v6

The browser is the model runner. Cloudflare is the GitHub tool transport. GitHub stores the authoritative instructions and durable task checkpoint.

## Active files

- `agent/LOADER6.user.js`: stable Tampermonkey loader, version 2. The installed script remains named **Venice Bridge Loader**. The standalone legacy **Venice Repo Bridge** entry stays disabled.
- `agent/BRIDGE6.js`: remotely updated browser runtime. The loader compiles it, runs it with explicit Tampermonkey functions, and receives a lifecycle handle. It does not rewrite the source with string patches.
- `agent/DOORMAN.worker.js`: authenticated GitHub transport, context snapshots, tool receipts, and progress checkpoints.
- `agent/DEPLOYER.worker.js`: worker deployment preserving existing binding types and settings.
- `agent/runtime/PROGRESS.md` and `STATE.json`: last completed work, exact next step, blockers, and evidence.
- `agent/runtime/receipts/<action-id>.json`: durable mutation results. Retrying the same action returns its saved result. An interrupted mutation is reported as uncertain and must be reconciled against GitHub before a new mutation.

## Instructions and progress

Every model turn fetches the current `main/TODO.md` Venice section and an excerpt of `main/METHODOLOGY.md`, along with the persisted checkpoint and recent relevant main-branch workflow runs. Active tasks live in TODO; historical lane instructions do not revive reassigned work. Writes are restricted to `venice/*`; main is read-only and merging is disabled.

Venice returns a single JSON block tagged `venice-v6` with the exact current turn id, a factual summary, exact next step, and at most four tool actions. Only new `.assistant` messages after the submitted wake are eligible. Historical messages, user prompts, quoted file contents, partial JSON, and wrong turn ids are not executed.

Tools return structured results into the next model turn. Every completed turn checkpoints to GitHub. Empty/no-work turns sleep five minutes. Work with returned results continues after a short delay. Job reports use a `dedupe_key` such as `run-123456` to prevent a fresh chat from opening the same issue twice.

## Chat rollover

The runtime starts with a fresh chat, then rolls over before accumulated input reaches 100,000 characters or ten turns. It also rolls over after a six-minute response timeout or repeated unstructured responses. It waits for a different chat route and an empty assistant history before composing a continuation. The next prompt reloads GitHub progress and current instructions; it does not replay the old conversation.

Local in-flight state survives a browser reload using Tampermonkey storage. A same-origin browser lock selects one active tab. Pause prevents new model prompts and new tool actions. A pending submitted GitHub operation may already be running; its receipt records its result.

## Autonomous maintenance

Write corrected runtime source to `agent/BRIDGE6.js` on `venice/sec-options-pipelines`. The loader checks once a minute, waits for a completed-turn idle point, compiles the candidate before stopping the current runtime, then retains a local healthy fallback. It does not restart unchanged source. A failed candidate is skipped by blob SHA.

For worker updates, write `agent/DOORMAN.worker.js` on the assigned `venice/*` branch and request `deploy_worker`. The deployment uses an immutable commit SHA through the configured deployer, not a changing branch head. Read back the new context endpoint after deployment. Loader metadata updates can also be pushed to `agent/LOADER6.user.js` and picked up by Tampermonkey's update mechanism; most behavior belongs in the remotely loaded runtime.

The doorman key is stored only in the installed Tampermonkey script storage as `vrb6.key`, configured with its menu item. Do not write credentials to GitHub, prompts, checkpoints, or receipts. Previously published keys need equivalent rotation in the Worker and the local configuration.

The loop requires an open, signed-in browser and an available Venice service. Browser suspension, network outages, account limits, and provider UI changes can delay or stop execution. Checkpointing supports recovery; it cannot guarantee unlimited provider availability.


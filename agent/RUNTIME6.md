# Venice persistent web runtime v6

The browser is the model runner. Cloudflare is the GitHub tool transport. GitHub stores the authoritative instructions and durable task checkpoint.

## Active files

- `agent/LOADER6.user.js`: stable Tampermonkey loader, version 2. The installed script remains named **Venice Bridge Loader**. The standalone legacy **Venice Repo Bridge** entry stays disabled.
- `agent/BRIDGE6.js`: remotely updated browser runtime. The loader compiles it, runs it with explicit Tampermonkey functions, and receives a lifecycle handle. It does not rewrite the source with string patches.
- `agent/DOORMAN.worker.js`: authenticated GitHub transport, context snapshots, tool receipts, and progress checkpoints.
- `agent/DEPLOYER.worker.js`: worker deployment preserving existing binding types and settings.
- `agent/runtime/PROGRESS.md` and `STATE.json`: last completed work, exact next step, blockers, and evidence.
- `agent/runtime/PLAN.json`: goal, repo benefit, Gantt row, weighted subtasks, acceptance criteria, and computed verified percentage.
- `agent/runtime/NOTES.md`: persistent file map, decisions, failed approaches, proven fixes, and unresolved questions. Omitted notes preserve the last saved version.
- `agent/runtime/receipts/<action-id>.json`: durable mutation results. Retrying the same action returns its saved result. An interrupted mutation is reported as uncertain and must be reconciled against GitHub before a new mutation.

## Instructions and progress

Every model turn fetches the current `main/TODO.md` Venice section and an excerpt of `main/METHODOLOGY.md`, along with the persisted checkpoint and recent relevant main-branch workflow runs. Active tasks live in TODO; historical lane instructions do not revive reassigned work. Writes are restricted to `venice/*`; main is read-only and merging is disabled.

Venice returns a single JSON block tagged `venice-v6` with the exact current turn id, a factual summary, exact next step, and at most four tool actions. Only new `.assistant` messages after the submitted wake are eligible. Historical messages, user prompts, quoted file contents, partial JSON, and wrong turn ids are not executed.

Tools return structured results into the next model turn. Every completed turn checkpoints to GitHub. Empty/no-work turns sleep five minutes. Work with returned results continues after a short delay. Large text reads are paged with `next_offset`; read the next page rather than assuming omitted text is absent. A failed action stops the remaining batch so dependent actions cannot run on an unproven result.

For James' current failure-monitoring lane, use `report_failure(run_id)`. The Worker derives the failed and skipped steps and exact exception lines directly from GitHub. It posts one factual report (or one verified correction to an existing inferred report) and retains a permanent per-run receipt in `agent/runtime/reports/`. This prevents model guesses about job status or a truncated checkpoint from becoming the report. Current tool results take precedence over the model's previous summary.

## Chat rollover

The runtime starts with a fresh chat, then rolls over before accumulated input reaches 100,000 characters or ten turns. It also rolls over after a six-minute response timeout or repeated unstructured responses. It waits for a different chat route and an empty assistant history before composing a continuation. The next prompt reloads GitHub progress and current instructions; it does not replay the old conversation.

Local in-flight state survives a browser reload using Tampermonkey storage. A same-origin browser lock selects one active tab. Pause prevents new model prompts and new tool actions. A pending submitted GitHub operation may already be running; its receipt records its result. Both classic and agentic chat use assistant-only message roots. The classic send-button fallback explicitly excludes the bridge badge, so the status text cannot accidentally pause the loop.

## Autonomous maintenance

Write corrected runtime source to `agent/BRIDGE6.js` on `venice/sec-options-pipelines`. The loader checks once a minute, waits for a completed-turn idle point, compiles the candidate before stopping the current runtime, then retains a local healthy fallback. It does not restart unchanged source. A failed candidate is skipped by blob SHA.

For worker updates, write `agent/DOORMAN.worker.js` on the maintenance branch and request `deploy_worker`. The deployer accepts an immutable commit and verifies that its source exactly matches the fixed maintenance branch. It preserves all existing binding types, checks required bindings, and verifies their presence after deployment. It enables `global_fetch_strictly_public` so authenticated requests between the two Workers do not fail with Cloudflare error 1042. A newly pushed source may require a later retry while GitHub's public source mirrors propagate. Read back the context endpoint after deployment. Loader metadata updates can also be pushed to `agent/LOADER6.user.js` and picked up by Tampermonkey's update mechanism; most behavior belongs in the remotely loaded runtime.

## Proven live checks

- Exact authenticated GitHub write/read, including replay without duplicate writes: commit `a089ee8ac06ad75112451d56543736dcb6393b0b` on the maintenance branch.
- Runner dispatch, public source download and artifact upload: run [42375131645](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42375131645), artifact `venice-bridge-download-proof`.
- Worker self-deployment through the fixed-target deployer, preserving existing bindings: commit `3254934f8d03748c3b14475f641b76f4d0ebd74d`.
- Model-generated reporting and checkpoints: issue [220](https://github.com/SRoyaltyy/checklist-engine/issues/220), followed by verified correction when the job-log path became available.
- Live chat rollover and state restoration were exercised; the browser resumes from GitHub's checkpoint and notes.

The doorman key is stored only in the installed Tampermonkey script storage as `vrb6.key`, configured with its menu item. Do not write credentials to GitHub, prompts, checkpoints, or receipts. Previously published keys need equivalent rotation in the Worker and the local configuration.

The loop requires an open, signed-in browser and an available Venice service. Browser suspension, network outages, account limits, and provider UI changes can delay or stop execution. Checkpointing supports recovery; it cannot guarantee unlimited provider availability.


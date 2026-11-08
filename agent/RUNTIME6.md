# Venice persistent web runtime v6

The browser is the model runner. Cloudflare is the GitHub tool transport. GitHub stores the authoritative instructions and durable task checkpoint.

## Active files

- `agent/LOADER6.user.js`: stable Tampermonkey loader, version 2.1.0. The installed script remains named **Venice Bridge Loader**. The standalone legacy **Venice Repo Bridge** entry stays disabled.
- `agent/BRIDGE6.js`: published browser runtime, version 6.2.3. The loader compiles it, runs it with explicit Tampermonkey functions, and receives a lifecycle handle. It does not rewrite the source with string patches.
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

Write corrected runtime source to `agent/BRIDGE6.js` on `venice/sec-options-pipelines`. The loader checks once a minute, waits for a completed-turn idle point, compiles the candidate before stopping the current runtime, then retains a local healthy fallback. It does not restart unchanged source. The runtime retries temporary ownership contention after reload or code updates, and waits before fetching context when the composer is unavailable or contains a draft. A failed candidate is skipped by blob SHA. New runtimes become the healthy fallback only after completing a checkpoint. The loader tolerates background timer delays and a browser sleep/resume gap without blacklisting healthy source.

For worker updates, write `agent/DOORMAN.worker.js` on the maintenance branch and request `deploy_worker`. The deployer accepts an immutable commit and verifies that its source exactly matches the fixed maintenance branch. It preserves all existing binding types, checks required bindings, and verifies their presence after deployment. It enables `global_fetch_strictly_public` so authenticated requests between the two Workers do not fail with Cloudflare error 1042. A newly pushed source may require a later retry while GitHub's public source mirrors propagate. Read back the context endpoint after deployment. Loader metadata updates can also be pushed to `agent/LOADER6.user.js` and picked up by Tampermonkey's update mechanism; most behavior belongs in the remotely loaded runtime.

## Proven live checks

- Exact authenticated GitHub write/read, including replay without duplicate writes: commit `a089ee8ac06ad75112451d56543736dcb6393b0b` on the maintenance branch.
- Runner dispatch, public source download and artifact upload: run [42375131645](https://github.com/SRoyaltyy/checklist-engine/actions/runs/42375131645), artifact `venice-bridge-download-proof`.
- Worker self-deployment through the fixed-target deployer, preserving existing bindings: commit `3254934f8d03748c3b14475f641b76f4d0ebd74d`.
- Model-generated reporting and checkpoints: issues [220](https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739) and [221](https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770), followed by exact GitHub-log corrections and verified persistent deduplication.
- Live classic-chat rollover and state restoration were exercised on runtime 6.2.0; Venice resumed its saved task, wrote the corrected progress file at commit `8f1cbd8c36321a47dee6192d8e8ed47440fa0a56`, read the verified result, then checkpointed the task as complete. Agentic mode has automated DOM-adapter coverage and was exercised earlier; this final acceptance pass used Classic.
- 49 automated checks pass: 17 transport/checkpoint/reporting, 10 Agentic browser adapter, 10 Classic browser adapter, 3 deployer, 6 loader/update/suspension checks, and 3 ownership/recovery checks.

## Daily use

Open https://venice.ai/chat/classic in the existing signed-in Chrome profile with **Venice Bridge Loader** enabled in Tampermonkey. Leave **Venice Repo Bridge** disabled. The existing local key and saved checkpoint are reused; no wake prompt or manual context paste is required. The badge should show **V6 ON**. Clicking that badge pauses/resumes; right-clicking requests a fresh chat. The loader's **testing** label becomes **healthy** after a completed checkpoint. A newly opened page can wait until the saved next wake is due.

The loop schedules the next idle check five minutes after a completed turn. Browser timer delays and model response time add to this. The observed background checkpoint intervals were approximately eight to nine minutes. The computer must remain awake, online, and signed in to Venice.

## Operating status

Verified at 2026-11-08 01:34 Hong Kong time: installed loader 2.1.0 and **healthy runtime 6.2.2**, loop ON in Classic Chat. Automatic source updating and ownership recovery are active. Unassisted monitoring checkpoints completed at 01:24:27 and 01:33:08 Hong Kong time, turns `mw6o9s60-bgoldpz7` and `mw6oirhp-w4ehs68d`. The earlier watch ended seconds before the first of these completed; that earlier pending result is superseded. Chrome's **Always keep these sites active** list now contains `venice.ai`, verified in the Settings UI.

Fresh-page startup passed: opening the Classic landing page reconnected with the saved enabled state, sent a wake without manual input, read runs(main), and checkpointed at 01:38:59 Hong Kong time (turn mw6osssp-vnm3z52x). Proactive rollover then continued in another chat and saved the inspected run results at 01:39:45 (turn mw6ou2z5-sa57fr5f). The startup, idle-wake, source-refresh and rollover acceptance checks have all been exercised live. Version 6.2.3 was observed loaded and ON; its new progress-evidence handling has automated coverage. Later live checkpoints on November 8 now record the completed monitoring work with 100% verified plan progress. It retains actual run/job links from tool result lists, so a completed read can provide progress evidence.

## Demonstrated work quality

Venice has demonstrated narrow failure monitoring, exact file edits with readback, handling returned results, checkpointing and fresh-chat continuation. It has not completed a substantial code feature with passing feature tests and an independently reviewed PR in this commissioning run. Runner downloads demonstrate transport capability, not coding quality.

The model previously inferred an incorrect diagnosis, misread skipped-step status, and treated truncated log text as missing. The verified report_failure path now derives the exact facts and persistently deduplicates the report. This improves the monitoring lane without establishing general autonomous engineering quality. Server progress counts recognized evidence; it does not independently judge every task's acceptance criterion or code correctness. Repository writes use venice/* branches and pull requests; main writes and merges remain disabled.

The current loader stores the doorman key locally in Tampermonkey as `vrb6.key`, configured with its menu item. Do not write credentials to GitHub, prompts, checkpoints, or receipts. Previously published keys need equivalent rotation in the Worker and the local configuration.

The loop requires an open, signed-in browser and an available Venice service. Browser suspension, network outages, account limits, and provider UI changes can delay or stop execution. Checkpointing supports recovery; it cannot guarantee unlimited provider availability.

## November 8 operating check and cleanup

At 23:08 HKT, the latest saved turn mw7yv47y-8vxkhl7y reported no new unreported SEC/OI failure and closed the monitoring check with 100% plan progress. This percentage applies to that monitoring plan, not the entire checklist-engine project. The loop has continued saving checkpoints into the following day. A real new failure, run 42399694729, was reported at https://github.com/SRoyaltyy/checklist-engine/issues/223 with the exact failed/skipped steps and exception, about four minutes after the logged failure.

Two legacy branch-only helpers, .github/workflows/nai-verdict.yml and nai-verdict2.yml, were found triggering on every push and repeatedly collecting the same November 2 run 41413529249. Both are now manual-only and require an explicit run_id. Verified commits: c065ed9fe815bde161f16b4335109f11370f9b68 and 82d02e1c2e75994d0a474c3996020e42f283320f. This removes unnecessary runner activity from routine checkpoints. The assigned SEC/options production pipelines and main were not modified.

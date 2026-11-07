# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section and METHODOLOGY.md every turn. Current lane (TODO.md@c7c31b02, Venice section): report failures only, then stop. Do NOT own or rewrite SEC/options download pipelines, do not push collectors, do not burn scrape quota on bulk downloads. Calendar work #96 stays parked. #96/#177/#163 are other lanes.

## File map
Maintenance branch: venice/sec-options-pipelines. agent/BRIDGE6.js is remotely loaded by agent/LOADER6.user.js. agent/DOORMAN.worker.js is the GitHub transport; agent/DEPLOYER.worker.js is its fixed-target deployer. State, plan, progress, notes and receipts live in agent/runtime/. My checkpoint file is agent/PROGRESS.md (last commit ba179d2306dbc448f85c9caa6ae07554e07cf192, blob a83aa26fe6c41bc7172f03a90812d97064c68ae4).

## Proven work
Exact GitHub read/write proof: a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof: https://github.com/SRoyaltyy/checklist-engine/actions/runs/42375131645. Worker self-update preserves existing bindings.

## Failure reporting — canonical facts
Run 42284432095, workflow nai-occ-oi-daily, sha e85547a, job 128121492870. report_failure output (authoritative, deduped) is comment https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739: failed_steps=['Run python scripts/nai/occ_oi_daily.py'], skipped_steps=['Run python scripts/nai/oi_probe.py'], error_lines=['Traceback (most recent call last):','ValueError: invalid literal for int() with base 10: \'\'','##[error]Process completed with exit code 1.'], log_unavailable=null.
Run 42156926867, nai-sec-form345, sha 8ec34d48, job 127693199421, failing step 'Run python scripts/nai/sec_datasets.py form345', annotation exit code 1 → issue #221. Traceback not captured for this one.

## Reported run IDs — never re-report
42284432095, 42156926867. Also deliberately unreported as duplicates/superseded: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, pre-e85547a or covered by #220) and 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch on superseded shas d5ab097/b0a563b).

## Approaches that failed / lessons
Never infer a traceback from source code. Never assume omitted text in a checkpoint or a truncated UI step means the log is absent — the GitHub API path used by report_failure can retrieve it. Prefer report_failure(run_id) over freeform issue text: it derives failed/skipped steps and exact error lines and dedupes persistently. Classic sender once clicked its own badge; fixed in 6.1.2. Cloudflare error 1042 fixed by global_fetch_strictly_public. Newly pushed worker source may need a retry while GitHub public source mirrors propagate.

## Open question
Job page step list renders an 'Run python scripts/nai/oi_probe.py' step (truncated) while report_failure records it as skipped. Canonical record defers to report_failure; flagging only, not investigating — out of lane.

## Next
Rewrite agent/PROGRESS.md to cite the canonical comment and drop superseded wording; then passive monitoring with actions=[] until a new nai-* failure appears outside the do-not-re-report set.
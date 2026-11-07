# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section and METHODOLOGY.md every turn. Current lane (TODO.md@c7c31b02): report failures only, then stop. Do NOT own or rewrite SEC/options download pipelines, no collector pushes, no bulk scraping. Calendar #96 parked. #96/#177/#163 are other lanes.

## File map
Maintenance branch venice/sec-options-pipelines. agent/BRIDGE6.js remotely loaded by agent/LOADER6.user.js; agent/DOORMAN.worker.js is GitHub transport; agent/DEPLOYER.worker.js fixed-target deployer. Runtime state in agent/runtime/. My checkpoint is agent/PROGRESS.md (last commit ba179d2306dbc448f85c9caa6ae07554e07cf192, blob a83aa26f).

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings.

## Failure reporting — canonical facts
Run 42284432095 / nai-occ-oi-daily / sha e85547a / job 128121492870. report_failure output (authoritative, deduped) = https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739 : failed_steps=['Run python scripts/nai/occ_oi_daily.py'], skipped_steps=['Run python scripts/nai/oi_probe.py'], error_lines=['Traceback (most recent call last):','ValueError: invalid literal for int() with base 10: \'\'','##[error]Process completed with exit code 1.'], log_unavailable=null. Supersedes both the body's inferred unguarded-DELO diagnosis and the earlier 'oi_probe ran / logs truncated' correction.
Run 42156926867 / nai-sec-form345 / sha 8ec34d48 / job 127693199421 / failing step 'Run python scripts/nai/sec_datasets.py form345' → https://github.com/SRoyaltyy/checklist-engine/issues/221 . Traceback not captured for this one.

## Reported run IDs — never re-report
42284432095, 42156926867. Deliberately unreported duplicates/superseded: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage) and 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch, superseded shas).

## Lessons
Never infer a traceback from source code. Never assume a truncated UI step means the log is absent — the API path used by report_failure retrieves it. Prefer report_failure(run_id) over freeform issue text. Cloudflare 1042 fixed by global_fetch_strictly_public; freshly pushed worker source may need one retry while mirrors propagate.

## Open question (flagged, not investigating)
Job page renders an oi_probe step (truncated) while report_failure lists it as skipped. Canonical record defers to report_failure. Out of lane.

## Next
Verify the PROGRESS.md rewrite commit, then passive monitoring with actions=[] until a new nai-* failure appears outside the do-not-re-report set.
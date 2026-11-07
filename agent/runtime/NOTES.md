# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section + METHODOLOGY.md each turn. Current lane (TODO.md@c7c31b02e530a35d9944c705d19422d606956809): thin chatbot poke — report a failed nai-sec-* / nai-occ-oi-daily run once with run ID + error, then stop; GPT owns fixes. Do NOT own/rewrite SEC/options download pipelines, no collector pushes, no bulk scraping. Calendar #96 parked. #96/#177/#163 are other lanes. Ignore venice/calendar-announce-ledger after dca969a.

## File map
Maintenance branch venice/sec-options-pipelines. agent/BRIDGE6.js remotely loaded by agent/LOADER6.user.js; agent/DOORMAN.worker.js = GitHub transport; agent/DEPLOYER.worker.js = fixed-target deployer; runtime state in agent/runtime/. Checkpoint agent/PROGRESS.md at commit 8f1cbd8c36321a47dee6192d8e8ed47440fa0a56, blob 4bbcb076f4aa7d07dbd93deacc723de168b757f7 (previous ba179d23 / blob a83aa26f).

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings.

## Failure reporting — canonical facts
Run 42284432095 / nai-occ-oi-daily / sha e85547a / job 128121492870. Authoritative deduped record: https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739 — failed_steps=['Run python scripts/nai/occ_oi_daily.py'], skipped_steps=['Run python scripts/nai/oi_probe.py'], error_lines=['Traceback (most recent call last):','ValueError: invalid literal for int() with base 10: \'\'','##[error]Process completed with exit code 1.'], log_unavailable=null. Supersedes the issue body's inferred unguarded-DELO diagnosis and earlier comment 6710061417. The unguarded DELO call at scripts/nai/occ_oi_daily.py line 8 remains an unverified inference and must not be cited as cause.
Run 42156926867 / nai-sec-form345 / sha 8ec34d48 / job 127693199421: failed step 'Run python scripts/nai/sec_datasets.py form345', no skipped steps. Exact log: RuntimeError: GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403: Forbidden; urllib.error.HTTPError: HTTP Error 403: Forbidden; RuntimeError: HTTP 403. Canonical verified correction: https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770. report_failure returned verified:true; a repeat call returned replayed:true with no duplicate.

## Reported run IDs — never re-report
42284432095, 42156926867. Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch on superseded shas d5ab097/b0a563b).

## Latest green runs (verified this turn, runs(main) snapshot)
42391969592 world-v2-code-ci sha 2ba3ebd success; 42370489444 world-v2-code-ci sha 230ca55 success; 42344942142 nai-daily-forward sha e85547a success; 42332789888 nai-sec-form13f sha e85547a success. Only warnings are Node20-deprecation / ubuntu-latest notices — not failures.

## Lessons
Never infer a traceback from source code. Never assume a truncated UI step means the log is absent — the API path used by report_failure retrieves it. Prefer report_failure(run_id) over freeform issue text. A failed probe differs from a skipped probe. Cloudflare 1042 fixed by global_fetch_strictly_public; freshly pushed worker source may need one retry while mirrors propagate.

## Interpretation
A step can render in the job page while its API conclusion is skipped. Rendering the step name is not evidence it executed; the API step conclusions plus report_failure settle it. Every step showing 'truncated due to its large size' in the UI does not mean the log is unavailable to the API path.

## Schedule note
nai-occ-oi-daily fires ~19:59 UTC daily; at 2026-11-07T17:39Z the next occurrence is still ahead, so no new occ run is expected yet. nai-sec-form13f fires ~03:10 UTC; nai-daily-forward ~05:58 UTC — both already green today.

## State
Lane tasks t1–t7 done. Passive monitoring until a nai-* failure appears outside the do-not-re-report set.
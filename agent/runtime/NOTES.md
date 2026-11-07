# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section + METHODOLOGY.md each turn. Current lane (TODO.md@c7c31b02e530a35d9944c705d19422d606956809): thin chatbot poke — report a failed nai-sec-* / nai-occ-oi-daily run once with run ID + error, then stop; GPT owns fixes. Do NOT own/rewrite SEC/options download pipelines, no collector pushes, no bulk scraping. Calendar #96 parked; #96/#177/#163 are other lanes. Ignore venice/calendar-announce-ledger after dca969a.

## File map
Maintenance branch venice/sec-options-pipelines. agent/BRIDGE6.js remotely loaded by agent/LOADER6.user.js; agent/DOORMAN.worker.js = GitHub transport; agent/DEPLOYER.worker.js = fixed-target deployer; runtime state in agent/runtime/. Checkpoint agent/PROGRESS.md now at commit aa3fab0cdd1dfe27b8acd27a934be49230db700c (blob 431e9399e614e976fb11d4d359a65b12773a0cbf); previous 8f1cbd8c (blob 4bbcb076), ba179d23.

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings.

## Failure reporting — canonical facts
Run 42399694729 / nai-occ-oi-daily / sha 2ba3ebdf977df51e7ab7e1993fdfee27faf19939 / job 128484582301 / 16s / triggered via schedule at 18:07Z. Canonical record: https://github.com/SRoyaltyy/checklist-engine/issues/223 — failed_steps=['Run python scripts/nai/occ_oi_daily.py'], skipped_steps=['Run python scripts/nai/oi_probe.py'], error_lines=['Traceback (most recent call last):',"ValueError: invalid literal for int() with base 10: ''",'##[error]Process completed with exit code 1.']. report_failure returned verified:true. Same ValueError signature as #220 but on the current main head 2ba3ebd, so #220's fix has not landed.
Run 42284432095 / nai-occ-oi-daily / sha e85547a / job 128121492870. Authoritative deduped record: https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739 — same failed/skipped steps and ValueError. Supersedes the issue body's inferred unguarded-DELO diagnosis and comment 6710061417. DELO remains unverified inference; never cite it as cause. Job annotation is only 'Process completed with exit code 1.' at step 5:12.
Run 42156926867 / nai-sec-form345 / sha 8ec34d48 / job 127693199421: failed step 'Run python scripts/nai/sec_datasets.py form345'; log: RuntimeError: GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403: Forbidden. Canonical correction: https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770 (verified:true).

## Reported run IDs — never re-report
42284432095, 42156926867, 42399694729. Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch on superseded shas d5ab097/b0a563b).

## Verified green snapshot (runs(main), 2026-11-07T18:12Z)
Top of list: 42399694729 nai-occ-oi-daily failure sha 2ba3ebd (reported). 42391969592 world-v2-code-ci sha 2ba3ebd success; 42370489444 world-v2-code-ci sha 230ca55 success; 42344942142 nai-daily-forward sha e85547a success; 42332789888 nai-sec-form13f sha e85547a success; 42261199680 / 42252851317 / 42252169840 / 42214284659 world-v2-code-ci all success; 42176587992 / 41982771257 / 41785171922 / 41592147370 / 41413030480 nai-daily-forward all success; 41413026299 nai-occ-oi-daily success sha d5ab097. 41227556402 outside-event-calendar cancelled (not reportable). Node20-deprecation and ubuntu-latest→Ubuntu26 notices are not failures.

## Lessons
Never infer a traceback from source code. Never assume a truncated UI step means the log is absent — the API path used by report_failure retrieves it. Prefer report_failure(run_id) over freeform issue text. A failed probe differs from a skipped probe. Cloudflare 1042 fixed by global_fetch_strictly_public; freshly pushed worker source may need one retry while mirrors propagate.

## Interpretation
A step can render in the job page while its API conclusion is skipped. Rendering a step name is not evidence it executed; API step conclusions plus report_failure settle it. A cancelled run is neither a failure nor reportable in this lane.

## Schedule note
nai-occ-oi-daily also fires on push/extra schedule — 42399694729 appeared at 18:07Z, well before the ~19:59 UTC daily slot, so check runs(main) every wake rather than assuming a quiet window. nai-sec-form13f ~03:10 UTC and nai-daily-forward ~05:58 UTC green today (sha e85547a).

## State
t1–t11 done. Lane idle: no unreported failure. Only open item is GPT fixing occ_oi_daily.py (issues #220/#223) and sec_datasets.py form345 (issue #221).
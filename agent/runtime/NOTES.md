# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section + METHODOLOGY.md each turn. Current lane (TODO.md@c7c31b02e530a35d9944c705d19422d606956809): thin chatbot poke — report a failed nai-sec-* / nai-occ-oi-daily run once with run ID + error, then stop; GPT owns fixes. Do NOT own/rewrite SEC/options download pipelines, no collector pushes, no bulk scraping. Calendar #96 parked; #96/#177/#163 are other lanes. Ignore venice/calendar-announce-ledger after dca969a.

## File map
Maintenance branch venice/sec-options-pipelines. agent/BRIDGE6.js remotely loaded by agent/LOADER6.user.js; agent/DOORMAN.worker.js = GitHub transport; agent/DEPLOYER.worker.js = fixed-target deployer; runtime state in agent/runtime/. Checkpoint agent/PROGRESS.md at commit 8f1cbd8c36321a47dee6192d8e8ed47440fa0a56, blob 4bbcb076f4aa7d07dbd93deacc723de168b757f7 (previous ba179d23 / blob a83aa26f).

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings.

## Failure reporting — canonical facts
Run 42284432095 / nai-occ-oi-daily / sha e85547a / job 128121492870. Authoritative deduped record: https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739 — failed_steps=['Run python scripts/nai/occ_oi_daily.py'], skipped_steps=['Run python scripts/nai/oi_probe.py'], error_lines=['Traceback (most recent call last):','ValueError: invalid literal for int() with base 10: \'\'','##[error]Process completed with exit code 1.']. Supersedes the issue body's inferred unguarded-DELO diagnosis and earlier comment 6710061417. The DELO line remains an unverified inference; never cite it as cause. Job page annotation is only 'Process completed with exit code 1.' at step 5:12.
Run 42156926867 / nai-sec-form345 / sha 8ec34d48 / job 127693199421: failed step 'Run python scripts/nai/sec_datasets.py form345', no skipped steps. Exact log: RuntimeError: GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403: Forbidden; urllib.error.HTTPError: HTTP Error 403: Forbidden; RuntimeError: HTTP 403. Canonical verified correction: https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770. report_failure returned verified:true; repeat call replayed:true, no duplicate.

## Reported run IDs — never re-report
42284432095, 42156926867. Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch on superseded shas d5ab097/b0a563b).

## Verified green snapshot (runs(main), 2026-11-07T17:57Z)
42391969592 world-v2-code-ci sha 2ba3ebd success 7m58s (merge #218 gpt/sec-bulk-retained-v2), artifacts canonical-binary-definition-plan-v1 6.72MB + fred-v2-source 1.86MB; 42370489444 world-v2-code-ci sha 230ca55 success 8m16s (merge #210 kimi/sec-options-defs); 42344942142 nai-daily-forward sha e85547a success 24s; 42332789888 nai-sec-form13f sha e85547a success 11m53s. Only Node20-deprecation and ubuntu-latest→Ubuntu26 notices — not failures.

## Lessons
Never infer a traceback from source code. Never assume a truncated UI step means the log is absent — the API path used by report_failure retrieves it. Prefer report_failure(run_id) over freeform issue text. A failed probe differs from a skipped probe. Cloudflare 1042 fixed by global_fetch_strictly_public; freshly pushed worker source may need one retry while mirrors propagate.

## Interpretation
A step can render in the job page while its API conclusion is skipped. Rendering the step name is not evidence it executed; the API step conclusions plus report_failure settle it. A cancelled run (e.g. outside-event-calendar 41227556402) is neither a failure nor reportable in this lane.

## Schedule note
nai-occ-oi-daily fires ~19:59 UTC daily; at 2026-11-07T18:03Z the next occurrence is ~1h56m ahead. nai-sec-form13f ~03:10 UTC and nai-daily-forward ~05:58 UTC already green today (sha e85547a).

## State
Lane tasks t1–t8 done. Passive monitoring only; no writes until a nai-* failure appears outside the do-not-re-report set.
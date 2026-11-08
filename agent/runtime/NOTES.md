# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section + METHODOLOGY.md each turn. Current lane (TODO.md@c7c31b02e530a35d9944c705d19422d606956809): thin chatbot poke — report a failed nai-sec-* / nai-occ-oi-daily run once with run ID + error, then stop; GPT owns fixes. Do NOT own/rewrite SEC/options download pipelines, no collector pushes, no bulk scraping. Calendar #96 parked; #96/#177/#163 other lanes. Ignore venice/calendar-announce-ledger after dca969a.

## File map
Branch venice/sec-options-pipelines. agent/BRIDGE6.js loaded by agent/LOADER6.user.js; agent/DOORMAN.worker.js = GitHub transport; agent/DEPLOYER.worker.js = deployer; runtime state agent/runtime/. agent/PROGRESS.md current blob 431e9399e614e976fb11d4d359a65b12773a0cbf (30 lines) per 2026-11-08T14:42Z re-read; earlier commits 8f1cbd8c, ba179d23, and aa3fab0c (whose sha was rejected as stale). LESSON: expected_sha must be the sha from the most recent read of that exact path; a stale sha fails closed — re-read, do not blind-retry.

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings.

## Failure reporting — canonical facts
Run 42399694729 / nai-occ-oi-daily / sha 2ba3ebd / job 128484582301 / 2026-11-07T18:07Z. Canonical issue #223 (re-scraped this turn, verified:true): failed step 'Run python scripts/nai/occ_oi_daily.py'; listed skipped step 'Run python scripts/nai/oi_probe.py'; error lines 'Traceback (most recent call last):' / "ValueError: invalid literal for int() with base 10: ''" / '##[error]Process completed with exit code 1.'. Same ValueError signature as #220 on a newer head, so the #220 fix has not landed.
Run 42284432095 / sha e85547a / job 128121492870: canonical https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739 — same failed/skipped step names and same ValueError lines. Supersedes the issue body's inferred unguarded-DELO diagnosis and comment 6710061417. DELO stays unverified inference; never cite as cause. #220 also contains a self-contradiction about whether oi_probe ran; report_failure's derived field is authoritative for the lane.
Run 42156926867 / nai-sec-form345 / sha 8ec34d48 / job 127693199421: failed step 'Run python scripts/nai/sec_datasets.py form345', skipped none; error lines RuntimeError GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403 Forbidden; urllib.error.HTTPError 403; RuntimeError HTTP 403; '##[error]Process completed with exit code 1.'. Canonical https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770 (verified:true).

## Reported run IDs — never re-report
42284432095, 42156926867, 42399694729. Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch, superseded shas d5ab097/b0a563b).

## runs(main) snapshot 2026-11-08T14:41Z (14 runs)
42434336421 nai-sec-bulk success sha 2ba3ebd 2026-11-08T01:27Z (new, healthy). 42399694729 occ failure (reported). 42332789888 nai-sec-form13f success e85547a; 42284432095 occ failure (reported); 42156926867 form345 failure (reported); 42106074154 occ failure (covered); 41906860199 / 41710121137 occ failures (covered); 41413535355 / 41413529249 / 41413017909 / 41413013359 Nov-2 failures (covered); 41413026299 occ success d5ab097. No world-v2-code-ci run newer than 42391969592 in this list.

## Open observation (not a failure, nothing filed)
Expected scheduled slots absent from runs(main): Nov 7 ~19:59Z nai-occ-oi-daily, Nov 8 ~03:10Z nai-sec-form13f, Nov 8 ~05:58Z nai-daily-forward. Possible schedule stall or disabled workflows. A missing run is not a failed run, so this lane does not report it through report_failure; re-check each wake and escalate to James/GPT only if the gap persists.

## Lessons
Never infer a traceback from source code. Never assume a truncated UI step means the log is absent — the API path in report_failure retrieves it. Prefer report_failure(run_id) over freeform issue text. A failed probe differs from a skipped probe. Cloudflare 1042 fixed by global_fetch_strictly_public.

## Interpretation
A step can render in the job page while its API conclusion is skipped; API conclusions plus report_failure settle it. A cancelled run is neither a failure nor reportable in this lane.

## State
t1–t11 done. t12 in progress: fresh sha obtained, checkpoint write re-issued, awaiting commit sha. No unreported failure exists. Only open external items: GPT fixing occ_oi_daily.py (#220/#223) and sec_datasets.py form345 (#221).
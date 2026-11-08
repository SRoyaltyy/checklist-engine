# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section + METHODOLOGY.md each turn. Lane (TODO.md@c7c31b02e530a35d9944c705d19422d606956809): thin chatbot poke — report a failed nai-sec-* / nai-occ-oi-daily run once with run ID + error, then stop; GPT owns fixes. No pipeline ownership, no collector pushes, no bulk scraping. Calendar #96 parked; #96/#177/#163 other lanes. Ignore venice/calendar-announce-ledger after dca969a.

## File map
Branch venice/sec-options-pipelines. agent/BRIDGE6.js + agent/LOADER6.user.js = browser runtime/loader; agent/DOORMAN.worker.js = GitHub transport (deploy via deploy_worker); agent/DEPLOYER.worker.js; runtime state agent/runtime/. agent/PROGRESS.md @ commit 8a3ed5d5cad3b052f84872bd3d82e3699e161fcd, blob 0fa61634a892f6b2a433ace58ecd6a0af896ff3d (verified 2026-11-08T14:52Z; 34 lines). LESSON: expected_sha must come from the most recent read of that exact path; stale sha fails closed — re-read, never blind-retry.

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings.

## Failure reports — canonical facts
42399694729 / nai-occ-oi-daily #6 / sha 2ba3ebd / job 128484582301 / 2026-11-07T18:07Z -> issue #223 (verified:true). Failed step 'Run python scripts/nai/occ_oi_daily.py'; error lines 'Traceback (most recent call last):' / "ValueError: invalid literal for int() with base 10: ''" / '##[error]Process completed with exit code 1.'; 1 error annotation (step:5:12); 19s (16s in job). Same ValueError signature as #220 on a newer head => #220 fix has not landed.
42284432095 / sha e85547a / job 128121492870 -> canonical https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739 (re-verified from scraped page this turn). Same failed step and same ValueError lines. Supersedes the body's unguarded-DELO inference and comment 6710061417. DELO stays unverified inference; never cite as cause. The canonical comment lists oi_probe as 'skipped' but 6710061417 proves it ran first; report_failure's derived step list is the authority.
42156926867 / nai-sec-form345 / sha 8ec34d48 / job 127693199421 -> canonical https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770 (re-verified from scraped page this turn). Failed step 'Run python scripts/nai/sec_datasets.py form345', skipped none; error lines RuntimeError GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403 Forbidden / urllib.error.HTTPError 403 / RuntimeError HTTP 403 / '##[error]Process completed with exit code 1.'

## Reported run IDs — never re-report
42284432095, 42156926867, 42399694729. Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch, superseded shas d5ab097/b0a563b). 41227556402 cancelled — neither failure nor reportable.

## runs(main) snapshot — identical at 14:41Z / 14:44Z / 14:50Z / 14:56Z / 15:05Z / 15:17Z / 15:26Z (30 entries)
Newest: 42434336421 nai-sec-bulk #51 sha 2ba3ebd SUCCESS 30m56s, jobs 128589843164 (19s) + 128589913741 (30m32s), artifact sec-bulk-receipt-42434336421 111 KB sha256:4d5af7ea….
Other successes: 42391969592 world-v2-code-ci #121 (merge PR #218 gpt/sec-bulk-retained-v2, sha 2ba3ebd, 7m58s; jobs 128461239926 verify 1m51s / 128461730485 sec-source-evidence / 128461729593 fred-source 6m1s; artifacts canonical-binary-definition-plan-v1 6.72 MB sha256:463d35ed… + fred-v2-source 1.86 MB sha256:2eb5b072…; annotations boilerplate only — Node20 deprecation + ubuntu-latest->26 notice, plus the known 'Uh oh! error while loading' UI banner); 42370489444 #120 (merge PR #210 kimi/sec-options-defs, sha 230ca55, 8m16s; jobs 128397429174 verify 1m50s / 128397841287 sec-source-evidence 0s / 128397840159 fred-source 6m23s; same two artifacts, digests 40d815f2… / 39b5d8c7…); 42344942142 nai-daily-forward #6 sha e85547a 24s; 42332789888 nai-sec-form13f sha e85547a; 42261199680 / 42252851317 / 42252169840 / 42214284659 / 41575832670 / 41574644199 world-v2-code-ci; 42176587992 / 41982771257 / 41785171922 / 41592147370 / 41413030480 nai-daily-forward; 41413026299 occ sha d5ab097; 41227563332 outside-event-calendar.

## Open observation (not a failure, nothing filed)
Scheduled slots absent from runs(main): Nov 7 ~19:59Z nai-occ-oi-daily, Nov 8 ~03:10Z nai-sec-form13f, Nov 8 ~05:58Z nai-daily-forward. Newest form13f is still 42332789888 (Nov 7 03:10Z) and newest nai-daily-forward 42344942142 (Nov 7 05:58Z). A missing run is not a failed run, so report_failure does not apply; escalate to James/GPT only if the gap persists through Nov 9.

## Lessons
Never infer a traceback from source. Never trust a truncated UI step to mean the log is missing — report_failure's API path retrieves it. Prefer report_failure(run_id) over freeform issue text. A failed probe differs from a skipped probe. Cloudflare 1042 fixed by global_fetch_strictly_public. A run-page 'Uh oh! error while loading' banner is a GitHub UI artifact, not evidence about the job. A cancelled run is neither a failure nor reportable. Do not rewrite PROGRESS.md on a no-change wake — re-read the blob sha first and skip the write if nothing changed.

## State
t1–t19 done. PROGRESS.md verified current (blob 0fa61634). No unreported failure as of 15:26Z. External items open: GPT fixing occ_oi_daily.py (#220/#223) and sec_datasets.py form345 (#221); plus the un-filed schedule-gap observation.
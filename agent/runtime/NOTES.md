# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section + METHODOLOGY.md each turn. Current lane (TODO.md@c7c31b02e530a35d9944c705d19422d606956809): thin chatbot poke — report a failed nai-sec-* / nai-occ-oi-daily run once with run ID + error, then stop; GPT owns fixes. Do NOT own/rewrite SEC/options download pipelines, no collector pushes, no bulk scraping. Calendar #96 parked; #96/#177/#163 other lanes. Ignore venice/calendar-announce-ledger after dca969a.

## File map
Branch venice/sec-options-pipelines. agent/BRIDGE6.js loaded by agent/LOADER6.user.js; agent/DOORMAN.worker.js = GitHub transport; agent/DEPLOYER.worker.js = deployer; runtime state agent/runtime/. agent/PROGRESS.md current commit 8a3ed5d5cad3b052f84872bd3d82e3699e161fcd, blob 0fa61634a892f6b2a433ace58ecd6a0af896ff3d (Nov 8 checkpoint). Prior: blob 431e9399, commits 8f1cbd8c, ba179d23, aa3fab0c (rejected as stale). LESSON: expected_sha must come from the most recent read of that exact path; a stale sha fails closed — re-read, do not blind-retry.

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings.

## Failure reporting — canonical facts
Run 42399694729 / nai-occ-oi-daily #6 / sha 2ba3ebd / job 128484582301 / 2026-11-07T18:07Z. Issue #223 (verified:true): failed step 'Run python scripts/nai/occ_oi_daily.py'; skipped step 'Run python scripts/nai/oi_probe.py'; error lines 'Traceback (most recent call last):' / "ValueError: invalid literal for int() with base 10: ''" / '##[error]Process completed with exit code 1.'; 1 error annotation, 19s. Same ValueError signature as #220 on a newer head, so the #220 fix has not landed.
Run 42284432095 / sha e85547a / job 128121492870: canonical https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739 — same failed/skipped step names and same ValueError lines. Supersedes the issue body's inferred unguarded-DELO diagnosis and comment 6710061417. DELO stays unverified inference; never cite as cause.
Run 42156926867 / nai-sec-form345 / sha 8ec34d48 / job 127693199421: failed step 'Run python scripts/nai/sec_datasets.py form345', skipped none; error lines RuntimeError GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403 Forbidden; urllib.error.HTTPError 403; RuntimeError HTTP 403; '##[error]Process completed with exit code 1.'. Canonical https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770 (verified:true).

## Reported run IDs — never re-report
42284432095, 42156926867, 42399694729. Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch, superseded shas d5ab097/b0a563b).

## runs(main) snapshot — 14:44Z and 14:50Z identical (30 entries)
Newest: 42434336421 nai-sec-bulk #51 sha 2ba3ebd SUCCESS, 30m56s, verify job 128589843164 19s + run job 128589913741 30m32s, artifact sec-bulk-receipt-42434336421 111 KB sha256:4d5af7ea...; annotations are Node20-deprecation + ubuntu-latest->Ubuntu26 warnings only, plus the transient 'error while loading' UI banner that does not affect the success conclusion.
Other successes: 42391969592 world-v2-code-ci #121 (merge PR #218 gpt/sec-bulk-retained-v2, sha 2ba3ebd, 7m58s, artifacts canonical-binary-definition-plan-v1 6.72 MB + fred-v2-source 1.86 MB); 42370489444 #120 (merge PR #210 kimi/sec-options-defs, sha 230ca55, 8m16s, same artifacts); 42344942142 nai-daily-forward #6 sha e85547a 24s; 42332789888 nai-sec-form13f sha e85547a; 42261199680 / 42252851317 / 42252169840 / 42214284659 / 41575832670 / 41574644199 world-v2-code-ci; 42176587992 / 41982771257 / 41785171922 / 41592147370 / 41413030480 nai-daily-forward; 41413026299 occ sha d5ab097; 41227563332 outside-event-calendar.
Failures: all covered per never-re-report set above. Cancelled (not reportable): 41227556402 outside-event-calendar.

## Open observation (not a failure, nothing filed)
Scheduled slots absent from runs(main): Nov 7 ~19:59Z nai-occ-oi-daily, Nov 8 ~03:10Z nai-sec-form13f, Nov 8 ~05:58Z nai-daily-forward. Newest form13f is still 42332789888 (Nov 7 03:10Z) and newest nai-daily-forward is 42344942142 (Nov 7 05:58Z), so the Nov 8 slots did not fire. A missing run is not a failed run, so this lane does not report it via report_failure; escalate to James/GPT only if the gap persists through Nov 9.

## Lessons
Never infer a traceback from source code. Never trust a truncated UI step to mean the log is missing — report_failure's API path retrieves it. Prefer report_failure(run_id) over freeform issue text. A failed probe differs from a skipped probe. Cloudflare 1042 fixed by global_fetch_strictly_public. A run-page 'Uh oh! error while loading' banner is a GitHub UI artifact, not evidence about the job. A cancelled run is neither a failure nor reportable in this lane. Avoid writing PROGRESS.md on no-change wakes unless the sweep result or a report changed; re-read the blob sha first when writing.

## State
t1–t15 done. No unreported failure as of 14:50Z. Open external items: GPT fixing occ_oi_daily.py (#220/#223) and sec_datasets.py form345 (#221); plus the un-filed schedule-gap observation above.
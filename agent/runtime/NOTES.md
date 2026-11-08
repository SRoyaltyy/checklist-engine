# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section + METHODOLOGY.md each turn. Lane (TODO.md@c7c31b02e530a35d9944c705d19422d606956809): thin chatbot poke — report a failed nai-sec-* / nai-occ-oi-daily run once with run ID + error, then stop; GPT owns fixes. No pipeline ownership, no collector pushes, no bulk scraping. Calendar #96 parked; #96/#177/#163 other lanes. Ignore venice/calendar-announce-ledger after dca969a.

## File map
Branch venice/sec-options-pipelines. agent/BRIDGE6.js + agent/LOADER6.user.js = browser runtime/loader; agent/DOORMAN.worker.js = GitHub transport (deploy via deploy_worker); agent/DEPLOYER.worker.js; runtime state agent/runtime/. agent/PROGRESS.md last checkpoint commit 24934c4ec5eb073134b19aae1c17f3c745099cad (blob b988307b82ae189a93703ca714839f49d6ae3e61, written 2026-11-08T16:35Z, verified:true) — next write must re-read for a fresh sha. LESSON: expected_sha must come from the most recent read of that exact path; stale sha fails closed — re-read, never blind-retry.

## Proven work
GitHub read/write proof a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof runs/42375131645. Worker self-update preserves bindings. Checkpoint commits: 8a3ed5d5… then 24934c4e… (16:35Z refresh).

## Failure reports — canonical facts
42399694729 / nai-occ-oi-daily #6 / sha 2ba3ebd / job 128484582301 / 2026-11-07T18:07Z -> issue #223 (verified:true). Failed step 'Run python scripts/nai/occ_oi_daily.py'; skipped step 'Run python scripts/nai/oi_probe.py' (per report_failure); error lines 'Traceback (most recent call last):' / "ValueError: invalid literal for int() with base 10: ''" / '##[error]Process completed with exit code 1.'; 1 error annotation (step:5:12), 1 warning (Node20), 1 notice (ubuntu-latest->Ubuntu26). Same ValueError as #220 on a newer head => #220 fix has not landed.
42284432095 / sha e85547a / job 128121492870 -> canonical https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739. Same failed step and same ValueError lines. Supersedes the body's unguarded-DELO inference and comment 6710061417 (which proves oi_probe ran before the failing step). DELO stays unverified inference; never cite as cause.
42156926867 / nai-sec-form345 / sha 8ec34d4 / job 127693199421 -> canonical https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770 (verified:true). Failed step 'Run python scripts/nai/sec_datasets.py form345', skipped none; error lines RuntimeError GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403 Forbidden / urllib.error.HTTPError 403 / RuntimeError HTTP 403 / '##[error]Process completed with exit code 1.' The SEC page itself serves normally and lists quarterly form345 ZIPs, so the 403 is the runner being blocked, not a dead URL.

## Reported run IDs — never re-report
42284432095, 42156926867, 42399694729. Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch, superseded shas d5ab097/b0a563b). 41227556402 cancelled — neither failure nor reportable.

## runs(main) snapshot — identical at 14:41Z / 15:05Z / 15:17Z / 15:37Z / 16:03Z / 16:15Z / 16:28Z / 16:39Z / 16:51Z / 17:00Z (30 entries, unchanged)
Newest: 42434336421 nai-sec-bulk #51 sha 2ba3ebd SUCCESS 30m56s, scheduled 2026-11-08T01:27Z, jobs 128589843164 verify 19s + 128589913741 run 30m32s, artifact sec-bulk-receipt-42434336421 111 KB sha256:4d5af7eac9f2a359c4b25693ba48fe01eb3bb5394a758116533fb92b6439a08b; annotations only 2 Node20 warnings + 2 ubuntu-latest->Ubuntu26 notices plus the known 'Uh oh! error while loading' UI banner.
Other successes: 42391969592 world-v2-code-ci #121 (merge PR #218, sha 2ba3ebd, 7m58s; artifacts canonical-binary-definition-plan-v1 6.72 MB sha256:463d35ed6f8e595653bb0bbe218aada74f7dc16c2e8dc4e1a156887476512058 + fred-v2-source 1.86 MB sha256:2eb5b07256ea1afc6733bce751569169fecc8225fcebd74e9a689ace021f4ba9); 42370489444 #120 (merge PR #210, sha 230ca55, 8m16s; same artifacts 40d815f2… / 39b5d8c7…); 42344942142 nai-daily-forward #6 sha e85547a 24s (only Node20 warning + Ubuntu26 notice); 42332789888 nai-sec-form13f sha e85547a; 42261199680 / 42252851317 / 42252169840 / 42214284659 / 41575832670 / 41574644199 world-v2-code-ci; 42176587992 / 41982771257 / 41785171922 / 41592147370 / 41413030480 nai-daily-forward; 41413026299 occ sha d5ab097; 41227563332 outside-event-calendar.

## Open observation (not a failure, nothing filed)
Scheduled slots absent from runs(main): Nov 7 ~19:59Z nai-occ-oi-daily, Nov 8 ~03:10Z nai-sec-form13f, Nov 8 ~05:58Z nai-daily-forward. Newest form13f 42332789888 (Nov 7 03:10Z); newest nai-daily-forward 42344942142 (Nov 7 05:58Z); newest occ 42399694729 (Nov 7 18:07Z). A missing run is not a failed run, so report_failure does not apply; escalate to James/GPT only if the gap persists through Nov 9.

## Lessons
Never infer a traceback from source. Never trust a truncated UI step to mean the log is missing — report_failure's API path retrieves it. Prefer report_failure(run_id) over freeform issue text. A failed probe differs from a skipped probe. Cloudflare 1042 fixed by global_fetch_strictly_public. A run-page 'Uh oh! error while loading' banner is a GitHub UI artifact. A cancelled run is neither a failure nor reportable. Re-read PROGRESS.md sha before every write; skip the write when content already matches.

## State
t1–t28 done. No unreported failure as of 17:00Z; no new run since 42434336421 (Nov 8 01:27Z). External items open: GPT fixing occ_oi_daily.py (#220/#223) and sec_datasets.py form345 (#221); plus the un-filed schedule-gap observation covering three consecutive missed slots.
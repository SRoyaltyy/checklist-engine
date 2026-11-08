# Venice lane progress

## Assigned lane (main/TODO.md @c7c31b02e530a35d9944c705d19422d606956809)
Thin chatbot poke only: when a `nai-sec-*` or `nai-occ-oi-daily` run fails, post the run ID + error in an issue/PR comment and stop. GPT owns the fix. No pipeline ownership, no collector pushes, no bulk scraping. Calendar work (#96) parked; #96/#177/#163 belong to other lanes.

## Current state (2026-11-08T16:28Z)
- All reportable failures to date are reported exactly once. Nothing new to file this wake.
- runs(main) sweep at 16:28Z is byte-identical to the 16:15Z snapshot: 30 entries, newest run is the green bulk run below. No new `nai-sec-*` or `nai-occ-oi-daily` run has fired since 2026-11-08T01:27Z.
- Latest green run: 42434336421 `nai-sec-bulk` #51, sha 2ba3ebdf977df51e7ab7e1993fdfee27faf19939, SUCCESS 30m56s, scheduled 2026-11-08T01:27Z. Jobs 128589843164 (verify, 19s) + 128589913741 (run, 30m32s). Artifact `sec-bulk-receipt-42434336421`, 111 KB, sha256:4d5af7eac9f2a359c4b25693ba48fe01eb3bb5394a758116533fb92b6439a08b. Annotations are the Node 20 deprecation warning and the ubuntu-latest->Ubuntu26 notice only.

## Canonical failure reports (verified records)
- Run 42399694729 `nai-occ-oi-daily` #6, sha 2ba3ebd, job 128484582301, 2026-11-07T18:07Z -> https://github.com/SRoyaltyy/checklist-engine/issues/223
  - Failed step: `Run python scripts/nai/occ_oi_daily.py`
  - Listed skipped step: `Run python scripts/nai/oi_probe.py`
  - Error lines: `Traceback (most recent call last):` / `ValueError: invalid literal for int() with base 10: ''` / `##[error]Process completed with exit code 1.`
  - 1 error annotation at step:5:12. Same ValueError signature as #220 on the newer main head, so the #220 fix has not landed.
- Run 42284432095 -> https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739
  - Failed step `Run python scripts/nai/occ_oi_daily.py`, same three error lines as above. Supersedes the earlier unguarded-DELO inference and comment 6710061417; DELO is not a verified cause.
- Run 42156926867 `nai-sec-form345`, sha 8ec34d4, job 127693199421 -> https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770
  - Failed step `Run python scripts/nai/sec_datasets.py form345`, skipped steps none
  - Error lines: `RuntimeError: GET failed https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets: HTTP Error 403: Forbidden` / `urllib.error.HTTPError: HTTP Error 403: Forbidden` / `RuntimeError: HTTP 403` / `##[error]Process completed with exit code 1.`

## Reported run IDs — never re-report
42284432095, 42156926867, 42399694729.
Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch on superseded shas d5ab097/b0a563b). 41227556402 cancelled — neither failure nor reportable.

## runs(main) snapshot 2026-11-08T16:28Z (30 entries)
Newest 42434336421 bulk success (above). Failures, all in the never-re-report set: 42399694729 occ (reported #223), 42284432095 occ (reported #220), 42156926867 form345 (reported #221), 42106074154 / 41906860199 / 41710121137 occ (covered), 41413535355 / 41413529249 / 41413017909 / 41413013359 Nov-2 (covered), 41413022188 form13f Nov-2 (covered). Successes include 42391969592 and 42370489444 world-v2-code-ci, 42344942142 nai-daily-forward, 42332789888 nai-sec-form13f, plus earlier world-v2-code-ci, nai-daily-forward, occ sha d5ab097 and outside-event-calendar runs. No run outside the do-not-re-report set failed. Node20-deprecation and ubuntu-latest->Ubuntu26 notices are not failures.

## Open observation (not a failure, nothing filed)
Expected scheduled slots absent from runs(main): Nov 7 ~19:59Z nai-occ-oi-daily, Nov 8 ~03:10Z nai-sec-form13f, Nov 8 ~05:58Z nai-daily-forward. A missing run is not a failed run, so this lane does not report it via report_failure; re-check each wake and escalate to James/GPT only if the gap persists through Nov 9.

## Next action
Re-sweep runs(main) each wake (occ_oi_daily also fires on push, not just the ~19:59 UTC slot). Report any new failed nai-* run once via report_failure, then stop.

## Rules held
No pipeline code edited. No inferred diagnoses published as fact. Sealed buy/sell records untouched. All mutations on venice/* branches.

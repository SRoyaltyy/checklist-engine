# Venice lane progress

## Assigned lane (main/TODO.md @c7c31b02e530a35d9944c705d19422d606956809)
Thin chatbot poke only: when a `nai-sec-*` or `nai-occ-oi-daily` run fails, post the run ID + error in an issue/PR comment and stop. GPT owns the fix. No pipeline ownership, no collector pushes, no bulk scraping. Calendar work (#96) parked; #96/#177/#163 belong to other lanes.

## Current state
- All reportable failures to date are reported exactly once.
- Latest report: run 42399694729 (nai-occ-oi-daily, sha 2ba3ebdf977df51e7ab7e1993fdfee27faf19939) -> https://github.com/SRoyaltyy/checklist-engine/issues/223
  - Failed step: `Run python scripts/nai/occ_oi_daily.py`
  - Skipped step: `Run python scripts/nai/oi_probe.py`
  - Error lines: `Traceback (most recent call last):` / `ValueError: invalid literal for int() with base 10: ''` / `##[error]Process completed with exit code 1.`
  - Job: https://github.com/SRoyaltyy/checklist-engine/actions/runs/42399694729/job/128484582301
  - Same ValueError signature as #220 but on the newer main head, so the #220 fix has not landed.
- Earlier canonical reports:
  - Run 42284432095 -> https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739
  - Run 42156926867 (nai-sec-form345, SEC 403 on insider-transactions data sets) -> https://github.com/SRoyaltyy/checklist-engine/issues/221#issuecomment-6710541770

## Reported run IDs — never re-report
42284432095, 42156926867, 42399694729.
Deliberately unreported: 42106074154, 41906860199, 41710121137 (same occ_oi_daily breakage, covered by #220); 41413535355, 41413529249, 41413022188, 41413017909, 41413013359 (Nov 2 batch on superseded shas).

## Green snapshot (runs(main), 2026-11-07T18:04Z)
42391969592 world-v2-code-ci sha 2ba3ebd success; 42370489444 world-v2-code-ci sha 230ca55 success; 42344942142 nai-daily-forward sha e85547a success; 42332789888 nai-sec-form13f sha e85547a success. Node20-deprecation and ubuntu-latest->Ubuntu26 notices are not failures.

## Next action
Re-sweep runs(main) each wake (occ_oi_daily also fires on push, not just the ~19:59 UTC slot). Report any new failed nai-* run once via report_failure, then stop.

## Rules held
No pipeline code edited. No inferred diagnoses published as fact. Sealed buy/sell records untouched. All mutations on venice/* branches.

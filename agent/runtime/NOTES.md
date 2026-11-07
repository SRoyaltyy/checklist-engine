# Durable Venice notes

## Authority and scope
Read main/TODO.md Venice section and METHODOLOGY.md every turn. Current lane is report failures, not fix SEC/OI collectors.

## File map
Maintenance branch: venice/sec-options-pipelines. agent/BRIDGE6.js is remotely loaded by agent/LOADER6.user.js. agent/DOORMAN.worker.js is the GitHub transport; agent/DEPLOYER.worker.js is its fixed-target deployer. State, plan, progress, notes and receipts are in agent/runtime/.

## Proven work
Exact GitHub read/write proof: a089ee8ac06ad75112451d56543736dcb6393b0b. Runner download proof: https://github.com/SRoyaltyy/checklist-engine/actions/runs/42375131645. Worker self-update preserves existing bindings.

## Failure reporting
Run 42284432095, job 128121492870: occ_oi_daily.py FAILED; oi_probe.py SKIPPED. Exact ValueError is in the job log and canonical report https://github.com/SRoyaltyy/checklist-engine/issues/220#issuecomment-6710271739. Use report_failure(run_id), which derives facts and deduplicates persistently. Do not repeat a freeform report.

## Approaches that failed
Never infer a traceback from source. Never assume omitted text in a checkpoint is absent from the real log. Classic sender once clicked its own badge; fixed in 6.1.2. Cloudflare error 1042 was fixed by global_fetch_strictly_public. Newly pushed worker source may require a later retry while GitHub public source mirrors propagate.

## Next
Read the cached report_failure result for 42284432095, retain these notes, reconcile plan evidence, then resume the current lane one item per wake.

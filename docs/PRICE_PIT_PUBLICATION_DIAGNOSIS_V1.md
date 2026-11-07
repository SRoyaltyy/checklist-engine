# Price PIT publication interruption

The full measurement run 41578885310 hit two distinct interruptions.

1. Part016's completed log records a quota wait from 05:27:06 to 05:54:35 UTC
   on 2026-11-03. It resumed, measured its remaining names, and published all
   50 proofs without a restart.
2. Parts034–175 failed before measuring, at release creation. Sampled logs for
   parts034/035/060 all show that call site. A bounded probe captured the
   previously omitted response: **403 Resource not accessible by integration**,
   despite declared Contents:write and remaining core quota.

Probe [41588017632](https://github.com/SRoyaltyy/checklist-engine/actions/runs/41588017632)
captured that response. After preserving the original worker commit as branch
`codex/price-pit-run-41578885310-source`, probe
[41588743279](https://github.com/SRoyaltyy/checklist-engine/actions/runs/41588743279)
succeeded with the same target commit. It created empty draft release
**432338603**, tag `price-full-cohort-pit-v1-41578885310-1-034`, as an explicit
recovery reservation. That empty reservation is not measurement evidence.

Both probes target `8003fb7906c3bf86d88612495664e597de1c65ae`. Their actual probe
commits/run IDs remain in the runner reports; no existing assets were changed.
The permission response and successful stable-ref experiment are consistent
with GitHub's documented workflow-scope restriction for release targets lacking
a branch-head or tag reference. This fixes publication access without obtaining
broader credentials. See [GitHub's release-target rule](https://github.blog/changelog/2023-11-02-github-actions-enforcing-workflow-scope-when-creating-a-release/)
and [release API documentation](https://docs.github.com/en/rest/releases/releases#create-a-release).

At 06:26 UTC, the original matrix had 33 successful parts, one running part031,
and 142 failed parts034–175. The failed scope is **6,799 names / 10,110,205
setup-day rows**. The retained cohort remains 8,439 names / 12,547,288 rows.
Completed stock proofs must be preserved; recovery must measure only missing
names and reuse the same frozen sources, recipe and worker. Per-part recovery
receipts must identify the actual recovery run and commit, even when restoring
the original dataset namespace.

The original full run remains in place and will retain its historical failure
status. No global rerun, source-packet rewrite, definition change, additional
exclusion or scoring approval follows from this diagnosis. Full-cohort MEASURED
is still pending. The publication probe request is reset false.

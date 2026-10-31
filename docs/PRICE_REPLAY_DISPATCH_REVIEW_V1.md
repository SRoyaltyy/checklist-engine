# Review of the eight quarantined replay mismatches

This is a read-only review of the ten published stock traces from run
`41068145897`, source `063f7fdc7eae2553348701fa10ada97e98bd770f`.
No new indicator computation, producer run, runtime policy or answer edit was
performed. All eight stocks remain `EXCLUDED_REPLAY_MISMATCH` for v1.

The reviewer authenticated every stock JSON body against the SHA in
`NUMERIC_RUNTIME_TRACE_V2.json`, checked identical frozen module hashes across
profiles, matched selectors by question/row/row-key hash, and independently
re-evaluated each recorded comparison from its exact float64 bit patterns.
Repeated baseline selectors and all recorded baseline array comparisons agree.

| Stock | Original mismatch selectors | Dispatch toggle reproduces both codes | Remaining |
|---|---:|---:|---:|
| FEIM | 22 | 0 | 22 |
| HHS | 4 | 4 | 0 |
| JHI | 2 | 0 | 2 |
| NKTR | 8 | 7 | 1 |
| OCGN | 1 | 1 | 0 |
| ABX | 92 | 73 | 19 |
| AMTD | 35 | 17 | 18 |
| CATO | 2 | 2 | 0 |
| Total | 166 | 104 | 62 |

For 104 selectors, the baseline and `no_numpy_dispatch` profiles reproduce the
two retained old/replay codes. Across the matched log-call schedules, no input
ratio hash changes; 910 call records have different log-output hashes despite
identical operand bytes. Those records include full-history and prefix calls
and are not 910 separate failing predicates. This locates a numerical dependency
at the observed `np.log` boundary. The experiment disabled all NumPy dispatch
features together, so it does not prove that changing log alone accounts for
every selector flip, or establish the original producer's historical CPU target.

The remaining 62 have two distinct follow-ups:

- FEIM/JHI account for 24. Their baseline selected `X86_V3`; disabling dispatch
  produced no numeric differences. Both profiles match replay. A supported
  `X86_V4` host has not been tested for these two names in this evidence set.
- The other 38 are exclusively `RETURN_AUTOCORR1_20/60` on NKTR/ABX/AMTD.
  Frozen `world_bar_statistics._autocorrelation` centers two vectors, calculates
  three `np.dot` products and divides by their square-root denominator. Record
  the selected dot/BLAS backend and exact operands/results before testing that
  dependency. A BLAS explanation is a hypothesis, not an established cause.
  The saved `np.show_runtime()` output warns that `threadpoolctl` was absent;
  it does not identify the active BLAS core.

Before proposing any runtime policy, use a same-host log-only substitution with
matched operand bytes and a baseline reinjection control. Test FEIM/JHI on an
actually supported X86_V4 host, and separately inspect the autocorrelation dot
path. An unsupported host is an inconclusive experiment, not grounds to force
unsupported CPU instructions. Preserve the exact unresolved selector ledger.

The two control stocks (DJCO/BPOP) retain all six selected control answers across
the toggle. Baseline prefixes have zero recorded bit differences on the measured
schedule. Neither observation establishes complete-universe PIT, arbitrary-prefix
stability, full-world acceptance or permission to remove quarantine. The current
price rebuild/recovery continues unchanged and scoring remains closed.

`PRICE_REPLAY_DISPATCH_REVIEW_V1.json` retains every selector's old/replay codes,
profile codes, numeric operand bits, source release/hash and unresolved family.
Reproduce using only Python's standard library and the already published stock
JSON files, arranged as `<evidence-root>/<release>/NUMERIC_RUNTIME_STOCK_TRACE_V2.json`:

```text
python docs/repro_price_replay_dispatch_review_v1.py --summary docs/NUMERIC_RUNTIME_TRACE_V2.json --evidence-root PATH_TO_STOCK_JSONS --output REVIEW.json
```

No dependency installation or market-data recomputation is required.

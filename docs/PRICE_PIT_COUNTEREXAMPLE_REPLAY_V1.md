# Three-name price packet repetition diagnostic

Run [41582288832](https://github.com/SRoyaltyy/checklist-engine/actions/runs/41582288832)
completed six clean-process repetitions of the unchanged full-measurement worker
at commit `5c1c8d25f8e7ac3a6c95bde492e07848f2695775`. Its LF-normalized worker
SHA256 is `d48f918fe27bbdab5df56d4408d74284deba47406b323a138dfd459fa3cddbc2`,
identical to the worker used by full-cohort run 41578885310.

| Name | Original packet differences | Repeat 1 | Repeat 2 | Repeat proof bytes equal original |
| --- | ---: | ---: | ---: | --- |
| AQMS | 1 | 1 | 1 | Both |
| AZIO | 1 | 1 | 1 | Both |
| BYRN | 16 | 16 | 16 | Both |

All six repetitions pass the two predeclared numeric prefix cuts and independent
setup-day alignment checks. The sampled packet differences are finite YES/NO
flips in direction predicates; their missing-value difference counts are zero.
No stored packet, arithmetic, CPU dispatch setting, definition or universe
membership changed. The diagnostic used one AMD EPYC 9V45 runner with default
dispatch and one BLAS/OpenMP thread.

The result establishes repeatability of the **reported differences** on this
runner. The proof format retains counts and bounded examples rather than every
numeric array or every differing answer position. Equal proof bytes therefore
do not establish equality of all recomputed numeric values or all answer bits.
The cause remains **NOT_PROVEN**. Hardware capability information does not prove
which kernel produced an original answer.

Readback of the three original producer job logs confirms Python 3.12.15,
NumPy 2.5.4, pandas 2.3.3, Arrow 26.0.0 and TA-Lib 0.8.2 there as well. The
selected log lines and job links are in
`PRICE_PIT_COUNTEREXAMPLE_ENVIRONMENT_READBACK_V1.json`. Other packages differ
(for example python-dateutil 3.0.0 versus 4.0.0); this is not a proof of complete
environment equivalence or of a particular dependency causing the flips.

All eight public result/request/stock-proof bodies were independently downloaded
and checked against authenticated release sizes and SHA256 digests. The exact
public report is `PRICE_PIT_COUNTEREXAMPLE_REPLAY_V1.json`, 9,163 bytes, SHA256
`e78345b52e9aea3762391c30f9ad518b27ffaaafdc10eb83d1e830fb8b1ade16`, on
[the diagnostic release](https://github.com/SRoyaltyy/checklist-engine/releases/tag/price-full-cohort-pit-v1-41582288832-1-counterexample-replay).

This three-name diagnostic does not replace the full retained-8,439 measurement.
Full-cohort run 41578885310 continues independently. Historical eligibility,
provider revisions, canonical binary coverage and column availability remain
separate gates. Scoring stays **CLOSED**. The diagnostic execution request is
reset to false after publication.

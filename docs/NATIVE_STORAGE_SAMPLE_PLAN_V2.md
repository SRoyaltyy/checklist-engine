# Lossless storage measurement under the amended plan

Authority: James/Cyrus's 2026-10-28 ~15:45 HKT entry, commit
`9f390e2` (merged by #71). This explicitly permits exact recomputation from
retained raw inputs and pinned code, superseding the previous prohibition.
No full-universe conversion starts before this sample has a measured budget.

The sample is the same MAN/MNTS/EYE native histories, every one of the 1,044
columns on all 22 timeframes, plus the SPY ETF context block on all 22 grids.
Pre-2020 source history is included. The published original numeric containers
are the reference; a successful computation or numerically close result is
insufficient. Recomputed matrices and availability dates must match their
stored SHA-256 fingerprints byte for byte, including signed zeros and NaN bits.
The ETF comparison covers every SPY column and every grid key against the
published ETF Parquets using that producer's historical code.

`ci/numeric_recompute_measure.py` authenticates the raw bars, calendar, frozen
recipe, and original containers. Separate subprocesses isolate historical
imports. Its report records the actual Python/package versions, source hashes,
runtime and stock peak RSS. A failure or timeout is published as incomplete;
there is no implicit recomputation acceptance or deletion of stored values.
No historical stock-to-sector/industry membership is inferred from a current map.

The independent compression experiment in `ci/numeric_reencode_measure.py`
tries ten reversible uint64 encodings on those existing stored arrays: the
original XOR, plain byte planes, first/second temporal deltas, optional adjacent
column deltas, and optional zigzag. Each candidate is decoded and compared,
then the selected output container is reopened and checked again. Existing v1
XOR defaults remain unchanged; delta layouts use a distinct v2 format. Only
identical column registries are shared. No column, row or timeframe is pruned.

The compression report projects numeric payloads with independently verified
per-timeframe native row counts. Dates, container overhead, answers, raw data,
shared/nonprice sources and additional question intermediates are explicitly
excluded from that number. The reconstruction report does not invent a full
world estimate: that requires the complete retained dependency inventory and
the remaining universe/question coverage. The existing roughly 560 GB weighted
measurement remains a failed budget result until superseded by actual evidence.

The workflow uses one runner, with bounded subprocess timeouts. The live world
build `40621517496` is never restarted, cancelled or reseeded. PRs #35/#43 remain
draft; scoring stays closed. Local validation: 118 focused tests pass with the
existing runtime, without dependency installation. Historical full-sample
reconstruction is a GitHub-runner check, not a claimed local result.

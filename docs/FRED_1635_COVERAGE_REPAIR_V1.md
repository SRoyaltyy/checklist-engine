# Explicit coverage for the eight extra FRED series

James's09:10 review correctly found no WORLD_COVERAGE rows for T10Y3M, T5YIE,
T10YIE, STICKCPIM159S, DFII10, CIVPART, INDPRO or BUSLOANS. The successful source
and native builds did not substitute for those missing rows.

Fresh public readback authenticated all24 assets/13106174 bytes in
`shared-context-v2-40636949344-1`. Every one of its22 native files was reopened
and measured on the exact12364370 approved stock-day weights, covering1712
market sessions. All8×22 level measurements are100%, first2020-01-02 through
2026-10-23, and exactly reproduce the previously published stock-day coverage.
No missing field was silently omitted or filled with zero.

WORLD_COVERAGE adds176 `fred_1635_native` rows, each naming the actual column,
native file/SHA, requested and official source identifier, reader, measured
stock-day counts, first date and scope. Existing rows remain unchanged. These
are the eight separate16:35 series; T10Y2Y and BAMLH0A0HYM2 remain on I195.
STICKCPIM159S maps explicitly to official STICKCPIM159SFRBATL and the stored
requested-name column `fred_stickcpim159s`; it is not counted twice.

ALFRED vintage_date<D is retained. Native levels sample the last-known vintage
at each boundary; monthly source facts are never interpolated. The producer's
44 real-source cutoff checks remain bound by its authenticated status file.
This repairs a measured-component/source-evidence gate; historical stock
eligibility, full world/question state, comprehensive leak and full dependency
budget/scoring remain separate open requirements.

Reproduce with `python -m ci.fred_extra_coverage` using the released native
directory, authenticated weights and the pinned published stock-day coverage.
The verifier rejects missing series or changed source bytes and retains zero
observations explicitly.14 local verifier/reader tests pass. No new vendor
request, release rewrite, local installation or protected-run action occurred.

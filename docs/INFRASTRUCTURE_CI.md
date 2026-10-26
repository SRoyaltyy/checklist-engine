# Infrastructure CI and world-data acceptance

The Phase 0 code check and the P1–P5 data gates prove different things.

- `world-v2-code-ci` runs imports before any source job, all regression tests, the real SEC companyfacts requests and the live ALFRED fetch. A SEC source is accepted as **BLOCKED**, not fetched, only when its public report contains the URL, HTTP status, response excerpt, identified User-Agent, request pacing and all retry attempts. Partial retrieval cannot be waived as a whole-source block.
- `world-v2-data-validation` retains the actual measured-world gate, including `--gate`. A failed coverage gate fails that workflow. It is an explicit data-validation run rather than a 40-minute six-stock rebuild on every code edit. Full-universe workflow work follows the Phase 0 merge.
- Source-handling CI may publish a provisional `docs/WORLD_COVERAGE.csv` based on the already released six-stock measurements plus fresh SEC request evidence. Every row says `SIX_STOCK_PROVISIONAL_NOT_FULL_UNIVERSE`. This file cannot tick Phase 1, 2 or 4.
- A green code check does not approve a world state, any questions, Step A, a shortlist, a combination fit or probabilities. Those stages require the full catalog/universe and the actual world/question quality and leakage gates.

The regression tests force an import failure, an upstream command exit 23 and empty release inputs. They check that fetch/downstream commands do not run and that the original command, exit code and log excerpt survive. Provisional publication first creates a draft and checks uploaded assets before making a release public.

James's 2026-10-26 ~09:40 HKT entry directs this infrastructure implementation to be merged first, with only the Phase 0 boxes actually proved ticked afterward. The six-stock snapshot and leak pass remain unticked.

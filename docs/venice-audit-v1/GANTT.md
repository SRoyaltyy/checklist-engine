# Audit Gantt — stages, substages and granular items

Nested overview of the audit hierarchy. Percentages appear **only** on substage rows and are scoped to that substage; large stages and the overall audit carry no computed percentage. Each substage links to its own visual Gantt and to its granular detail page.

Totals: 10 stages, 20 substages, 47 child requirements, 2 main-accepted children.

## Stage S0 — Stage 0: blockers and gates

Stage status: **UNVERIFIED**. Substages: 4.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S0.1 | Legacy replay and quarantine closure | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S0.1.svg) | [detail](details/S0.1.md) |
| S0.2 | Price sample, available_from and join identity contracts | UNVERIFIED | 0.0% (0/3) | 3 | [chart](charts/S0.2.svg) | [detail](details/S0.2.md) |
| S0.3 | Full world gate and PIT packet replay | UNVERIFIED | 0.0% (0/2) | 2 | [chart](charts/S0.3.svg) | [detail](details/S0.3.md) |
| S0.4 | SEC runner access | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S0.4.svg) | [detail](details/S0.4.md) |

## Stage S1 — Stage 1: data and world state

Stage status: **IN_PROGRESS**. Substages: 6.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S1.1 | Price history and corporate actions | UNVERIFIED | 0.0% (0/2) | 2 | [chart](charts/S1.1.svg) | [detail](details/S1.1.md) |
| S1.2 | World-state reference and event feeds | IN_PROGRESS | 12.5% (2/16) | 16 | [chart](charts/S1.2.svg) | [detail](details/S1.2.md) |
| S1.3 | SEC filings panels | UNVERIFIED | 0.0% (0/3) | 3 | [chart](charts/S1.3.svg) | [detail](details/S1.3.md) |
| S1.4 | Options chains and open interest | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S1.4.svg) | [detail](details/S1.4.md) |
| S1.5 | Money flow and imbalance feeds | UNVERIFIED | 0.0% (0/2) | 2 | [chart](charts/S1.5.svg) | [detail](details/S1.5.md) |
| S1.6 | Pipeline documentation | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S1.6.svg) | [detail](details/S1.6.md) |

## Stage S2 — Stage 2: definitions

Stage status: **UNVERIFIED**. Substages: 1.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S2.1 | Lens design and strict indicator definitions | UNVERIFIED | 0.0% (0/2) | 2 | [chart](charts/S2.1.svg) | [detail](details/S2.1.md) |

## Stage S3 — Stage 3: chart viewport

Stage status: **UNVERIFIED**. Substages: 1.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S3.1 | Chart viewport feature | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S3.1.svg) | [detail](details/S3.1.md) |

## Stage S4 — Stage 4: question framework

Stage status: **UNVERIFIED**. Substages: 1.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S4.1 | Complete question framework and batches | UNVERIFIED | 0.0% (0/2) | 2 | [chart](charts/S4.1.svg) | [detail](details/S4.1.md) |

## Stage S5 — Stage 5: answer generation

Stage status: **UNVERIFIED**. Substages: 1.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S5.1 | Computed historical answers for the full question set | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S5.1.svg) | [detail](details/S5.1.md) |

## Stage S5B — Stage 5b: v2 ladders and aliases

Stage status: **UNVERIFIED**. Substages: 1.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S5B.1 | V2 ladder and alias semantic completion | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S5B.1.svg) | [detail](details/S5B.1.md) |

## Stage S6 — Stage 6: mining and exit rules

Stage status: **UNVERIFIED**. Substages: 3.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S6.1 | Combination coverage and interaction orders | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S6.1.svg) | [detail](details/S6.1.md) |
| S6.2 | Exit-rule registry applied per setup | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S6.2.svg) | [detail](details/S6.2.md) |
| S6.3 | Luck correction and same-day benchmark | UNVERIFIED | 0.0% (0/1) | 1 | [chart](charts/S6.3.svg) | [detail](details/S6.3.md) |

## Stage S7 — Stage 7: evaluation and reporting

Stage status: **UNVERIFIED**. Substages: 1.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S7.1 | Per-setup and exit-tuple statistics | UNVERIFIED | 0.0% (0/3) | 3 | [chart](charts/S7.1.svg) | [detail](details/S7.1.md) |

## Stage S8 — Stage 8: shadow and live gates

Stage status: **UNVERIFIED**. Substages: 1.

| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |
|---|---|---|---|---|---|---|
| S8.1 | Shadow and live gate status | UNVERIFIED | 0.0% (0/2) | 2 | [chart](charts/S8.1.svg) | [detail](details/S8.1.md) |

Percent basis used on every substage row: numerator = child requirements with main_acceptance_status COMPLETE; denominator = child requirements in that substage; scope = that substage only.

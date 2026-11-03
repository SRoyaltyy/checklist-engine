# SEC + Options strict definitions — design spec v1

**Lane:** TODO.md Kimi item 3 (Cyrus 2026-11-03 11:21 HKT): "Then SEC and options
strict definitions → [2 Define / Strict definitions]. Binary / fixed-outcome only,
no free text."
**Author:** Kimi. **Status:** spec for James/Cyrus review; implementation follows
approval, family by family. Definitions only — never data downloads (Venice's lane).

---

## 0. Scope decisions (please confirm)

1. **Ownership.** This TODO item supersedes the older assignment of the
   options/money-flow *new families* to GPT (`docs/BINARY_QUESTIONS_V1.md`
   2026-10-30 00:41, METHODOLOGY §00 line 27). GPT keeps price-world columns,
   `available_from`, join keys and the world gate; **Kimi owns all question
   definitions**, price and non-price. Flagging so James can correct if wrong.
2. **Frozen inventory.** Per `docs/OPTIONS_MONEYFLOW_INVENTORY_V1.md` the 258 items
   are fixed — definitions attach only to existing items: **C26, I178, I187, I188,
   I189, I192, I193, I194, I196, I197, I199, I201, I202**. No new data kinds.
3. **What gets defined now vs held.**
   - **Definable now** (source components authenticated): I201 CBOE market-wide
     options (DATA_READY); I189 FINRA short volume; event-facet definitions for
     I187 Form 4, I197 analyst, I199 13F, I188 short interest, I192 XBRL — these
     bind to Venice's pipelines and answer `NOT_EVALUABLE` with explicit reasons
     until the data lands.
   - **Held as placeholders** (required fields unauthenticated, per inventory
     table): single-stock IV level/percentile/term/skew, unusual volume, max pain,
     OI walls (I202); net flow, large/small orders, block/dark-pool prints, ETF
     flows. No definitions published for these until their components exist —
     writing YES/NO formulas against missing baselines would manufacture
     precision. The existing placeholder sections in `BINARY_QUESTIONS_V1.md`
     remain the tracking record.

## 1. Contract rules every definition obeys

From `docs/BINARY_QUESTIONS_V1.md` + METHODOLOGY §P4 + dictionary C29:

- Answers exactly `["NO","YES"]`; `NOT_EVALUABLE` is excluded from the answer set,
  never counted as NO. Missing / short history / pre-source-start → NE with a
  compact reason code. A known 0 is evaluable.
- `formula` = `(<feature_expression>) <comparator> <literal>` on one line;
  thresholds literal only (percentile/z features expose normalized values vs
  literal cutoffs).
- **PIT:** all evidence ends before day D. Non-price records usable only if the
  public timestamp (SEC acceptance datetime, FINRA publication, CBOE session
  publication) is < D 09:30 ET. Filings/insider/13F/analyst join on
  filed/accepted/published date < D — **never** period end. FRED via ALFRED
  vintages.
- feature kinds: `continuous`, `integer_count`, `signed_integer`,
  `category_code`, `boolean` (codebook explicit in `feature_json`).
- Facets per lever 4 (METHODOLOGY line 28), with the event-question convention
  from WAR_ROOM glossary W0-EVT/T20-CNT/T20-EXT: days since/until, count in
  window, direction of last event.

## 2. Direction mapping table (draft — event facets depend on it)

Fixed codebook, no free text. **Pending Cyrus/James confirmation.**

| Event source | bullish | bearish | neutral / countable-only |
|---|---|---|---|
| I197 analyst action | `upgrade` (raise in rating or to-buy) | ` downgrade` (drop in rating or to-sell) | initiate / resume / reiterate / PT-only changes — counted, not directional |
| I187 Form 4 transaction code | `P` (open-market purchase) | `S` (open-market sale) | A, F, G, M, X… — counted, not directional |
| I199 13F position change | — | — | **no direction mapping**: position-change is quantitative only (Δshares, Δfilers); 13F is a holdings report, not an order-flow signal |

## 3. Definition inventory (per item)

Feature-expression naming: `sec_<source>_<measure>_v1(...)` /
`opt_cboe_<measure>_v1(...)`. All window/count parameters are registered dials
with explicit ranges. `timeframe_days=1` unless stated; windows in trading days
ending D-1 (or last available publication < D 09:30 ET).

| Item | Families (facet → example formula) | NE rules |
|---|---|---|
| C26 sector membership | absolute: `(sec_sector_code_v1(as_of=D-1)) = <SIC/GICS code>`; persistence: days in current sector ≥ N (5/20/60); state change: sector changed within last N days; count: membership changes in last 252d | NE if no SEC filing ≤ D-1 carrying dei/SIC data |
| I187 Form 4 | event days-since: `(sec_form4_days_since_last_v1(direction=bullish)) <= 5/10/20`; window count: insider buys in last N sessions ≥ k; cluster: ≥3 distinct insiders with P in last 10 sessions; net $ direction: (Σ$P−Σ$S) over 20d > 0; size: largest P ≥ $100k/$500k/$1M | NE before first acceptance date on record; pre-source-start NE |
| I188 short interest | level: SI % of float > 5/10/20; days-to-cover > 3/5/10; own-history percentile (252d publication points) ≥ 80/90; tercile state-change: percentile crossed 33↔66 within last 2 publication points | NE if latest publication date ≥ D (SETTLEMENT→PUBLICATION lag explicit; use last publication < D) |
| I189 short volume | level: short/total volume ratio > 0.45/0.5/0.55; 5d mean ratio > threshold; own-history 60d percentile ≥ 80; state change: ratio crossed above its 60d median within 5d | NE on FINRA non-publication days (holiday/weekend lag → last published < D) |
| I192 XBRL fundamentals | via `world_sec_facts.py` selection (filed ≤ D-1, original unrestatement, TTM): P/E level vs 10/15/20/30; P/B > 1/3/5; revenue growth YoY > 0/10%; margin expanded YoY (boolean); statuses VALUE only | NE on CONFLICTING_VALUES_SAME_FILED_DATE / MULTIPLE_VALID_PERIOD_STARTS / no qualifying filing; only 3,996/8,439 CIK coverage — NE outside coverage, never NO |
| I193 shares outstanding | Δ shares outstanding % over last 2 filings > ±1% (split/dilution event); boolean: any change in last 63d | NE if no dei record ≤ D-1 |
| I194 Altman Z / Piotroski / Beneish | score level vs threshold (Z > 1.8/3.0; Piotroski ≥ 6/8; Beneish M > −1.78/0); direction: score rose vs prior computation date; computed from I192 facts with dated formula version | NE whenever any input fact is NE — scores never partially imputed |
| I196 dividends/splits | days since last ex-dividend ≤ 30/60/90; dividend per share changed vs prior (boolean); split event in last 63d (boolean) | NE if no distribution record ≤ D |
| I197 analyst actions | days since last upgrade ≤ 5/10/20; net (upgrades−downgrades) in last 30d ≥ 1/2/3; PT change % of last action ≥ ±5/10%; count of actions in last 30d ≥ k | NE before first recorded action < D; direction table §2 |
| I199 13F | # filers holding > 0 vs prior quarter (≥ / Δ); total shares Δ% QoQ > ±10/25%; new filer appears this quarter (boolean); days since latest filing < D check | NE: 13F usable only if filed < D (45-day lag after quarter end); no direction mapping (§2) |
| I201 CBOE market-wide | put/call **volume** ratio level > 0.7/0.8/0.9/1.0; put/call **OI** ratio level; own-history percentile (252 sessions, **era-split**); VIX level band (fixed-set: <12 / 12–20 / 20–30 / >30); VIX term structure state (`contango`/`backwardation` = fixed-set, futures dated < D); SKEW ≥ 120/130/140; equity-only ratio preferred | NE: ratios derived from raw counts at declared precision (not only the 6-decimal convenience column); eras split at 2019-10-07 exchange/group definition break and post-2022 0DTE discontinuity — percentile facets never cross an era boundary |
| I202 single-stock options | **no definitions published yet** — held per §0.3 until the inventory's required fields (dated chain identity, snapshot time, fixed tenor/delta contract) are authenticated | — |

## 4. Binding path into the master

**Decision (2026-11-03, pending James review):** standalone emitter first.
`test_binary_canonical_plan.py` pins the sealed v2.7 grid totals (15,093
questions / 232 cutoffs / 154,667 OAT variants), and grid extension is a
QUESTION_TREE_v3 decision. So SEC/options strict definitions emit to
`docs/BINARY_MASTER_SEC_V1.csv` via `ci/sec_options_master.py` in the exact
26-column BINARY_MASTER_V1 schema (`question_id` prefix `BS1-`), measurements
in `world_sec_events.py`; a future v3 merge into the master is a mechanical
append. First family implemented as the pattern: **I187 Form 4** (28 defs:
days_since / count / cluster / net_dollars / max_trade). Pre-existing master
rows are untouched.

## 5. Validation plan

- New test file(s) `tests/test_binary_master_sec*.py` per family group: tape the
  acceptance-date PIT edge (filing accepted D-1 23:00 ET usable; D 08:00 ET not),
  NE-before-source-start, era-split percentile, 13F 45-day lag, zero-call
  handling for CBOE ratios.
- Full 14-file CI list + emit-consistency block before any merge.

## 6. Open questions for James/Cyrus

1. Confirm scope transfer of options/money-flow family definitions GPT → Kimi (§0.1).
2. Confirm the direction mapping table (§2), especially 13F = no direction.
3. I194: which Altman Z variant for public industrials (original 1968 vs EM),
   and NE for financials/utilities? Default proposed: 1968, NE outside
   industrials.
4. Batch program: TODO froze BINARY_MASTER batches through #177 (now merged).
   Does item 3 authorize new BOUND rows for these SEC/options families as they
   are approved (one PR per family group), or definitions-as-specs first?

# Methodology review — 2026-10-23 (Kimi)

Status: **open review, pending Cyrus's decisions.** Cross-posted as a review comment on PR #5.
Scope: I read `METHODOLOGY.md` on the `docs/methodology` branch, `dials/v2.7.1/README.md`, and the engine code on branch `engine/v2.7.2.2` (`engine.py`, `ENGINE_README.md`, `grid.csv`). This file is the durable copy for the bots.

Overall: the discipline is right — strict before-D rule enforced in code (`A.shift(1)`, k-day bars ending D−1), frozen add-only question files, discover/check/exam splits, fees off, expected-profit-vs-market scoring, and a pre-registered luck bar. The skeleton is sound. The issues below are ordered by how much damage each can do if left unspecified. None requires re-running anything; they are spec decisions to write down before "start Step A".

## 1. The luck bar assumes independent tries; the data is heavily correlated (biggest gap)
5.4 SE over 650,660 tries is a Bonferroni-style number and is fine as far as it goes — but every case-tally behind it violates independence in two ways:
- **Same stock, consecutive days.** One ticker triggering the same answer 10 days in a row is ~1 independent observation wearing 10 costumes.
- **Same day, many stocks.** One macro shock (Feb 2021 rotation, Aug 2024 carry unwind) hits every case dated that week; a sector event hits every name in it.

Both shrink the effective n far below the headline n, so a "5.4σ" result can be 2σ in cluster-robust terms. Fix before Step A: compute the bar on **cluster-robust SEs (cluster by ticker; also check date clustering), or a block bootstrap over tickers×dates**. The "cap how much any single trade can move the average" rule catches one huge winner; it does not catch 200 correlated losers. Cheap version: recompute the bar on winsorised, ticker-de-duplicated cases (e.g. max 1 case per ticker per 21 sessions) and require both bars.

## 2. End-of-sample censoring for outcomes is undefined
The engine hard-cuts data at 2024-12-31, but exit rule v1 needs up to 15 trading days *after* entry, and the 30-day close/best/worst need 30. Every case in roughly the last 6 weeks of 2024 (and of each practice year) has a censored outcome. §4 of METHODOLOGY.md must say explicitly, e.g.: "cases whose full outcome window would cross 2024-12-31 get outcome = NOT_READY and are excluded from all tallies" — and the same rule must be applied identically at the 2025–26 exam boundary. Without this, year-boundary effects and incomplete trades silently contaminate Step A and the exam.

## 3. "Beats the market" needs a frozen, precise benchmark
Cases pass a liquidity + ≥$100M filter and exclude NOT_READYs, so they are not the market. Comparing their mean return to SPY buy-and-hold over the same window mixes the signal with a small/size effect. Specify once: market = equal-weight mean forward return of *all filtered stocks with a ready answer on day D* (or SPY — but say which), same entry/exit rule, same fees. Freeze it in the lock index with the question files.

## 4. Exit rule v1 execution realism
- "Sell at +20% if it gets there" presumes a resting stop that fills *at* +20%. Gaps through the stop fill worse. State the fill assumption (stop-limit at +20%; fills at open if gapped) and run the fee sensitivity at 60bp and 120bp round trip, not just 30bp/side. A setup whose edge is 40bp dies at realistic slippage — better to know on practice data.
- The $1M median dollar-volume floor is admittedly a guess (ENGINE_README says so). For names near the floor, real size can't get in/out at the paper price. Keep them, but report results with a "floor cohort" flag so untradeable-in-size names can't carry a result.

## 5. Survivorship: check where the edge lives
Survivors-only bias is disclosed, which is good. Add one diagnostic to Step B/C reporting: the mcap distribution of passing cases. If an edge concentrates in $100–300M names, expect it to degrade live, because the 2025–26 exam universe (today's survivors) will quietly include names that later die — the live gap will be *worse* than practice suggests.

## 6. Keep a NOT_READY tally per question
-1/n_a cases are excluded, correctly — but NOT_READY correlates with young/small/sparsely-traded stocks, so each question's effective sample is conditioned differently. Store n_total, n_ready, n_not_ready per question+answer so reviewers can see the conditioning.

## 7. The combining model needs the same pre-registration as the questions
METHODOLOGY §1 "later, the good answers get combined into one model" is where a second, bigger round of overfitting lives: 650k candidate features → select winners → fit a combiner on the same 2020–22 data → the combiner's own degrees of freedom eat the luck bar. Before the exam, freeze: (a) the exact combining recipe — recommendation: deliberately boring: logistic regression (or a simple Bayesian tally) on the *confirmed* question+answers only, cap on feature count, no interactions; (b) fitting only on discover_2020_22, calibration checked on check_2023_24; (c) a calibration table (predicted vs realised P(profit) by decile) as a first-class output, since the end goal is "probability of winning at horizon X given this setup bundle."

## 8. Write the 2025–26 split-date metadata exception into the lock rules
`integrity/mcap_fix.py` uses 2025–26 split dates to un-adjust historical prices (MVIS). ENGINE_README defends this as "metadata, not outcomes" and I agree — but it is the single place where 2025–26 data touches the practice pipeline, so METHODOLOGY.md should say it explicitly under house rules, otherwise it looks like a leak in retrospect.

## 9. Cutoff-grid near-duplicates (state it, no action needed)
232 OAT cutoffs contain many near-identical versions (leg=3 ATR vs 4 ATR). The 650,660 try count treats them as independent, so the 5.4 bar is *conservative* — fine, safe direction. One sentence in §7 noting the effective number of independent tests is far smaller than 650,660 is enough.

## 10. Doc nits
- §3: name the structure explicitly as "**dials 1–4 + history lever**". (To answer Cyrus's question: yes, it is documented — in `ENGINE_README.md`'s title and `dials/v2.7.1/README.md`; the 15,093 = 6,654 base + 8,439 history split in §3 is correct.)
- §3 should state which subset of the 15,093 questions Step A actually computes: per ENGINE_README the built daily-only engine covers 2,023 answer columns at lookbacks 10/20/60; k>1 bars and the not-built variant list mean the full tree isn't covered yet. Not a flaw — but the doc currently implies the whole tree runs.
- ENGINE_README is stale on two counts: question count (14,588 at v2.6 write-up vs 15,093 locked) and the grid (v2.7.2.2 = 232 cutoffs / 154,667 versions, while ENGINE_README still describes the default-cutoff build). One refresh line each.
- The New Bot §0 resources table from the PR #5 comment thread is still not folded in.

## Decisions only Cyrus can make
1. The market benchmark (#3).
2. The outcome-censoring rule (#2).
Everything else can be drafted into §4/§7 wording once those two are picked.

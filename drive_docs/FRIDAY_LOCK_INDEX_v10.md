# Friday joint lock index — Fri 2026-10-23 23:00 HKT

Manager Bot listing. **v8** updated 2026-10-22 ~20:40 HKT (path bank v2 frozen). Supersedes v7 (Drive 1YSMIyqbLq7Bfz0JfogiKYCBRLfykKGaZ), v6 (Drive 1FU5lOm7bfWZaI51XA7mjrQ2tk3BMHpUL), v5 (Drive 1wFIdBs0_RvwE-Gr64eeV3uFhZniCYhCH), v4 (Drive 1555hpgRi0WRZPYIIucjajeQ0DlW-E5RZ), v3 (Drive 14vtWrL3tfPvXUuFP781BQ9sqEwbI-1uH), v2 (Drive 1gHM5dNDGpc_HbFoJmnkhHtrmU4JbDkzS) and v1 (1hQO1DlhcohGBILl6IaltwcyBsG3Um6pp).
2025–26 stays sealed until that open. HINT numbers from 2020–24 are not passes.

## Chart-picture / story core (Cyrus yes 2026-10-22)

| Item | sha256 |
|------|--------|
| **FROZEN_RECIPE.md** | **bf8a2d79001cef5476d8caa9d13a87bc3dcb1ce81ec9f9b8b5d2d4c2fa304ef6** |
| chart_picture_gate.py | 2059efb613c62fe178c5f91c6ddbc9c7d49fc6651db86e126f5cf3c9a2c774e8 |
| PRELOCK_ADDENDUM_CHART_PICTURE.md | 9a5e6b89a529095d3953f279e001e7ff54c9ffe2d074240ff8af44fa58b93d0c |
| match2.py | bea4bf150b64d9789c6713f18d3a3b435fb99e04b9b6cee0daafb0b0ac9169f9 |
| feats.py | 687db55fbcc3174be32ca18c5e825e26283e7eca4d393b0690f2fa2ab369c5bf |
| feats2.py | d54ce7219c6c5bb7ff30e02e0538f93d06d3f5710ec72a2626cb74dfe0c6f2f5 |

Local pack: `/workspace/checklist_brainstorm/chart_picture/`  
Taskforce pack: `/workspace/checklist_brainstorm/mine/state_test/chart_picture/` (and Drive `checklist_engine_chunks`)  
Selftest: AAPL 2022-09-01 FAIL; ALDX twin PASS; CWEN PASS.  
2020–24 twin outcomes: **HINT only**. First real test: 2025–26 at Fri open.

Hard gates (any fail → not same setup): BB mid slope up; body g:r20 ≥ 0.9; %B ≥ 0.12; dip ≤ 4.2 ATR; days since 20d high in [5,18]; giveback of prior run ≥ 0.5. Soft warn only: red/green vol 10d > 1.0. `lower_highs10` stays continuous.

## Other locked pins (from earlier addenda; do not retune)

| Lane | Item | sha (short / full as recorded) |
|------|------|--------------------------------|
| 00051-C + earn-in-30 | addendum v5 | 926cd311…c4ed |
| 00051 | scorer | 885da90b…49ac |
| earn tags | pin | 08f15079…42cc |
| 2025–26 earn manifest | pin | ee6e836a…915d |
| F4TR sealed tar | pin | d8ed17c3…b628 |
| bucket map | pin | f10a3103…d382 — **LOST** (map v4; superseded by v5 below) |
| OHLCV6 warnings | addendum | b30c467e…544a |
| OHLCV6 | scorer v6.1 | afe1e5d0…65dd |
| New Bot OHLCV NB manifest | pin | 784e00ac…6e45 (tar e53a8960…7506) |

Correction: earlier short `a31064c4…0e` for the recipe was wrong; use **bf8a2d79…ef6** only.

## Bucket map (Grok Bot, 2026-10-22 ~18:07 HKT)

| Item | sha256 (short) | Drive |
|------|----------------|-------|
| map v5 csv | 8a9b8fbc…890c | Drive 1hYeYZ6u… |
| map v5 md | 646d0b73…d0ce | Drive 1eJTx3t__… |
| map v4 | f10a3103…d382 | **LOST** — never uploaded to Drive; nothing depends on it |

v5 adds cp-01…cp-06 HARD + cp-07 soft warn; `in_engine_counts` still false until Taskforce/New Bot land answer chunks. Recipe/addendum/gate pins unchanged.

Old v5 pair (csv 65ecd4d7…1fc5 / md dea9da68…5047) is replaced by the aligned pair above.

## Survivors price file (pinned v3)

`/workspace/pricehist/universe_2020_survivors.parquet` = original locked file, verified with sha256sum 2026-10-22 ~19:55 HKT:
`fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337`
All builds record this hash. Rebuilds 0c94c3af… and 2601ba63… are dropped. Builds filter to 2020–24.

## Options-IV v2 (Grok Bot)

Options-IV rows 2020–24 rebuilt as v2 (README Drive 1YIraOFc…), same 6 rows and point-in-time rule as v1. Vs v1: 2020 99.68% match (mostly 6–8 Jan, DoltHub no pre-6-Jan reading), 2021 99.94%. 2025–26 sealed.

## Chart-picture gate status (v5): RECOVERED — IN Friday lock (unconditional)

Restored ~19:38 HKT at `/workspace/state_test/case_arqt/`; sha256 verified locally 2026-10-22 ~20:15 HKT, all match locked pins:

| File | sha256 (full, verified) | Drive |
|------|-------------------------|-------|
| feats.py | 687db55fbcc3174be32ca18c5e825e26283e7eca4d393b0690f2fa2ab369c5bf | 1uRP-lUf3vF1svD2_juGbIw_gn7KHeVuT |
| feats2.py | d54ce7219c6c5bb7ff30e02e0538f93d06d3f5710ec72a2626cb74dfe0c6f2f5 | 1bT8WkfD-JUgPsP2msUFjHXhog0A_iIrL |
| match2.py | bea4bf150b64d9789c6713f18d3a3b435fb99e04b9b6cee0daafb0b0ac9169f9 | 1Ll_OPD0Hdkp-sBHUdvdmICC9D8neIYur |
| ARQT.csv | e239c454a99657a6bed3d6925f2d1b2b6df95f8633d49d70b113701c8077b9ca | — |

ARQT.csv: post-wipe restore, unverifiable vs original; reference case only, sets no cutoff.
`checklist_brainstorm/qa/redundancy/feats.py` (51cb9572…) is a different script — do not use.

Selftest 2026-10-22 ~20:10 HKT (Taskforce): AAPL 2022-09-01 FAIL (mid_slope_up, gr_body20, pctB, dip_atr); ALDX 2021-11-18 PASS.

Condition (New Bot cp_* from original feats.py + Taskforce spot-check by Fri 2026-10-23 20:00 HKT): **MET 2026-10-22 ~20:20 HKT**. Gate is IN the Friday lock unconditionally.

### New Bot cp_* build
| Item | sha256 (short) | Drive |
|------|----------------|-------|
| cp_* tags CSV (`cp_build/cp_tags.csv`) | 54a731b2af3f20f7a3a1c82e3c78da9975d40e6f72528238b9dba649b4ea0d64 | inside tar |
| manifest (`cp_build/MANIFEST.json`) | 5f0c3c4377b479e2413a452b8a71427167690569ac199555cc4fb7e3adf47e2a | inside tar |
| tar NBCP_chart_picture_2020_24.tar.gz | 45209602a57b5b72832b475ba6bf1b9c3573fd50c0adf0cfb7125b7edb3725e8 | 1UAGlXkq0rCdbXtwuGuuUiyImQBf8PfHm |

Correction to v5: "inside tar" was an assumption there; now confirmed by New Bot and verified by Grok Bot (sha256sum of Drive download + extracted files, 2026-10-22 ~20:30 HKT).

Taskforce spot-check: **PASS** — 7 cutoffs match gate; 210 truncation values identical (no look-ahead); 1,134 gate-agreement answers; ~22% NOT_READY expected; 2025–26 never read.

Known difference: cp_* answers day D from the last bar before D (≤7 days old); gate selftest reads D's own bar.

CHART_PICTURE_V2_FORMULAS.md (Drive 1pSFAIKcP2EWjieXbG01yVJj6pt-3EeOo, 0badaa4a…) = spare, not built.

## Path bank v1 — "how it got here" (New Bot) — FROZEN 2026-10-22 ~20:25 HKT

264 questions (240 yes/no, 24 fixed labels); 21 families × lookbacks 5/10/20/60. Answers use bars before D only; scored at 5/10/20 trading days only.

| Item | sha256 (verified by Grok Bot ~20:30 HKT) | Drive |
|------|---------------------------------------|-------|
| path_bank_v1.tar.gz | 7931e0a01e21154e4d1c1f18015ab7f27b3a74fc7103ad78bc434958f5aabd4e | 15MzpQAXwLp4abEy11vuOwIFqSp6S_2SL |
| PATH_BANK.csv | 5b09a9e61767219593e31517fe177167523f63a3269c06524da005327dd7b4ba | inside tar |
| path_bank.py | 985e4469192b49cd4a61470d984ad2826294767156c6deb0f42c675e2b1f8c71 | inside tar |

6 families overlap cp_* → correlated evidence, not independent.

## Path bank v2 (New Bot) — FROZEN, unscored (before the Fri 2026-10-23 21:00 HKT deadline; v1 stays locked)

5,716 questions / 76 families, lookbacks 3–60d. No-lookahead test: 5 tickers × 10 dates, 0 mismatches. Refuses 2025+ dates.

| Item | sha256 (verified by Grok Bot ~20:40 HKT) | Drive |
|------|---------------------------------------|-------|
| path_bank_v2.tar.gz | 7e8d2694aa000b3938852dab22a84cd4f235c60e2a5411309eba7d936d9d54f1 | 1RVBDpoSNkBKXDI5JNhhDbUvCb-6QgBS3 |
| PATH_BANK_V2.csv | d077855c75c0d18d14f5cf117fa78ff57e9690d893b813192efd8f5815339f6c | inside tar |
| path_bank_v2.py | d0910085777d40db5563dba0beec60372e149fde65d4a58b812efd2a726679cc | inside tar |

Overlaps cp_*, path bank v1 and story questions → correlated evidence. v2 is **exploratory**: on 2025-26 it gets BH across all 5,716 jointly (only very strong results survive). The 3 pre-registered tests (Q8, Q5, Q7) keep their own small BH family.

## Story questions v1 (Taskforce) — FROZEN, unscored

9 story questions. Frozen, not scored. Q4 and Q7 overlap the path-bank band family → correlated evidence, not independent.

| File | sha256 (verified by Grok Bot ~20:30 HKT) | Drive |
|------|---------------------------------------|-------|
| STORY_QUESTIONS_V1.md | 37da873b1956f242ee823e48084995c892d26aa05a688376253430803522e7a9 | **1AercJPdaXCkGcS6vow6P5P0Z3Mhbb1NC** (canonical) |
| story_q.py | 3828cfb7cfb019c4da0195c3f66c70b766aab54eee63282e5b5d5cfaf0bfbca9 | inside bundle story_q_hint_2020_24.tar.gz **1S51XWlFqQ3tZyY6cFZadeV5_D5z2CR4N** (canonical) |
| bundle story_q_hint_2020_24.tar.gz | 6db01246b6a1761a35836e8973bdd5641aaa2528eb0482b5748905c30eae60eb | 1S51XWlFqQ3tZyY6cFZadeV5_D5z2CR4N |

Local paths: /workspace/state_test/story_q/. Duplicate Drive copies (same sha, not canonical, kept): STORY_QUESTIONS_V1.md 1weuTsyxHo52ydNOEnHkqqBNLrZnFSiPo; story_q.py 1bNMet4ezkmll59Z6B_SAUhT-XFi7j7Ov.

Typo correction: story_q.py was first reported as `3828cfb7…e2a9`; Taskforce confirmed the true pin is `…bfbca9` (file unchanged).

## Pre-registered for 2025-26 (from Taskforce HINT scan)

Source: HINT_SCAN_2020_24.md, Drive 1e8KZS1Wlcf5TBDdGbgNSfQFWz5p1mJw6, sha256 2f3365fefcbd3b254520ebcf61b48469481a11625cbe8f13450d3d42b5ef4bf8 (verified from Drive; same file inside bundle 1S51XWlFqQ3tZyY6cFZadeV5_D5z2CR4N).

1. **Q8 "closed above last red candle high"** = WARNING / fade. All names. Horizons 5/10/21d.
2. **Q5 "biggest red candle of 20d in last 5"**, inside the cp_* all-6-pass group. Primary horizon 10d.
3. **Q7 "lower band touch then bounce"**, inside the pass group. Horizon 10d. Overlaps the path-bank band family (correlated).

Bare cp_* pass = no edge on 2020-24 (HINT only); kept as base filter only.
Same bar for all: 30bp/side costs, matched controls, Benjamini-Hochberg.

## Repo
Private github.com/SRoyaltyy/checklist-engine, owned by James — copy of specs, not data. Path bank in repo via PR; story-q copy in repo pending.

PRELOCK_2025_26.md unchanged.

## v9 additions (2026-10-23 HKT)

v9 = v8 above unchanged (v8 Drive 1GAMBbh33vmt2Lz9QpODukDIrXPo136Xg, sha256 2c18f28b16f872ff2f912b8560423b2eeb167ff353e352db45e3a27e08b8a00a) plus this section. All sha256 below computed by Grok Bot 2026-10-23 HKT and match the posted prefixes. Repo: SRoyaltyy/checklist-engine (main). No 2025+ data read.

### Buyable filter (commit 50e3243) — bundle `buyable_filter_v1/`
| File | sha256 (full) | Drive |
|------|---------------|-------|
| buyable_filter_v1_v2.tgz | 6fca0013aa554aee3b42e7c9f5037f409c2513a2f18a7320dec8cc8a37f3c85f | 1iiHW_iSy0bo5gjZ9ElmJK5vTmGw_mPNp |
| buyable_filter_v1/BUYABLE_FILTER_V1.md | f39b1cb6ff2cfbfd94d37d35d87215476961f8766d9b0fe3bea44b2cd5fb8b25 | inside tgz |
| buyable_filter_v1/buyable_filter.py | ffec7c4aeee5f0629bbde0173ad950ba6b634e727121f800c4ade4ff38465057 | inside tgz |
| buyable_filter_v1/drop_list.csv | 3c1ed970286e7998574748391604033c65d330efcfd9a82a49d47788b745a5a2 | inside tgz |
| buyable_filter_v1/drop_list_v2.csv | 5a6cb756b7b71c1658b89524a6c2349136ad6132c642a88d8e91be4566963239 | inside tgz |

Notes: v2 ETF rule is partial (only 14 ETFs known). Market cap NOT applied (SEC blocked); v3 later.

### Exit rule v1 (Taskforce, commit b4aab94; results csv commit 543d76c) — `practice_results/exit_grid_2020_24/`
| File | sha256 (full) | Drive |
|------|---------------|-------|
| exit_grid_v1.tgz | 6888f4da7c07135bc48f070ae49472edeb1adb97cae8743de59a81bb4b91d6c3 | 1GJ9JEMVWPKAiWj0ttSBPVu98-kf8rgMz |
| EXIT_RULE_V1.md | 215de51396760884d7a3688e752c49465d6676286e0e75628065cb2a72c197d3 | inside tgz |
| exit_grid_results_v1.csv | 6d05f56fa7b1ad001a51c94708477e9a9dbec849f30f4c00403c43837c1b0220 | inside tgz |

EXIT_RULE_V1 = 20% take-profit, no stop, sell at day-15 close; a day touching both target and stop counts as stop; 30bp/side. HINT only (2020–22 +0.40% vs avg, passed BH; 2023–24 +0.09%, missed BH).

### STACKS_V1 (Taskforce) — `practice_results/exit_grid_2020_24/stacks/`
| File | sha256 (full) | Drive |
|------|---------------|-------|
| STACKS_V1.md (pre-registration, written before run) | b877df0f929c9b2547a0ea3647909a312a23c3a09b6055d0fc277c055c8220e2 | — (GitHub only) |
| STACKS_RESULTS_V1.md | 1aa30470f323ae3f8bcb53234aeec3d82e0b2a91d7cdb24281ae7a17dbf087b1 | — (GitHub only) |

Pre-registered stack for 2025–26: **Q5 + no big recent move**, under EXIT_RULE_V1. 2023–24: win 49.3%, +0.11% vs average stock, BH q=0.036 — HINT only. "Running ahead" leg used SPY only (no sector history).

### FINDINGS_FREEZE_V1 (James, commit 3502460)
| File | sha256 (full) | Drive |
|------|---------------|-------|
| FINDINGS_FREEZE_V1.md | 498181f79c7ba69ea063f53aca69ff451f8e9afdf9f754f205423aae14d3e8a0 | 1JkL8w-WHXYN1lrLWqYvBzvvRaJtqQ6Y5 |
| FINDINGS_FREEZE_V1.csv | a8819d1f8925e8b59567871f9b523276f33c92c57beb8c1fd98dc2f79187e66f | 1zWMF-sF0s-IMtsClNSWqh6J0qZ-UuWTm |

1,503 rows (`found_on` column tags 2020–22 discoveries); 320 flagged survivor-bias risk. Near-low / near-high results CANNOT be cleared by 2025–26 (also survivors-only); only live trading days after the lock can clear them. Look-alike (whole-chart) shapes EXCLUDED (59–68% on 2020–22, 46–52% on 2023–24). James's 80% story-question result is RETRACTED (audit commit c567998; pairing artifact, ~50% with fixed 1:1 pairs).

PRELOCK_2025_26.md untouched.

---

## v10 additions (2026-10-23 HKT)

Everything above this line is v9 byte-for-byte (v9 sha256 4d31b9210a473379c1c83c10264e089d1d84516bf1579380b67ce813d36b467b; repo copy SRoyaltyy/checklist-engine commit 16c60d6, drive_docs/FRIDAY_LOCK_INDEX_v9.md; Drive 1zMMe8XOXTza3wViqrP-Yg0oD6Zrmj8Js).

### 1. STACKS_V1 Drive copies (verified by Drive download; identical to v9 GitHub entries)

| File | sha256 | Drive id |
|---|---|---|
| STACKS_V1.md | b877df0f929c9b2547a0ea3647909a312a23c3a09b6055d0fc277c055c8220e2 | 1WOgnrLrrUopgVZ5OgTfjLO7ICkXWnlYv |
| STACKS_RESULTS_V1.md | 1aa30470f323ae3f8bcb53234aeec3d82e0b2a91d7cdb24281ae7a17dbf087b1 | 1our-UPWWZ3u9NColzcooJjXFfuEqn96h |
| stacks_results_v1.csv | 7392253fe161bcf81e4911234cf1255eb6672e2a58d3a330baa4387192b15266 | 1ZE_-FNXhXmqTXj2wTjHQ1mGGozT7d-5m |

### 2. SCORE_V1 — count-the-signs score (verified from GitHub main and Drive round-trip)

Repo: SRoyaltyy/checklist-engine, practice_results/exit_grid_2020_24/score/. SCORE_V1.md added in commit fc4827826b9ce4f8422acf18aabeb90b1ecbd84b; SCORE_RESULTS_V1.md in c884667b1ee5c6f434bb83db35350a323b2cc381; folder head 3fd7980af7813823ab6971a5ebd8faad697786fb (2026-10-23 00:59 HKT).

| File | sha256 | Drive id |
|---|---|---|
| SCORE_V1.md (method, written before run) | 098399e8fa061132f74740bc807bf1cf2323037ac006afc3aac961d1b21fc113 | 153V23amD9Ibega_cGznMJg4LyG7xexVV |
| SCORE_RESULTS_V1.md | e00ece613ac1cf4f49ea0847ba0108f95299dba8655f1f08445808a33ffc9516 | 118hp_0WTOgOkua4AgNmTeIf2q_2DaWvF |

Notes:
- Score uses 2020–22 signs only (FINDINGS_FREEZE_V1), checked on 2023–24.
- Score runs BACKWARDS: top fifth (most winner signs) did worst, hit +10% only 16%, trailed average on both halves.
- Bottom fifth (jumpiest): +0.51%/trade vs average under EXIT_RULE_V1 and +0.70% with 10-day hold on 2023–24, passes luck check — BUT median 10-day trade −1.41%, win rate 45.7%. Lottery-like.
- FLAGGED: bottom fifth possibly flattered by survivors-only data. 2025–26 is survivors-only too; only live post-lock trading days can clear it.
- No fifth reaches 55% wins on 2023–24 under either exit.
- 796 path-bank signs scored; 311 sheet items skipped (listed in items_used_skipped.csv).

Pre-registered for the 2025–26 test (HINTs only): (a) bottom fifth vs average under EXIT_RULE_V1 and under 10-day hold; (b) top-fifth underperformance vs average.

### 3. Other records

- James's 20-pair sample: PAIRS_SAMPLE_20.pdf, Drive 1l8E9nK15HXLa_y6gXx3X8_K8zlyqEOeS, sha fc905310…3766, commit 759232a, seed 20261023 (2020–24 practice data only).
- Look-alike pairs v2 fixed: lookalike_pairs_v2_fixed.tar (parts 00–11), full tar sha b171aba7…61b6, checksums Drive 1Etw8ka_4LfZYxHjJHgfWIt0MrykWwYHI; README commit 44b0e55.
- v9 repo commit 16c60d6.

No 2025+ data read. PRELOCK_2025_26.md untouched.

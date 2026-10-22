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

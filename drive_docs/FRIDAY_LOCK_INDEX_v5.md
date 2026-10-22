# Friday joint lock index — Fri 2026-10-23 23:00 HKT

Manager Bot listing. **v5** updated 2026-10-22 ~20:25 HKT (chart-picture gate condition MET; gate IN Fri lock unconditionally). Supersedes v4 (Drive 1555hpgRi0WRZPYIIucjajeQ0DlW-E5RZ), v3 (Drive 14vtWrL3tfPvXUuFP781BQ9sqEwbI-1uH), v2 (Drive 1gHM5dNDGpc_HbFoJmnkhHtrmU4JbDkzS) and v1 (1hQO1DlhcohGBILl6IaltwcyBsG3Um6pp).
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
| cp_* tags CSV | 54a731b2…0d64 | (in tar) |
| manifest | 5f0c3c43…7e2a | (in tar) |
| tar | — | 1UAGlXkq0rCdbXtwuGuuUiyImQBf8PfHm |

Taskforce spot-check: **PASS** — 7 cutoffs match gate; 210 truncation values identical (no look-ahead); 1,134 gate-agreement answers; ~22% NOT_READY expected; 2025–26 never read.

Known difference: cp_* answers day D from the last bar before D (≤7 days old); gate selftest reads D's own bar.

CHART_PICTURE_V2_FORMULAS.md (Drive 1pSFAIKcP2EWjieXbG01yVJj6pt-3EeOo, 0badaa4a…) = spare, not built.

PRELOCK_2025_26.md unchanged.

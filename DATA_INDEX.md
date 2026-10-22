# DATA_INDEX — large data NOT in this repo

All big files live on the box (`/workspace/...`) or Google Drive folder `checklist_engine_chunks` (id `1FL6sQIYJDAq4xbgLq7YSRseIFC6BqE6I`). Verify sha256 before use.

## Price file (ONLY valid one)
| name | location | sha256 |
|---|---|---|
| universe_2020_survivors.parquet | box `/workspace/pricehist/` | `fb9bbe69147ecf77cfb55c68578a2b4f128f689675d6ba7417cbef5f5b1ef337` |

**DO NOT USE** the rebuilds `0c94c3af…` and `2601ba63…` — they are not the locked price file.

## Chart-picture `cp_*` tags (2020–24)
| item | where | sha256 |
|---|---|---|
| cp_* build tar | Drive `1UAGlXkq0rCdbXtwuGuuUiyImQBf8PfHm` | — |
| tags CSV | inside tar | `54a731b2…0d64` |
| manifest | inside tar | `5f0c3c43…7e2a` |

Taskforce spot-check passed: 210/210 truncation PIT checks; ~22% NOT_READY is expected (insufficient history).

## buckets7 tars (box `/workspace/checklist_brainstorm/buckets7/`, also on Drive)
| file | size (bytes) | sha256 |
|---|---|---|
| buckets7_2020.tar | 35430400 | 743f38abe22aa774580393b649b6a2079f0ef3dc508bc105ad67d56a0522b2bc |
| buckets7_2021.tar | 41185280 | 5b5302896123f7c34e8377324221ce8fb24ed68ed0f17d8ca4091e86896b5d5d |
| buckets7_2022.tar | 44093440 | 7f69569a373847092060afe2968d1c567a66ea0909930c0939207178199f6472 |
| buckets7_2023.tar | 45086720 | 542310b8b927d7cf297e0295ec41da8df2240f64cdc03fd3bd17fbd2e01c673e |
| buckets7_2024.tar | 48435200 | e71e427c67a070f62eda2cc175776f53b4e76d176da6f752458f911a8d9d6adc |

## Drive docs copied into `drive_docs/`
| file | Drive id | sha256 |
|---|---|---|
| FRIDAY_LOCK_INDEX_v5.md (current) | 1wFIdBs0_RvwE-Gr64eeV3uFhZniCYhCH | 3412b7cb422ff748b051d8f48aa8fb39451ff47d53b02cd33da4869d4055c2d9 |
| FRIDAY_LOCK_INDEX_v4.md (superseded) | 1555hpgRi0WRZPYIIucjajeQ0DlW-E5RZ | b2e87bd14940c5d180dbafd13323c2e9d1cc2e68a2115e86d739155045624baf |
| CHART_PICTURE_V2_FORMULAS.md (spare, not built) | 1pSFAIKcP2EWjieXbG01yVJj6pt-3EeOo | 0badaa4adc5b5a071722a944acaa1c588d826f2559d8263edc6fd87b84f10c05 |
| options_iv_README_v2.md | 1YIraOFciAQ70dLMu1yOi83EW_CjazLvd | 73f816314556d8112742331cf918eead2e90cd97b0504b0775e1e37f4bd94e64 |

Map v5.1: `map_v5_1/six_bucket_map_v5_1.csv` sha `fed2c2599133af3689d4f6754f41e45a16b56e25e57f5e1159cb8e291312956b` (map v4 is lost).

Also on the box but not here: engine output CSVs (`checklist_brainstorm/engine`, `qa`), raw caches, `checklist_brainstorm/data`, `drive/`, `archive/`, `repull/`, `inbox/`.

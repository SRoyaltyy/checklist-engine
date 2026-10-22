# Coverage matrix (Grok Bot) - per year x sector
Cells: files / tickers / rows. STK tickers = tickers with bars in the year (from chunk json). FRESH_MKT_ADDON is market-wide (one file per year, all sectors).

Generated 2026-10-22 ~13:55 HKT. Result: 0 MISSING cells (84 year x sector cells, 2020-2026).
- TR Financial 2020-23 is present: TR tickers = STK tickers-with-bars (2020 2,854/2,854; 2021 3,189/3,191; 2022 3,508/3,510; 2023 3,962/3,962). The 1-2 ticker gaps (also seen in Industrials and Utilities in some years) were not investigated; probably names with too few bars for TR.
- Financial files are split into parts in 2020-23 and 2025 (TR__Financial_part0..N), single file in 2024 and 2026 (TR__Financial). A reader that globs only `TR__Financial.npz` / `COUNTS2_TR__Financial.parquet` finds Financial in 2024/2026 only. Use `Financial*`.
- FRESH per-stock is complete for 2020-2026, all sectors (2020 and 2026 finished 13:40-13:44 HKT by the fresh queue).
- 2024 STK Financial ticker figure (18,628) is a sum of the json n_tickers field (that year's json lacks tickers_with_bars_in_year), so it overcounts. Use COUNTS2 or TR (4,656) for that cell.
- COUNTS2 (STK) and FRESH ticker counts include padded tickers with no bars that year (all NR), so they exceed STK-with-bars.

| year | sector | STK | TR | COUNTS2 (STK) | COUNTS2_TR | FRESH | FRESH_MKT_ADDON |
|---|---|---|---|---|---|---|---|
| 2020 | Basic_Materials | 1f / 215 tk / 73,370 r | 1f / 215 tk / 53,289 r | 1f / 290 tk / 73,370 r | 1f / 215 tk / 53,289 r | 1f / 290 tk / 73,370 r | yes |
| 2020 | Communication_Services | 1f / 182 tk / 64,515 r | 1f / 182 tk / 43,826 r | 1f / 255 tk / 64,515 r | 1f / 182 tk / 43,826 r | 1f / 255 tk / 64,515 r | yes |
| 2020 | Consumer_Cyclical | 1f / 383 tk / 133,078 r | 1f / 383 tk / 91,909 r | 1f / 526 tk / 133,078 r | 1f / 383 tk / 91,909 r | 1f / 526 tk / 133,078 r | yes |
| 2020 | Consumer_Defensive | 1f / 174 tk / 60,720 r | 1f / 174 tk / 41,521 r | 1f / 240 tk / 60,720 r | 1f / 174 tk / 41,521 r | 1f / 240 tk / 60,720 r | yes |
| 2020 | Energy | 1f / 198 tk / 63,503 r | 1f / 198 tk / 49,473 r | 1f / 251 tk / 63,503 r | 1f / 198 tk / 49,473 r | 1f / 251 tk / 63,503 r | yes |
| 2020 | Financial | 4f / 2,854 tk / 1,791,493 r | 2f / 2,854 tk / 686,395 r | 4f / 7,081 tk / 1,791,493 r | 2f / 2,854 tk / 686,395 r | 4f / 7,081 tk / 1,791,493 r | yes |
| 2020 | Healthcare | 1f / 702 tk / 265,397 r | 1f / 702 tk / 161,923 r | 1f / 1,049 tk / 265,397 r | 1f / 702 tk / 161,923 r | 1f / 1,049 tk / 265,397 r | yes |
| 2020 | Industrials | 1f / 482 tk / 180,642 r | 1f / 482 tk / 117,432 r | 1f / 714 tk / 180,642 r | 1f / 482 tk / 117,432 r | 1f / 714 tk / 180,642 r | yes |
| 2020 | Real_Estate | 1f / 204 tk / 62,491 r | 1f / 204 tk / 49,578 r | 1f / 247 tk / 62,491 r | 1f / 204 tk / 49,578 r | 1f / 247 tk / 62,491 r | yes |
| 2020 | Technology | 1f / 511 tk / 200,629 r | 1f / 511 tk / 120,601 r | 1f / 793 tk / 200,629 r | 1f / 511 tk / 120,601 r | 1f / 793 tk / 200,629 r | yes |
| 2020 | Unknown | 1f / 9 tk / 40,480 r | 1f / 9 tk / 2,026 r | 1f / 160 tk / 40,480 r | 1f / 9 tk / 2,026 r | 1f / 160 tk / 40,480 r | yes |
| 2020 | Utilities | 1f / 86 tk / 26,818 r | 1f / 86 tk / 21,038 r | 1f / 106 tk / 26,818 r | 1f / 86 tk / 21,038 r | 1f / 106 tk / 26,818 r | yes |
| 2021 | Basic_Materials | 1f / 234 tk / 73,080 r | 1f / 234 tk / 57,387 r | 1f / 290 tk / 73,080 r | 1f / 234 tk / 57,387 r | 1f / 290 tk / 73,080 r | yes |
| 2021 | Communication_Services | 1f / 210 tk / 64,260 r | 1f / 210 tk / 50,249 r | 1f / 255 tk / 64,260 r | 1f / 210 tk / 50,249 r | 1f / 255 tk / 64,260 r | yes |
| 2021 | Consumer_Cyclical | 1f / 437 tk / 132,552 r | 1f / 437 tk / 103,812 r | 1f / 526 tk / 132,552 r | 1f / 437 tk / 103,812 r | 1f / 526 tk / 132,552 r | yes |
| 2021 | Consumer_Defensive | 1f / 195 tk / 60,480 r | 1f / 195 tk / 47,165 r | 1f / 240 tk / 60,480 r | 1f / 195 tk / 47,165 r | 1f / 240 tk / 60,480 r | yes |
| 2021 | Energy | 1f / 211 tk / 63,252 r | 1f / 211 tk / 51,620 r | 1f / 251 tk / 63,252 r | 1f / 211 tk / 51,620 r | 1f / 251 tk / 63,252 r | yes |
| 2021 | Financial | 4f / 3,191 tk / 1,784,412 r | 2f / 3,189 tk / 759,100 r | 4f / 7,081 tk / 1,784,412 r | 2f / 3,189 tk / 759,100 r | 4f / 7,081 tk / 1,784,412 r | yes |
| 2021 | Healthcare | 1f / 848 tk / 264,348 r | 1f / 848 tk / 196,371 r | 1f / 1,049 tk / 264,348 r | 1f / 848 tk / 196,371 r | 1f / 1,049 tk / 264,348 r | yes |
| 2021 | Industrials | 1f / 522 tk / 179,928 r | 1f / 522 tk / 127,065 r | 1f / 714 tk / 179,928 r | 1f / 522 tk / 127,065 r | 1f / 714 tk / 179,928 r | yes |
| 2021 | Real_Estate | 1f / 218 tk / 62,244 r | 1f / 218 tk / 52,551 r | 1f / 247 tk / 62,244 r | 1f / 218 tk / 52,551 r | 1f / 247 tk / 62,244 r | yes |
| 2021 | Technology | 1f / 615 tk / 199,836 r | 1f / 615 tk / 142,389 r | 1f / 793 tk / 199,836 r | 1f / 615 tk / 142,389 r | 1f / 793 tk / 199,836 r | yes |
| 2021 | Unknown | 1f / 9 tk / 40,320 r | 1f / 9 tk / 2,268 r | 1f / 160 tk / 40,320 r | 1f / 9 tk / 2,268 r | 1f / 160 tk / 40,320 r | yes |
| 2021 | Utilities | 1f / 94 tk / 26,712 r | 1f / 94 tk / 22,775 r | 1f / 106 tk / 26,712 r | 1f / 94 tk / 22,775 r | 1f / 106 tk / 26,712 r | yes |
| 2022 | Basic_Materials | 1f / 245 tk / 72,790 r | 1f / 245 tk / 60,428 r | 1f / 290 tk / 72,790 r | 1f / 245 tk / 60,428 r | 1f / 290 tk / 72,790 r | yes |
| 2022 | Communication_Services | 1f / 216 tk / 64,005 r | 1f / 216 tk / 53,638 r | 1f / 255 tk / 64,005 r | 1f / 216 tk / 53,638 r | 1f / 255 tk / 64,005 r | yes |
| 2022 | Consumer_Cyclical | 1f / 450 tk / 132,026 r | 1f / 450 tk / 111,542 r | 1f / 526 tk / 132,026 r | 1f / 450 tk / 111,542 r | 1f / 526 tk / 132,026 r | yes |
| 2022 | Consumer_Defensive | 1f / 199 tk / 60,240 r | 1f / 199 tk / 49,647 r | 1f / 240 tk / 60,240 r | 1f / 199 tk / 49,647 r | 1f / 240 tk / 60,240 r | yes |
| 2022 | Energy | 1f / 216 tk / 63,001 r | 1f / 216 tk / 53,754 r | 1f / 251 tk / 63,001 r | 1f / 216 tk / 53,754 r | 1f / 251 tk / 63,001 r | yes |
| 2022 | Financial | 4f / 3,510 tk / 1,777,331 r | 3f / 3,508 tk / 837,811 r | 4f / 7,081 tk / 1,777,331 r | 3f / 3,508 tk / 837,811 r | 4f / 7,081 tk / 1,777,331 r | yes |
| 2022 | Healthcare | 1f / 886 tk / 263,299 r | 1f / 886 tk / 218,464 r | 1f / 1,049 tk / 263,299 r | 1f / 886 tk / 218,464 r | 1f / 1,049 tk / 263,299 r | yes |
| 2022 | Industrials | 1f / 546 tk / 179,214 r | 1f / 546 tk / 134,586 r | 1f / 714 tk / 179,214 r | 1f / 546 tk / 134,586 r | 1f / 714 tk / 179,214 r | yes |
| 2022 | Real_Estate | 1f / 220 tk / 61,997 r | 1f / 220 tk / 54,983 r | 1f / 247 tk / 61,997 r | 1f / 220 tk / 54,983 r | 1f / 247 tk / 61,997 r | yes |
| 2022 | Technology | 1f / 644 tk / 199,043 r | 1f / 644 tk / 158,741 r | 1f / 793 tk / 199,043 r | 1f / 644 tk / 158,741 r | 1f / 793 tk / 199,043 r | yes |
| 2022 | Unknown | 1f / 9 tk / 40,160 r | 1f / 9 tk / 2,259 r | 1f / 160 tk / 40,160 r | 1f / 9 tk / 2,259 r | 1f / 160 tk / 40,160 r | yes |
| 2022 | Utilities | 1f / 96 tk / 26,606 r | 1f / 96 tk / 23,984 r | 1f / 106 tk / 26,606 r | 1f / 96 tk / 23,984 r | 1f / 106 tk / 26,606 r | yes |
| 2023 | Basic_Materials | 1f / 255 tk / 72,500 r | 1f / 255 tk / 62,364 r | 1f / 290 tk / 72,500 r | 1f / 255 tk / 62,364 r | 1f / 290 tk / 72,500 r | yes |
| 2023 | Communication_Services | 1f / 226 tk / 63,750 r | 1f / 226 tk / 55,140 r | 1f / 255 tk / 63,750 r | 1f / 226 tk / 55,140 r | 1f / 255 tk / 63,750 r | yes |
| 2023 | Consumer_Cyclical | 1f / 472 tk / 131,500 r | 1f / 472 tk / 115,339 r | 1f / 526 tk / 131,500 r | 1f / 472 tk / 115,339 r | 1f / 526 tk / 131,500 r | yes |
| 2023 | Consumer_Defensive | 1f / 208 tk / 60,000 r | 1f / 208 tk / 50,855 r | 1f / 240 tk / 60,000 r | 1f / 208 tk / 50,855 r | 1f / 240 tk / 60,000 r | yes |
| 2023 | Energy | 1f / 224 tk / 62,750 r | 1f / 224 tk / 55,431 r | 1f / 251 tk / 62,750 r | 1f / 224 tk / 55,431 r | 1f / 251 tk / 62,750 r | yes |
| 2023 | Financial | 4f / 3,962 tk / 1,770,250 r | 3f / 3,962 tk / 923,885 r | 4f / 7,081 tk / 1,770,250 r | 3f / 3,962 tk / 923,885 r | 4f / 7,081 tk / 1,770,250 r | yes |
| 2023 | Healthcare | 1f / 909 tk / 262,250 r | 1f / 909 tk / 224,871 r | 1f / 1,049 tk / 262,250 r | 1f / 909 tk / 224,871 r | 1f / 1,049 tk / 262,250 r | yes |
| 2023 | Industrials | 1f / 572 tk / 178,500 r | 1f / 571 tk / 139,482 r | 1f / 714 tk / 178,500 r | 1f / 571 tk / 139,482 r | 1f / 714 tk / 178,500 r | yes |
| 2023 | Real_Estate | 1f / 228 tk / 61,750 r | 1f / 228 tk / 55,953 r | 1f / 247 tk / 61,750 r | 1f / 228 tk / 55,953 r | 1f / 247 tk / 61,750 r | yes |
| 2023 | Technology | 1f / 665 tk / 198,250 r | 1f / 665 tk / 163,991 r | 1f / 793 tk / 198,250 r | 1f / 665 tk / 163,991 r | 1f / 793 tk / 198,250 r | yes |
| 2023 | Unknown | 1f / 10 tk / 40,000 r | 1f / 10 tk / 2,446 r | 1f / 160 tk / 40,000 r | 1f / 10 tk / 2,446 r | 1f / 160 tk / 40,000 r | yes |
| 2023 | Utilities | 1f / 99 tk / 26,500 r | 1f / 98 tk / 24,394 r | 1f / 106 tk / 26,500 r | 1f / 98 tk / 24,394 r | 1f / 106 tk / 26,500 r | yes |
| 2024 | Basic_Materials | 1f / 258 tk / 73,080 r | 1f / 258 tk / 64,488 r | 1f / 290 tk / 73,080 r | 1f / 258 tk / 64,488 r | 1f / 290 tk / 73,080 r | yes |
| 2024 | Communication_Services | 1f / 234 tk / 64,260 r | 1f / 234 tk / 57,901 r | 1f / 255 tk / 64,260 r | 1f / 234 tk / 57,901 r | 1f / 255 tk / 64,260 r | yes |
| 2024 | Consumer_Cyclical | 1f / 494 tk / 132,552 r | 1f / 494 tk / 121,332 r | 1f / 526 tk / 132,552 r | 1f / 494 tk / 121,332 r | 1f / 526 tk / 132,552 r | yes |
| 2024 | Consumer_Defensive | 1f / 217 tk / 60,480 r | 1f / 217 tk / 53,287 r | 1f / 240 tk / 60,480 r | 1f / 217 tk / 53,287 r | 1f / 240 tk / 60,480 r | yes |
| 2024 | Energy | 1f / 232 tk / 63,252 r | 1f / 232 tk / 57,082 r | 1f / 251 tk / 63,252 r | 1f / 232 tk / 57,082 r | 1f / 251 tk / 63,252 r | yes |
| 2024 | Financial | 4f / 18,628 tk / 1,784,412 r | 1f / 4,656 tk / 1,075,645 r | 4f / 7,081 tk / 1,784,412 r | 1f / 4,656 tk / 1,075,645 r | 4f / 7,081 tk / 1,784,412 r | yes |
| 2024 | Healthcare | 1f / 966 tk / 264,348 r | 1f / 966 tk / 236,106 r | 1f / 1,049 tk / 264,348 r | 1f / 966 tk / 236,106 r | 1f / 1,049 tk / 264,348 r | yes |
| 2024 | Industrials | 1f / 618 tk / 179,928 r | 1f / 617 tk / 149,644 r | 1f / 714 tk / 179,928 r | 1f / 617 tk / 149,644 r | 1f / 714 tk / 179,928 r | yes |
| 2024 | Real_Estate | 1f / 237 tk / 62,244 r | 1f / 237 tk / 58,706 r | 1f / 247 tk / 62,244 r | 1f / 237 tk / 58,706 r | 1f / 247 tk / 62,244 r | yes |
| 2024 | Technology | 1f / 701 tk / 199,836 r | 1f / 701 tk / 172,173 r | 1f / 793 tk / 199,836 r | 1f / 701 tk / 172,173 r | 1f / 793 tk / 199,836 r | yes |
| 2024 | Unknown | 1f / 11 tk / 40,320 r | 1f / 11 tk / 2,641 r | 1f / 160 tk / 40,320 r | 1f / 11 tk / 2,641 r | 1f / 160 tk / 40,320 r | yes |
| 2024 | Utilities | 1f / 102 tk / 26,712 r | 1f / 102 tk / 25,365 r | 1f / 106 tk / 26,712 r | 1f / 102 tk / 25,365 r | 1f / 106 tk / 26,712 r | yes |
| 2025 | Basic_Materials | 1f / 269 tk / 72,500 r | 1f / 269 tk / 65,767 r | 1f / 290 tk / 72,500 r | 1f / 269 tk / 65,767 r | 1f / 290 tk / 72,500 r | yes |
| 2025 | Communication_Services | 1f / 252 tk / 63,750 r | 1f / 252 tk / 60,751 r | 1f / 255 tk / 63,750 r | 1f / 252 tk / 60,751 r | 1f / 255 tk / 63,750 r | yes |
| 2025 | Consumer_Cyclical | 1f / 516 tk / 131,500 r | 1f / 516 tk / 125,804 r | 1f / 526 tk / 131,500 r | 1f / 516 tk / 125,804 r | 1f / 526 tk / 131,500 r | yes |
| 2025 | Consumer_Defensive | 1f / 231 tk / 60,000 r | 1f / 231 tk / 55,987 r | 1f / 240 tk / 60,000 r | 1f / 231 tk / 55,987 r | 1f / 240 tk / 60,000 r | yes |
| 2025 | Energy | 1f / 242 tk / 62,750 r | 1f / 242 tk / 59,667 r | 1f / 251 tk / 62,750 r | 1f / 242 tk / 59,667 r | 1f / 251 tk / 62,750 r | yes |
| 2025 | Financial | 4f / 5,844 tk / 1,770,250 r | 4f / 5,841 tk / 1,299,556 r | 4f / 7,081 tk / 1,770,250 r | 4f / 5,841 tk / 1,299,556 r | 4f / 7,081 tk / 1,770,250 r | yes |
| 2025 | Healthcare | 1f / 1,010 tk / 262,250 r | 1f / 1,010 tk / 247,213 r | 1f / 1,049 tk / 262,250 r | 1f / 1,010 tk / 247,213 r | 1f / 1,049 tk / 262,250 r | yes |
| 2025 | Industrials | 1f / 675 tk / 178,500 r | 1f / 675 tk / 162,641 r | 1f / 714 tk / 178,500 r | 1f / 675 tk / 162,641 r | 1f / 714 tk / 178,500 r | yes |
| 2025 | Real_Estate | 1f / 242 tk / 61,750 r | 1f / 242 tk / 59,985 r | 1f / 247 tk / 61,750 r | 1f / 242 tk / 59,985 r | 1f / 247 tk / 61,750 r | yes |
| 2025 | Technology | 1f / 751 tk / 198,250 r | 1f / 751 tk / 181,838 r | 1f / 793 tk / 198,250 r | 1f / 751 tk / 181,838 r | 1f / 793 tk / 198,250 r | yes |
| 2025 | Unknown | 1f / 12 tk / 40,000 r | 1f / 12 tk / 2,751 r | 1f / 160 tk / 40,000 r | 1f / 12 tk / 2,751 r | 1f / 160 tk / 40,000 r | yes |
| 2025 | Utilities | 1f / 104 tk / 26,500 r | 1f / 104 tk / 25,809 r | 1f / 106 tk / 26,500 r | 1f / 104 tk / 25,809 r | 1f / 106 tk / 26,500 r | yes |
| 2026 | Basic_Materials | 1f / 290 tk / 58,580 r | 1f / 290 tk / 57,047 r | 1f / 290 tk / 58,580 r | 1f / 290 tk / 57,047 r | 1f / 290 tk / 58,870 r | yes |
| 2026 | Communication_Services | 1f / 255 tk / 51,510 r | 1f / 255 tk / 51,395 r | 1f / 255 tk / 51,510 r | 1f / 255 tk / 51,395 r | 1f / 255 tk / 51,762 r | yes |
| 2026 | Consumer_Cyclical | 1f / 526 tk / 106,252 r | 1f / 526 tk / 105,625 r | 1f / 526 tk / 106,252 r | 1f / 526 tk / 105,625 r | 1f / 526 tk / 106,774 r | yes |
| 2026 | Consumer_Defensive | 1f / 240 tk / 48,480 r | 1f / 240 tk / 48,036 r | 1f / 240 tk / 48,480 r | 1f / 240 tk / 48,036 r | 1f / 240 tk / 48,719 r | yes |
| 2026 | Energy | 1f / 251 tk / 50,702 r | 1f / 251 tk / 50,290 r | 1f / 251 tk / 50,702 r | 1f / 251 tk / 50,290 r | 1f / 251 tk / 50,952 r | yes |
| 2026 | Financial | 4f / 7,081 tk / 1,430,362 r | 1f / 7,081 tk / 1,314,679 r | 4f / 7,081 tk / 1,430,362 r | 1f / 7,081 tk / 1,314,679 r | 4f / 7,081 tk / 1,437,376 r | yes |
| 2026 | Healthcare | 1f / 1,049 tk / 211,898 r | 1f / 1,049 tk / 209,232 r | 1f / 1,049 tk / 211,898 r | 1f / 1,049 tk / 209,232 r | 1f / 1,049 tk / 212,942 r | yes |
| 2026 | Industrials | 1f / 714 tk / 144,228 r | 1f / 714 tk / 140,863 r | 1f / 714 tk / 144,228 r | 1f / 714 tk / 140,863 r | 1f / 714 tk / 144,937 r | yes |
| 2026 | Real_Estate | 1f / 247 tk / 49,894 r | 1f / 247 tk / 49,604 r | 1f / 247 tk / 49,894 r | 1f / 247 tk / 49,604 r | 1f / 247 tk / 50,141 r | yes |
| 2026 | Technology | 1f / 793 tk / 160,186 r | 1f / 793 tk / 156,803 r | 1f / 793 tk / 160,186 r | 1f / 793 tk / 156,803 r | 1f / 793 tk / 160,973 r | yes |
| 2026 | Unknown | 1f / 159 tk / 32,320 r | 1f / 159 tk / 4,591 r | 1f / 160 tk / 32,320 r | 1f / 159 tk / 4,591 r | 1f / 160 tk / 32,362 r | yes |
| 2026 | Utilities | 1f / 106 tk / 21,412 r | 1f / 106 tk / 21,398 r | 1f / 106 tk / 21,412 r | 1f / 106 tk / 21,398 r | 1f / 106 tk / 21,518 r | yes |

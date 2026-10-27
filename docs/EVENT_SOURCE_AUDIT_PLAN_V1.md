# Completed event source audit

Run 40454756033 completed all eight analyst and eight earnings fetch jobs. A green source job only proves the attempts completed, not historical completeness or point-in-time availability. The audit pins that run's head, attempt, frozen input manifest and shard count. It reads the released bytes only and issues no provider requests.

For every shard it requires the exact sorted requested/attempted canonical ticker list, completed source status and consistent source/part/attempt row totals. Every Parquet must match both the status and receipt hashes, schema, per-ticker count and requested ticker membership. The combined actual ticker row counts must match the whole shard attempt ledger. Duplicate rows, duplicate receipt tickers, inconsistent local event dates and mislabeled naive timestamps fail. It records all source hashes, part bounds, non-null field counts, rows by year and distinct tickers by year.

Empty provider responses remain `NO_ROWS_RETURNED_HISTORY_UNPROVEN`; source errors remain errors. Provider event timestamps and a current download do not establish first historical observation, revision vintages or original release timing. These gates stay unproven, and world/scoring remain closed. The immutable audit report measures the actual source gaps that the next historical-source/PIT work must address.

Validation: 25 local audit/parser/transport tests passed. Linux CI repeats these before reading all released parts. No local dependency installation or heavy data processing is performed.

## Semantic missingness correction (audit v2)

Direct inspection of analyst shard 0, `events_0000.parquet`, found 608 whitespace/empty `from_grade` strings among 1,861 rows. Pandas `notna()` counted all 1,861 as non-null. Those raw byte-audit counts therefore cannot be used as meaningful grade coverage. Audit v2 retains raw non-null counts, subtracts blank strings for semantic coverage, records blank counts and provider timezone categories, and leaves every published source part unchanged. Numeric zero and nonempty identifiers such as ticker `NA` remain valid. The original audit/release remains immutable.

Future fetch normalization strips category padding and emits null for empty firm/grade/action values. Missing action implies missing direction; no grade or direction is invented. The v2 audit reuses the existing source run/head and all 688 parts, with no provider or SEC requests. It still does not establish historical completeness, original publication timing or revisions. Twenty-seven local audit/parser/transport tests passed, including blank-category/zero/NA-identity cases; Linux CI and the actual v2 re-audit follow.

# Completed event source audit

Run 40454756033 completed all eight analyst and eight earnings fetch jobs. A green source job only proves the attempts completed, not historical completeness or point-in-time availability. The audit pins that run's head, attempt, frozen input manifest and shard count. It reads the released bytes only and issues no provider requests.

For every shard it requires the exact sorted requested/attempted canonical ticker list, completed source status and consistent source/part/attempt row totals. Every Parquet must match both the status and receipt hashes, schema, per-ticker count and requested ticker membership. The combined actual ticker row counts must match the whole shard attempt ledger. Duplicate rows, duplicate receipt tickers, inconsistent local event dates and mislabeled naive timestamps fail. It records all source hashes, part bounds, non-null field counts, rows by year and distinct tickers by year.

Empty provider responses remain `NO_ROWS_RETURNED_HISTORY_UNPROVEN`; source errors remain errors. Provider event timestamps and a current download do not establish first historical observation, revision vintages or original release timing. These gates stay unproven, and world/scoring remain closed. The immutable audit report measures the actual source gaps that the next historical-source/PIT work must address.

Validation: 25 local audit/parser/transport tests passed. Linux CI repeats these before reading all released parts. No local dependency installation or heavy data processing is performed.

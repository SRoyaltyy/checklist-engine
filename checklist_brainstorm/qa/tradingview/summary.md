# TradingView coverage, draft v8.1 rebuild (21,423 rows): 2026-10-22 ~03:58 HKT
Built by merge_v81.py from source files. 0 duplicate ids. BUT twins kept (3,983 -BUT ids, all with base row; timeframe pilot twins grouped with their base row); signal_group filled on every row (rows without an owner group use their own id).

Inputs: James v5.5e (7,794; 520 never-fire rows excluded), Grok v3f (1,654 main + 64 ratings) + grok-bot-vix-term (156), New Bot v4.4g compact (650), Taskforce v10.5 compact (Drive 1YjNmJTq..., 8,309 minus 20 fails-to-deliver PV-TFC-1001..1020 = 8,289; 35 rows carry `low_info`) + Taskforce timeframe pilot (224, block `timeframe_pilot`, passed Manager Bot retest), Theme Radar compact (2,592). Tag files now read from inbox/tags/.

| owner | rows | pulled | math |
|---|---|---|---|
| Taskforce | 8,513 | 320 (incl. 20 FINRA) | 8,193 (incl. 224 timeframe pilot) |
| James | 7,794 | 746 | 7,048 |
| Theme Radar | 2,592 | 1,460 | 1,132 |
| Grok | 1,874 | 1,525 | 349 |
| New Bot | 650 | 336 | 314 |
| total | 21,423 | 4,387 | 17,036 |

## Holds / flags (row_tags.csv `hold`, `flag`, `low_info`)
- Grok no nightly archive (beta-residual 102, median target chg 112, price vs mean target 112, revenue next-Q revision 112, EPS next-Q revision 112): 550
- Theme Radar market-cap ratios: 154; Finviz Market Cap/Shares Outstanding: 194; skip 08-06/08-10 volume: 386; Finviz Earnings Date unchecked: 40
- newroots rows: 0 in sheet (rule in place: held until 2 clean nightly runs). James new sources (SOFR, reverse repo, auctions, cash balance, yield curve): 0 in sheet (rule in place).
- Rows with any hold: 1,294. FLAGGED: 20 FINRA short volume (PV-TFC-0881..0900). low_info: 35 Taskforce rows (fire >=99%).

## MKT-JA check
All 156 MKT-JA rows (MKT-JA-007...) are identical in id, variant, definition, data type and timeframe to James's VIX term-structure rows in James-removed-v5.5d.csv (the handoff), and none are in v5.5e. Tagged owner Grok (src grok-bot-vix-term.csv), TV M295. None excluded.

## Coverage
second_tag rows (440 Taskforce compact rows, 460 extra tags) counted once under each tagged item, never as extra rows (row_count sum across items 19,964 vs 21,423 rows because off-chart rows are not items).
Items: have 165 with rows / 2 without (M292, M293, off-chart by design). Buildable 0/40, new-data 0/11. M117 now 60 rows; M013, M030, M157, M158 20 each; M272 30; M278 40.
Rows: on chart 19,504, off chart 1,919, untagged 0.

# Grok Bot checklist v3e — changelog (2026-10-22 HKT)
Base: v3e-pre (1,654 main + 64 ratings; previous Drive upload was v3c). Source: Manager Bot final live re-pull (Drive 19jbXdfzYBPeK3caQSj9St9PDXzL2U10h / 1TQ0mDergeaPhxzl8JZHJurc8weJ-2boZ). No sealed buy/sell records touched; old copies kept in qa/old/.
1. CFTC start dates (14 series: BTC x3, VX x3, ES/NQ/RTY/DX commercials, HG/NG/ZC/ZS large spec): already equal to the real first-report dates in the re-pull (fixed in the 1,654 file before upload; v3c had 1986-01-15/2006-06-13). No change needed.
2. Jobless claims, ISM mfg, ISM services, Yahoo VX=F rows: not present in the 1,654 file (already cut after v3c). No change needed.
3. HOLD (not cut) 438 rows on the 4 save_nightly series with no nightly archive: beta-residual sector-future vs stock (102; v3c name "future move minus stock return"), median price target change % (112), price vs mean target (112), revenue next Q revision (112). Notes start with "HOLD=no_nightly_archive".
4. Pin file: 2026-08-06 now rewritten=yes, later sha 94cb047 (2026-08-07 08:57 HKT), later AAPL 312.41 / fwd P/E 32.76 (first commit 6650943 kept as pin: 313.87 / 32.91).
5. Ratings file: 64 ids FV-GB-2449..2518 clashed with main-file ids; renumbered +560 to FV-GB-3009..3078 (BUT-mirror refs updated). Map: grok-bot-ratings.id_map.csv.
Counts: main 1,654 (1,216 active + 438 held), ratings 64, total 1,718 unique ids.

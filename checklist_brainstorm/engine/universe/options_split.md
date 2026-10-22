# 'Options' bucket split, 2024 engine (Grok Bot, 2026-10-22 HKT)

Bucket = regex `option|implied vol|\biv\b|open interest|chain` on source + data_type of merged_draft_v8.2 (reproduces 266 questions / 220 in engine).
Each of the 220 rows was checked on its source and definition. Of their definitions, 0 mention a chain, open interest, put/call, a strike or per-stock IV.

**Result: 0 real options data, 220 volatility index.** All 220 are James's market-wide MKT-JA rows tagged data_type 'Options/vol'. They are the same for every stock on a given day.

| source | class | rows |
|---|---|---|
| CBOE ^OVX | volatility index | 44 |
| CBOE ^VIX3M | volatility index | 44 |
| CBOE ^VIX3M minus ^VIX | volatility index | 44 |
| CBOE ^VIX9D | volatility index | 44 |
| ICE BofA MOVE (Yahoo ^MOVE) | volatility index | 44 |

Examples:
- MKT-JA-1774 (CBOE ^OVX): YES if 1-session change in OVX (oil VIX) (latest value as of yesterday's close or 09:25 ET where noted) >= +1.0 x stdev of its rolling 1-session changes over pr
- MKT-JA-1686 (CBOE ^VIX3M): YES if 1-session change in VIX3M (latest value as of yesterday's close or 09:25 ET where noted) >= +1.0 x stdev of its rolling 1-session changes over prior 252 
- MKT-JA-1708 (CBOE ^VIX3M minus ^VIX): YES if 1-session change in VIX term slope (VIX3M - VIX, pts) (latest value as of yesterday's close or 09:25 ET where noted) >= +1.0 x stdev of its rolling 1-ses
- MKT-JA-1664 (CBOE ^VIX9D): YES if 1-session change in VIX9D (latest value as of yesterday's close or 09:25 ET where noted) >= +1.0 x stdev of its rolling 1-session changes over prior 252 
- MKT-JA-1752 (ICE BofA MOVE (Yahoo ^MOVE)): YES if 1-session change in MOVE index (latest value as of yesterday's close or 09:25 ET where noted) >= +1.0 x stdev of its rolling 1-session changes over prior

The real options sources (DoltHub options, Yahoo chain archive, OI estimate, put/call) are listed in master.csv but are not in the engine.

## All rows
| id              | source                      | class            |
|:----------------|:----------------------------|:-----------------|
| MKT-JA-1752     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1752-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1753     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1753-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1754     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1754-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1755     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1755-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1756     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1756-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1757     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1757-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1758     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1758-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1759     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1759-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1760     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1760-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1761     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1761-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1762     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1762-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1763     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1763-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1764     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1764-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1765     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1765-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1766     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1766-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1767     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1767-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1768     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1768-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1769     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1769-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1770     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1770-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1771     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1771-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1772     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1772-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1773     | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1773-BUT | ICE BofA MOVE (Yahoo ^MOVE) | volatility_index |
| MKT-JA-1774     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1774-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1775     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1775-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1776     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1776-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1777     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1777-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1778     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1778-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1779     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1779-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1780     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1780-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1781     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1781-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1782     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1782-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1783     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1783-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1784     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1784-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1785     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1785-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1786     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1786-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1787     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1787-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1788     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1788-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1789     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1789-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1790     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1790-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1791     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1791-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1792     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1792-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1793     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1793-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1794     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1794-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1795     | CBOE ^OVX                   | volatility_index |
| MKT-JA-1795-BUT | CBOE ^OVX                   | volatility_index |
| MKT-JA-1664     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1664-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1665     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1665-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1666     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1666-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1667     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1667-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1668     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1668-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1669     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1669-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1670     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1670-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1671     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1671-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1672     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1672-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1673     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1673-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1674     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1674-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1675     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1675-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1676     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1676-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1677     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1677-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1678     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1678-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1679     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1679-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1680     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1680-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1681     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1681-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1682     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1682-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1683     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1683-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1684     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1684-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1685     | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1685-BUT | CBOE ^VIX9D                 | volatility_index |
| MKT-JA-1686     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1686-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1687     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1687-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1688     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1688-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1689     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1689-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1690     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1690-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1691     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1691-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1692     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1692-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1693     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1693-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1694     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1694-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1695     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1695-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1696     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1696-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1697     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1697-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1698     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1698-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1699     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1699-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1700     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1700-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1701     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1701-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1702     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1702-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1703     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1703-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1704     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1704-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1705     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1705-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1706     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1706-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1707     | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1707-BUT | CBOE ^VIX3M                 | volatility_index |
| MKT-JA-1708     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1708-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1709     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1709-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1710     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1710-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1711     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1711-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1712     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1712-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1713     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1713-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1714     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1714-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1715     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1715-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1716     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1716-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1717     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1717-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1718     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1718-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1719     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1719-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1720     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1720-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1721     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1721-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1722     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1722-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1723     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1723-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1724     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1724-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1725     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1725-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1726     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1726-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1727     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1727-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1728     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1728-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1729     | CBOE ^VIX3M minus ^VIX      | volatility_index |
| MKT-JA-1729-BUT | CBOE ^VIX3M minus ^VIX      | volatility_index |

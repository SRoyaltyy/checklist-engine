# MONEYFLOW_SOURCE_HUNT_V1

Box-tested 2026-10-30 HKT (James / Grok Bot). Inventory FINAL; download-first. Questions still open.

## Scope (Cyrus 2026-10-30)
Money-flow family means **order/capital flow**, not Chaikin/Twiggs (those are price/volume-derived and already have OHLCV). Target fields: net flow, large vs small orders, block/dark-pool prints, ETF flows, short volume.

## Source table

| Source | What it is | Dates | Fields | PIT | Live-replicable | Status 2026-10-30 |
|---|---|---|---|---|---|---|
| FINRA Reg SHO daily short volume (CNMS + venues) | Per-symbol short vs total volume | **2020-01-02 → 2026-10-29** (CNMS). Prior box parquet ended 2026-10-21; this run appended 10-22..10-29 | short_volume, short_exempt, total_volume, short_ratio | File for day D usable next session | Yes (`cdn.finra.org/equity/regsho/daily/{CNMS,FNSQ,FNYX,FNQC,FNRA,FORF}shvolYYYYMMDD.txt`) | **DOWNLOADED / APPENDED** — box `/workspace/checklist_brainstorm/data/finra_shvol/finra_shvol_{2020..2026}.parquet` + staging `/workspace/options_moneyflow_dl/`; also on release `data-ext-2020-26-v1` (pre-append) |
| FINRA bi-weekly short interest | Exchange-listed SI | Settlement **2020-01-15 → 2026-09-30** (162/162). 2026-10-15 CDN still 403 (not published) | qty, prior, ADV, days_to_cover, publication_date | Join on publication_date < D | Yes (`cdn.finra.org/equity/otcmarket/biweekly/shrtYYYYMMDD.csv`) | **DOWNLOADED** through Sep-30; wait for Oct-15 file |
| FINRA OTC weeklySummary API | ATS / OTC weekly share quantity by participant | Current window (API returns ~200KB) | weekly trade count / share qty | Weekly lag | HTTP 200 from box | **PARTIAL** — useful for dark/ATS flavor; not a full stock-day panel yet |
| ETF.com fund flows page | Issuer flow analytics | Unknown | Flows | Unknown | HTTP 403 / challenge from box | **BLOCKED from box** this run |
| ETFdb category pages | AUM listings | Live | AUM | Live | Timeout/empty this run | **NOT USABLE** this run |
| iShares holdings AJAX | Holdings CSV claim | Live | Holdings | Live | HTTP 200 but HTML shell, not CSV | **FAIL** (known) |
| Futu / Webull capital-flow endpoints | Large/small order flow, block prints (vendor) | Unknown | Net flow, large/small | Unknown | Needs account — **not tested** | **AUTH REQUIRED** |
| Paid dark-pool / block vendors | Full prints | Full | Prints | Vendor | Paid | **Blocked** without Cyrus |

## Note on inventory overlap
- Dictionary **I189** = FINRA daily short volume (already in Phase 1 boxes 1.101–1.105). Treated as the free money-flow backfill that exists today.
- Chaikin money flow / Twiggs / OBV stay under volume indicators (price-derived), not this hunt.

## What was done this run
- Proved FINRA CNMS/FNYX/FORF/… daily short volume HTTP 200 for 2020 and 2026 sample dates.
- Downloaded 36 venue-day files for **2026-10-22..2026-10-29**.
- Append-only extended `finra_shvol_2026.parquet`: **202 dates → 208 dates**, rows **2,371,596 → 2,445,314**, max date **2026-10-29**. Backup: `finra_shvol_2026.parquet.bak_before_1022_append`.
- Confirmed SI through **2026-09-30**; Oct mid-month not published yet.

## Remaining gaps
- Large vs small order flow, block/dark-pool prints at stock-day grain: **no free history found**.
- ETF fund-flow history: no free bulk CSV proven from the box.
- Upload refreshed `finra_shvol_2026.parquet` to release/Drive (large; not committed to git).

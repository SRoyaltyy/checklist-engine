# TODO — per-agent lanes (James maintains; newest state only)

Rules for everyone: work only your lane. Tick an item with proof (run ID or commit on main) — no proof = not done. Delete finished items at next edit; history lives in git, not here. Every item names the Gantt row it advances. Never rewrite sealed buy/sell records. Times in HKT.

Focus now (Cyrus 2026-11-05): **SEC** and **Options** Gantt rows, done by plain scheduled scripts on GitHub runners — no AI calls inside the jobs. Cyrus (09:38 HKT): Venice is a chatbot at its core; keep its scope thin. Hand the real SEC/options download work to GPT as normal code PRs.

---

## Venice
**Lane:** thin chatbot poke only. Keep the Venice AI tab + Tampermonkey/Cloudflare bridge alive so it can notice a broken scheduled job and open a wake / issue. Do **not** own or rewrite the SEC/options download pipelines, do not push new collectors, and do not burn scrape quota on bulk downloads. Calendar work (#96) stays parked.
- [ ] When a `nai-sec-*` or `nai-occ-oi-daily` run fails, post the run ID + error in a PR comment or issue and stop. GPT owns the fix.

## Kimi
**Lane:** strict definitions + v1 master. Definitions only — never data downloads. Do not touch data pipelines. Do the items below strictly in order (Cyrus-approved 2026-11-03 11:21 HKT).
- [x] **1. STOP adding BINARY_MASTER batches.** Held from 2026-11-03 11:21 HKT; last batch 26 (`f756e39d`, 107,201 defs bound). No new batches were pushed while #177 was open.
- [x] **2. Fix PR #177 CI, then merge** → [4 Questions / v1 master]. DONE 2026-11-03 ~12:00 HKT. Merged as `87928850`.
- [x] **3. Then SEC and options strict definitions** → [2 Define / Strict definitions]. DONE 2026-11-07 ~20:05 HKT. PR #210 merged as `230ca55b` (head `1d24d28c`, green CI run **42369998747**): 114 strict defs across 10 blocks + 27 unit tests; canonical grid untouched. Held within item 3 (documented, not blocking): I194 Altman variant (§6.3 ruling), I202 options/money-flow (source authentication).
- [ ] **4. Then ruling parts 5–8** → [2 Define / Strict definitions]. MA30, VWAP anchor, SPY_VIX still held for Cyrus's ruling.

## GPT
**Lane:** (1) finish price world / world gate in order, then (2) take over **SEC + Options no-AI download pipelines** from Venice (Cyrus 2026-11-05). Definitions stay with Kimi. Branch `gpt/*` or continue on open PRs; PR to main.
- [x] **1. Prove world_gate on the #203 price rebuild** → [0 World gate full cohort]. Run **41574830836**; result [`docs/COMPLETED_PRICE_WORLD_GATE_V1.json`](docs/COMPLETED_PRICE_WORLD_GATE_V1.json): **NOT_PROVEN**. Scoring CLOSED.
- [x] **2. Full-cohort price PIT measurement** → [0 World gate full cohort]. Run **41844079765** (attempt1, SUCCESS); exact [`docs/PRICE_FULL_COHORT_PIT_MEASURED_V1.json`](docs/PRICE_FULL_COHORT_PIT_MEASURED_V1.json): **MEASURED, 8,439 names / 12,547,288 setup-day rows**, zero unmeasured names. Full public-bundle/142-receipt readback and preservation of all8,438 retained proof fingerprints/failure vectors PASS. Prefix/alignment PASS; diagnostic packet replay FAIL for1,308 stocks, retained explicitly. Scoring CLOSED. Merged to main as `707760b` in PR #212.
- [x] **3. `available_from` on every price-world column + leak-trap fixes** → [2 Define / available_from], feeds [4 Questions / v1 master]. Run **42249025598**, attempt1, SUCCESS: all **22,968 produced column bindings**, complete retained-source audit, and BPOP/DJCO/KGRN frozen probes with zero differences. Exact [receipt](docs/PRICE_COLUMN_AVAILABILITY_PROOF_V1.json) and [public readback](docs/PRICE_COLUMN_AVAILABILITY_PUBLIC_READBACK_V1.json); PR #214. Columns only; definitions unchanged. Scoring CLOSED.
- [x] **4. Publish the price-world join keys/dates** → [1 Data / SEC + Options joins]. [Guide + metadata](docs/PRICE_WORLD_JOIN_CONTRACT_V1.md), [8,439 ticker keys](dictionary/PRICE_WORLD_JOIN_KEYS_V1.csv) and [9,271 frozen sessions](dictionary/PRICE_WORLD_SESSIONS_V1.csv) verified on main `081eba0` (PR #216), check42252744579 SUCCESS. Observed filing ranges explicit; zero formal ownership intervals, so historical ticker↔CIK joins remain blocked rather than invented. Scoring CLOSED.
- [x] **5. FIX FIRST: SEC 403 on runners** → [1 Data / SEC]. Run **42260180822**, attempt1, SUCCESS: both ticker maps, Form345/13F source indexes and submissions/numeric API samples pass through the verified production relay after the owner-approved SEC-only contact deployment. All24synthetic checks PASS. Exact [public receipt](docs/SEC_RUNNER_ACCESS_SUCCESS_42260180822_V1.json) independently hash-checked; PR #217. Scheduled SEC workflows use this client/relay. Source access only; bulk data and cohort coverage follow in6–7. Scoring CLOSED.
- [ ] **6. SEC tickers + bulk** → [1 Data / SEC / analyst / sector history]. Complete producer **42370671052** SUCCESS:6,446,806filing observations +68,436,577numeric facts, versioned retained raw/parquet assets; identity5,159unique/8,439, facts4,941unique-ticker matches. Missing/empty CIKs and filename-only evidence explicit in [receipt](docs/SEC_BULK_RETAINED_SUCCESS_42370671052_V2.json). Independent all-raw/all-parquet readback **42372758947** is running; keep unchecked until PASS/main proof. Historical ownership remains unproven. Scoring CLOSED.
- [ ] **7. Form 4 + 13F** → same row. SEC Insider Transactions + Form 13F quarterly zips 2020Q1→latest. Fixed-value fields only (buy/sell code, shares, price, dates) — no free text.
- [ ] **8. Options open interest** → [1 Data / Options + money-flow (#165)]. Free daily per-stock OI from runners (OCC / Cboe). Daily cron + backfill; write depth in `docs/OPTIONS_OI_FREE_V1.md`. Also fix `nai-occ-oi-daily` (failed 41906860199 at 04:27 HKT Nov 5).
- [ ] **9. Forward daily collectors** → #165. FINRA daily short volume + CBOE indices, daily cron, append to release assets.
- [ ] **10. Summary doc** `docs/NO_AI_DATA_PIPELINES_V1.md`: each workflow, schedule, latest green run ID, coverage.

## James
**Lane:** coordination, this file, Gantt, reviews/merges, rulings. No competing implementation PRs.
- [ ] Review + merge GPT SEC/options pipeline PRs; regenerate Gantt from main artifacts.
- [ ] Merge viewport #163 once checked.
- [ ] Get Cyrus's ruling on MA30 / VWAP anchor / SPY_VIX.

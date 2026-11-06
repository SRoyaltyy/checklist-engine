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
- [ ] **3. Then SEC and options strict definitions** → [2 Define / Strict definitions] ~45% amber. Binary / fixed-outcome only, no free text. PR #210 (head `a2e20e45`, 114 defs) — finish and merge.
- [ ] **4. Then ruling parts 5–8** → [2 Define / Strict definitions]. MA30, VWAP anchor, SPY_VIX still held for Cyrus's ruling.

## GPT
**Lane:** (1) finish price world / world gate in order, then (2) take over **SEC + Options no-AI download pipelines** from Venice (Cyrus 2026-11-05). Definitions stay with Kimi. Branch `gpt/*` or continue on open PRs; PR to main.
- [x] **1. Prove world_gate on the #203 price rebuild** → [0 World gate full cohort]. Run **41574830836**; result [`docs/COMPLETED_PRICE_WORLD_GATE_V1.json`](docs/COMPLETED_PRICE_WORLD_GATE_V1.json): **NOT_PROVEN**. Scoring CLOSED.
- [x] **2. Full-cohort price PIT measurement** → [0 World gate full cohort]. Run **41844079765** (attempt1, SUCCESS); exact [`docs/PRICE_FULL_COHORT_PIT_MEASURED_V1.json`](docs/PRICE_FULL_COHORT_PIT_MEASURED_V1.json): **MEASURED, 8,439 names / 12,547,288 setup-day rows**, zero unmeasured names. Full public-bundle/142-receipt readback and preservation of all8,438 retained proof fingerprints/failure vectors PASS. Prefix/alignment PASS; diagnostic packet replay FAIL for1,308 stocks, retained explicitly. Scoring CLOSED. Report and recovery summary land together in PR #212; this task is complete on its verified merge to main.
- [ ] **3. `available_from` on every price-world column + leak-trap fixes** → [2 Define / available_from], feeds [4 Questions / v1 master] ~35% amber. Columns only, not definitions.
- [ ] **4. Publish the price-world join keys/dates** the SEC and Options rows will join on (ticker↔CIK date ranges, trading calendar). Done = doc + file on main.
- [ ] **5. FIX FIRST: SEC 403 on runners** → [1 Data / SEC]. Scripts from #208/#209 (`nai-sec-bulk`, `nai-sec-form345`, `nai-sec-form13f`) still 403 on every run (incl. 41906860199 / overnight nai-sec-bulk). Fix User-Agent / egress; prove with a green run. Prefer a scheduled Actions path, not Venice scrapes.
- [ ] **6. SEC tickers + bulk** → [1 Data / SEC / analyst / sector history]. Runners hitting sec.gov (proper User-Agent, ≤10 req/s): `company_tickers.json`, `company_tickers_exchange.json`, `submissions.zip`, `companyfacts.zip`. Filter to `retained_8439` via `docs/SEC_RETAINED_IDENTITY_MAP_V1.json`; parquet release asset; report CIK coverage (now 3,996/8,439).
- [ ] **7. Form 4 + 13F** → same row. SEC Insider Transactions + Form 13F quarterly zips 2020Q1→latest. Fixed-value fields only (buy/sell code, shares, price, dates) — no free text.
- [ ] **8. Options open interest** → [1 Data / Options + money-flow (#165)]. Free daily per-stock OI from runners (OCC / Cboe). Daily cron + backfill; write depth in `docs/OPTIONS_OI_FREE_V1.md`. Also fix `nai-occ-oi-daily` (failed 41906860199 at 04:27 HKT Nov 5).
- [ ] **9. Forward daily collectors** → #165. FINRA daily short volume + CBOE indices, daily cron, append to release assets.
- [ ] **10. Summary doc** `docs/NO_AI_DATA_PIPELINES_V1.md`: each workflow, schedule, latest green run ID, coverage.

## James
**Lane:** coordination, this file, Gantt, reviews/merges, rulings. No competing implementation PRs.
- [ ] Review + merge GPT SEC/options pipeline PRs; regenerate Gantt from main artifacts.
- [ ] Merge viewport #163 once checked.
- [ ] Get Cyrus's ruling on MA30 / VWAP anchor / SPY_VIX.

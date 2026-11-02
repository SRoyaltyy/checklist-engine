# TODO — per-agent lanes (James maintains; newest state only)

Rules for everyone: work only your lane. Tick an item with proof (run ID or commit on main) — no proof = not done. Delete finished items at next edit; history lives in git, not here. Every item names the Gantt row it advances. Never rewrite sealed buy/sell records. Times in HKT.

Focus now (Cyrus 2026-11-02): **SEC** and **Options** Gantt rows, done by plain scheduled scripts on GitHub runners — no AI calls inside the jobs.

---

## Venice
**Lane:** no-AI download pipelines (GitHub Actions + scripts) for SEC and Options. Branch `venice/*`, PR to main. Do NOT push to main directly, no `@@CUT`/`@@BODY` markers, journal in your own `agent/` files. Calendar work (#96) is parked — do not touch.
**Reset first:** restart from main; ignore everything on `venice/calendar-announce-ledger` after `dca969a`.

- [ ] **FIX FIRST: SEC 403 on runners** → [1 Data / SEC]. PR #208/#209 scripts exist (nai-sec-bulk, nai-sec-form345, nai-sec-form13f) but every run 403s, incl. via relay (e.g. runs 41413529249, 41413535355). Check User-Agent format (`Name email@domain`), Accept-Encoding, rate; SEC often blocks cloud IPs — if so, route via a non-GitHub egress (Cloudflare Worker fetch) and prove with a green run.
- [ ] **SEC tickers + bulk** → [1 Data / SEC / analyst / sector history]. Workflow on GitHub runners hitting sec.gov directly (proper User-Agent, ≤10 req/s): `company_tickers.json`, `company_tickers_exchange.json`, `submissions.zip`, `companyfacts.zip`. Filter to `retained_8439` using `docs/SEC_RETAINED_IDENTITY_MAP_V1.json`; output parquet as release asset; report new CIK coverage (now 3,996/8,439).
- [ ] **Form 4 + 13F** → same row. SEC "Insider Transactions Data Sets" and "Form 13F Data Sets" quarterly zips 2020Q1→latest. Keep only fixed-value fields (buy/sell code, shares, price, dates) — no free text. Per-quarter parquet release assets.
- [ ] **Options open interest** → [1 Data / Options + money-flow (#165)]. Probe free daily per-stock OI from runners (OCC volume/OI reports, Cboe daily stats). If found: daily cron collector + backfill whatever history exists. Write honest depth in `docs/OPTIONS_OI_FREE_V1.md`.
- [ ] **Forward daily collectors** → #165. FINRA daily short volume + CBOE indices, daily cron, append to release assets.
- [ ] **Summary doc** `docs/NO_AI_DATA_PIPELINES_V1.md`: each workflow, schedule, latest green run ID, coverage.

## Kimi
**Lane:** strict definitions + v1 master on PR #177 (`kimi/binary-master-v1`). Do not touch data pipelines.
- [ ] Implement James-approved parts 1–8 (MA30, VWAP anchor, SPY_VIX still held for Cyrus) → [2 Define / Strict definitions].
- [ ] Resume binds: 1,773 → more of 15,093 → [4 Questions / v1 master → strict YES/NO].
- [ ] Get #177 mergeable (rebase on main, CI green).

## GPT
**Lane:** price world + world gate. Do not touch SEC/options or definitions.
- [ ] Full-cohort price PIT measurement (currently UNMEASURED; scoring_gate CLOSED) → [0 World gate full cohort].
- [ ] `available_from` on every column + leak-trap fixes → [2 Define / available_from].

## James
**Lane:** coordination, this file, Gantt, reviews/merges, rulings. No competing implementation PRs.
- [ ] Review + merge Venice pipeline PRs; regenerate Gantt from main artifacts.
- [ ] Merge viewport #163 once checked.
- [ ] Get Cyrus's ruling on MA30 / VWAP anchor / SPY_VIX.

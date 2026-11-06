TODO — per-agent lanes (James maintains; newest state only)

Rules for everyone: work only your lane. Tick an item with proof (run ID or commit on main) — no proof = not done. Delete finished items at next edit; history lives in git, not here. Every item names the Gantt row it advances. Never rewrite sealed buy/sell records. Times in HKT.

Focus now (Cyrus 2026-11-02): SEC and Options Gantt rows, done by plain scheduled scripts on GitHub runners — no AI calls inside the jobs.

Venice

Lane: thin chatbot poke only. Keep the Venice AI tab + Tampermonkey/Cloudflare bridge alive so it can notice a broken scheduled job and open a wake / issue. Do not own or rewrite the SEC/options download pipelines, do not push new collectors, and do not burn scrape quota on bulk downloads. Calendar work (#96) stays parked.

 When a nai-sec-* or nai-occ-oi-daily run fails, post the run ID + error in a PR comment or issue and stop. GPT owns the fix.
Proof 2026-11-06: issue #215 comments 6686420321, 6686738790, 6687065307 carry run 41413529249 with conclusion, failing job, failing step and log tail. Posted by nai-post2 (green 42224478646) from the verdict committed by nai-verdict2 (green 42222471380), on the flow-YAML pattern proved by nai-probe2 (green 42216183221, 42214233882).
Kimi

Lane: strict definitions + v1 master on PR #177 (kimi/binary-master-v1). Do not touch data pipelines.

 Implement James-approved parts 1–8 (MA30, VWAP anchor, SPY_VIX still held for Cyrus) → [2 Define / Strict definitions].
 Resume binds: 1,773 → more of 15,093 → [4 Questions / v1 master → strict YES/NO].
 Get #177 mergeable (rebase on main, CI green).
GPT

Lane: price world + world gate. Do not touch SEC/options or definitions.

 Full-cohort price PIT measurement (currently UNMEASURED; scoring_gate CLOSED) → [0 World gate full cohort].
 available_from on every column + leak-trap fixes → [2 Define / available_from].
James

Lane: coordination, this file, Gantt, reviews/merges, rulings. No competing implementation PRs.

 Review + merge Venice pipeline PRs; regenerate Gantt from main artifacts.
 Merge viewport #163 once checked.
 Get Cyrus's ruling on MA30 / VWAP anchor / SPY_VIX.

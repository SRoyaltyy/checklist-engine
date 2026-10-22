#!/usr/bin/env python3
"""Pull DoltHub post-no-preference/options volatility_history via web SQL API, one date at a time, paged 1000 rows.
2020-2024 ONLY (2025-26 deliberately not pulled: blind holdout). Writes raw/vh_{y}.parquet. Survivors-only caveat: pre-2021-04-20 rows are a backfill."""
import sys, json, time, urllib.request, urllib.parse, pandas as pd
API = "https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master"
def q(sql, tries=6):
    for k in range(tries):
        try:
            u = API + "?" + urllib.parse.urlencode({"q": sql})
            j = json.load(urllib.request.urlopen(u, timeout=120))
            if j.get("query_execution_status") == "Success": return j["rows"]
            print("ERR", j.get("query_execution_message"), flush=True)
        except Exception as e: print("EXC", e, flush=True)
        time.sleep(5 * (k + 1))
    raise RuntimeError(sql)
y = int(sys.argv[1]); assert 2020 <= y <= 2024
dates = pd.date_range(f"{y}-01-01", f"{y}-12-31").strftime("%Y-%m-%d")
out = []; t0 = time.time(); nd = 0
for i, d in enumerate(dates):
    rows = []; off = 0
    while True:
        r = q(f"SELECT * FROM volatility_history WHERE date='{d}' ORDER BY act_symbol LIMIT 1000 OFFSET {off}")
        rows += r; off += 1000
        if len(r) < 1000: break
    if rows: out.append(pd.DataFrame(rows)); nd += 1
    if i % 30 == 0: print(y, i, d, len(rows), nd, f"{time.time()-t0:.0f}s", flush=True)
df = pd.concat(out); 
for col in df.columns:
    if col not in ("date", "act_symbol") and not col.endswith("_date"): df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
df.to_parquet(f"raw/vh_{y}.parquet", index=False); print("DONE", y, len(df), f"{time.time()-t0:.0f}s", flush=True)

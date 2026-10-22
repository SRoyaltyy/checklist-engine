#!/usr/bin/env python3
"""Pull DoltHub volatility_history 2020-2024 ONLY. Resume-safe; SSL backoff; checkpoint every 15 dates with data."""
import sys, json, time, urllib.request, urllib.parse, os, atexit, pandas as pd
API = "https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master"
def q(sql, tries=8):
    for k in range(tries):
        try:
            u = API + "?" + urllib.parse.urlencode({"q": sql})
            j = json.load(urllib.request.urlopen(u, timeout=90))
            if j.get("query_execution_status") == "Success": return j["rows"]
            print("ERR", j.get("query_execution_message"), flush=True)
        except Exception as e:
            print("EXC try", k+1, e, flush=True)
        time.sleep(min(60, 3 * (2 ** k)))
    raise RuntimeError(sql)
y = int(sys.argv[1]); assert 2020 <= y <= 2024
path = f"raw/vh_{y}.parquet"; os.makedirs("raw", exist_ok=True)
have = set(); prev = None
if os.path.exists(path):
    prev = pd.read_parquet(path); have = set(prev.date.astype(str).unique())
    print(f"RESUME {y}: {len(have)} dates ({len(prev)} rows)", flush=True)
dates = pd.date_range(f"{y}-01-01", f"{y}-12-31").strftime("%Y-%m-%d")
buf = []; t0 = time.time(); nd = len(have); since_ckpt = 0
def flush():
    global prev, buf, since_ckpt
    if not buf: return
    chunk = pd.concat(buf, ignore_index=True)
    prev = pd.concat([prev, chunk], ignore_index=True) if prev is not None else chunk
    prev.to_parquet(path, index=False)
    print(f"CHECKPOINT {y} dates={prev.date.nunique()} rows={len(prev)}", flush=True)
    buf = []; since_ckpt = 0
atexit.register(flush)
for i, d in enumerate(dates):
    if d in have:
        if i % 30 == 0: print(y, i, d, "SKIP", nd, f"{time.time()-t0:.0f}s", flush=True)
        continue
    t1 = time.time(); rows = []; off = 0
    while True:
        r = q(f"SELECT * FROM volatility_history WHERE date='{d}' ORDER BY act_symbol LIMIT 1000 OFFSET {off}")
        rows += r; off += 1000
        if len(r) < 1000: break
    if rows:
        df = pd.DataFrame(rows)
        for col in df.columns:
            if col not in ("date", "act_symbol") and not col.endswith("_date"):
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
        buf.append(df); nd += 1; have.add(d); since_ckpt += 1
    if i % 10 == 0 or rows:
        print(y, i, d, len(rows), nd, f"{time.time()-t0:.0f}s (+{time.time()-t1:.1f}s)", flush=True)
    if since_ckpt >= 15: flush()
flush()
print("DONE", y, 0 if prev is None else len(prev), f"{time.time()-t0:.0f}s", flush=True)

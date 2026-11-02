"""Daily OCC open-interest snapshot (no AI). OCC series-search gives CURRENT per-series OI only (no history).
Collect for retained cohort names that OCC lists as optionable. Output -> release nai-occ-oi-daily-v1, one parquet per OCC date."""
import datetime as dt, os, re, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import get, cohort, ensure_release, assets, upload

TAG = "nai-occ-oi-daily-v1"; BROWSER = "Mozilla/5.0 (checklist-engine research cyrus-checklist@users.noreply.github.com)"
lim = int(os.environ.get("OCC_LIMIT", "0"))
delo = get("https://marketdata.theocc.com/delo-download?prodType=ALL&downloadFields=OS;US;SN&format=txt", ua=BROWSER).decode("latin1")
und = {l.split("\t")[1].strip() for l in delo.splitlines() if l.count("\t") >= 2}
names = [t for t in cohort() if t.replace("-", ".") in und or t in und]
if lim: names = names[:lim]
print("optionable cohort names:", len(names), flush=True)
day = dt.datetime.utcnow().strftime("%Y%m%d"); asset = f"occ_oi_{day}.parquet"
ensure_release(TAG, "No-AI OCC daily open interest v1")
if asset in assets(TAG) and not lim:
    print("already have", asset); sys.exit(0)
rows, fails = [], 0
pat = re.compile(r"^(\S+)\s+(\d{4})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+[CP ]+\s+(\d+)\s+(\d+)")
for i, t in enumerate(names):
    try:
        txt = get(f"https://marketdata.theocc.com/series-search?symbolType=U&symbol={t.replace('-', '.')}", ua=BROWSER, pace=0.35, tries=3, timeout=60).decode("latin1")
    except Exception:
        fails += 1; continue
    for l in txt.splitlines():
        m = pat.match(l.strip())
        if m:
            p, y, mo, d, si, sd, c, pu = m.groups()
            rows.append((t, p, f"{y}-{int(mo):02d}-{int(d):02d}", float(f"{si}.{sd}"), int(c), int(pu)))
    if i % 500 == 0: print(i, len(rows), flush=True)
df = pd.DataFrame(rows, columns=["ticker", "product", "expiry", "strike", "call_oi", "put_oi"]); df["snapshot_utc"] = day
p = f"occ_oi_{day}{'_test' if lim else ''}.parquet"; df.to_parquet(p, compression="zstd", index=False); upload(TAG, p)
print({"names": len(names), "fails": fails, "series": len(df), "tickers_with_rows": df.ticker.nunique()})

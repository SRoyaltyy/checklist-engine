"""Daily forward collectors (no AI): FINRA Reg SHO daily short volume (CNMS) + Cboe index daily history CSVs.
FINRA: backfills any missing trading days in the last 30 calendar days (resumable). Output -> release nai-daily-forward-v1."""
import datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get, ensure_release, assets, upload
TAG = "nai-daily-forward-v1"; ensure_release(TAG, "No-AI daily forward collectors v1"); have = assets(TAG)
today = dt.date.today(); got = []
for k in range(int(os.environ.get("FINRA_DAYS", "30"))):
    d = today - dt.timedelta(days=k)
    if d.weekday() >= 5: continue
    n = f"finra_CNMSshvol{d:%Y%m%d}.txt"
    if n in have: continue
    try:
        get(f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{d:%Y%m%d}.txt", n, tries=2)
    except Exception as e:
        print("no file", d, e); continue
    upload(TAG, n); got.append(n)
for ix in ["VIX", "VIX9D", "VIX3M", "VIX6M", "VIX1Y", "VVIX", "SKEW", "OVX", "GVZ", "VXN", "RVX"]:
    n = f"cboe_{ix}_History.csv"
    try:
        get(f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{ix}_History.csv", n, ua="Mozilla/5.0", tries=2); upload(TAG, n); got.append(n)
    except Exception as e:
        print("cboe fail", ix, e)
print("uploaded", got)

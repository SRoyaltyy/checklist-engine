"""Fetch split events + monthly split-adjusted closes from Yahoo chart API for every release-universe
ticker (cache, resumable). Same output schema as fetch_yahoo.py, but reads the universe from the
data release (CHECKLIST_DATA_DIR) instead of the hardcoded /workspace path, so it runs on any box.
Split dates are corporate-action metadata used only by mcap_fix.py (see METHODOLOGY house rules)."""
import json, os, sys, time, urllib.request, concurrent.futures as cf, pandas as pd

DD = os.environ.get('CHECKLIST_DATA_DIR', '.')
tk = sorted(pd.read_parquet(f'{DD}/universe_2020_survivors_le2024.parquet', columns=['ticker']).ticker.astype(str).unique())
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yraw')
os.makedirs(out, exist_ok=True)

def get(t):
    p = f'{out}/{t}.json'
    if os.path.exists(p):
        return t, 'cached'
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{t.replace('.', '-')}?period1=1514764800&period2=1798761600&interval=1mo&events=split"
    for k in range(4):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20))
            json.dump(r, open(p, 'w')); return t, 'ok'
        except urllib.error.HTTPError as e:
            if e.code == 404: json.dump({'err': 404}, open(p, 'w')); return t, '404'
            time.sleep(2 + 3*k)
        except Exception:
            time.sleep(2 + 3*k)
    return t, 'fail'

with cf.ThreadPoolExecutor(12) as ex:
    res = list(ex.map(get, tk))
print(pd.Series([r[1] for r in res]).value_counts().to_dict())

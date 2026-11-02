"""Probe free options open-interest sources from a GitHub runner (no AI). Writes OI_SOURCE_PROBE.json."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import get, ensure_release, upload, UA
B = "Mozilla/5.0 (checklist-engine research cyrus-checklist@users.noreply.github.com)"
P = {"occ_series_search_current": "https://marketdata.theocc.com/series-search?symbolType=U&symbol=AAPL",
     "occ_delo_product_list": "https://marketdata.theocc.com/delo-download?prodType=ALL&downloadFields=OS;US;SN&format=txt",
     "occ_volume_query_daily": "https://marketdata.theocc.com/volume-query?reportDate=20200102&format=csv&volumeQueryType=O&symbolType=U&symbol=AAPL&reportType=D&accountType=ALL&productKind=ALL&porc=BOTH",
     "occ_oi_historical_guess": "https://marketdata.theocc.com/oi-query?reportDate=20200102&symbol=AAPL&format=csv",
     "cboe_delayed_chain_current": "https://cdn.cboe.com/api/global/delayed_quotes/options/AAPL.json",
     "cboe_daily_market_stats": "https://www.cboe.com/us/options/market_statistics/daily/?dt=2020-01-02",
     "nasdaq_option_chain_current": "https://api.nasdaq.com/api/quote/AAPL/option-chain?assetclass=stocks&limit=5",
     "sec_company_tickers": "https://www.sec.gov/files/company_tickers.json"}
out = {}
for k, u in P.items():
    try:
        b = get(u, ua=(UA if "sec.gov" in u else B), tries=2, timeout=40)
        out[k] = {"url": u, "ok": True, "bytes": len(b), "head": b[:300].decode("latin1"), "has_open_interest": b"pen" in b and b"nterest" in b or b"open_interest" in b}
    except Exception as e:
        out[k] = {"url": u, "ok": False, "err": str(e)[:300]}
    print(k, out[k].get("ok"), out[k].get("bytes"), flush=True)
json.dump(out, open("OI_SOURCE_PROBE.json", "w"), indent=1)
ensure_release("nai-occ-oi-daily-v1", "No-AI OCC daily open interest v1"); upload("nai-occ-oi-daily-v1", "OI_SOURCE_PROBE.json")

"""Inspect existing org prices and verified halt events for unresolved price names."""
import hashlib,io,json,urllib.request
from pathlib import Path
import pandas as pd
TICKERS=["ACA","ACVA","ATKR","AXG","AZTR","BDRX","BLFS","BTF","BZH","CCO","COCH","CYCN","GCTK","HCTI","IAE","IHD","IPW","LBRDA","LPSN","MUSQ","PERF","PPCB","PSKY","QNCX","QRVO","SBFM","SLP","SXTC","TWG","UUU","VTAK","WBD"]
URL='https://raw.githubusercontent.com/SRoyaltyy/fullscan/cc932d413b78dbd375f78aa99229da46752e9ac8/data/prices/ohlc.parquet'
EXPECTED='31e6bf7f5a9054080123dff90a2f36d38e080d6ead72c6cfbb7752d959470cca'
def main():
    out=Path('price-gap-probe');out.mkdir(exist_ok=True)
    with urllib.request.urlopen(URL,timeout=180) as response:raw=response.read()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=EXPECTED:raise ValueError('Existing fullscan price source changed')
    prices=pd.read_parquet(io.BytesIO(raw));prices['date']=pd.to_datetime(prices.date)
    selected=prices[prices.ticker.isin(TICKERS)&(prices.date<=pd.Timestamp('2026-10-23'))].copy()
    selected.to_parquet(out/'fullscan_price_gap_candidates.parquet',index=False)
    halts=pd.read_parquet('nasdaq_halts_2020_2026.parquet');records=[]
    for ticker in TICKERS:
        frame=selected[selected.ticker==ticker].sort_values('date');events=halts[halts.symbol==ticker].copy()
        records.append(dict(ticker=ticker,existing_source_rows=len(frame),first=str(frame.date.min())[:10] if len(frame) else None,last=str(frame.date.max())[:10] if len(frame) else None,latest_rows=frame.tail(3).astype({'date':str}).to_dict('records'),halt_events=events.astype(str).tail(5).to_dict('records'),used_as_replacement=False))
    report=dict(source=URL,source_sha256=digest,source_rows=len(prices),original_columns=list(prices),halt_source_columns=list(halts),halt_source_sha256=hashlib.sha256(Path('nasdaq_halts_2020_2026.parquet').read_bytes()).hexdigest(),records=records,scope='Independent source inspection only; no inferred delisting, forward fill or accepted price replacement')
    (out/'PRICE_GAP_SOURCE_PROBE.json').write_text(json.dumps(report,indent=2))
    print('PRICE_GAP_SOURCE_PROBE',json.dumps(report),flush=True)
if __name__=='__main__':main()

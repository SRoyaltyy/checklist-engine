"""Measure the existing fullscan price asset against the frozen checklist bars.
This audit writes evidence only; it cannot replace either input or approve P1.
"""
import argparse,hashlib,json,urllib.request
from pathlib import Path
from collections import Counter
import pandas as pd
import numpy as np
from price_reconcile import reconcile_one


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--frozen',required=True);ap.add_argument('--commit',required=True)
    ap.add_argument('--expected-blob',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    url=f'https://raw.githubusercontent.com/SRoyaltyy/fullscan/{a.commit}/data/prices/ohlc.parquet'
    target=out/'existing_ohlc.parquet'
    urllib.request.urlretrieve(url,target)
    data=target.read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(data)).encode()+bytes([0])+data).hexdigest()
    if blob!=a.expected_blob:raise ValueError('existing price blob differs from inspected source')
    report=dict(status='PROVISIONAL_SOURCE_AUDIT',url=url,git_blob=blob,sha256=hashlib.sha256(data).hexdigest())
    del data
    new=pd.read_parquet(target).reset_index()
    report['original_columns']=list(new.columns)
    names={c:str(c).lower() for c in new.columns}
    new=new.rename(columns=names)
    if 'ticker' not in new and 'symbol' in new:new=new.rename(columns={'symbol':'ticker'})
    needed=['ticker','date','open','high','low','close','volume']
    if not set(needed)<=set(new):
        report.update(error='unrecognized OHLCV schema; source not joined',missing=sorted(set(needed)-set(new)))
    else:
        new=new[needed].copy();new['date']=pd.to_datetime(new.date).astype('datetime64[ns]')
        new['ticker']=new.ticker.astype(str)
        report.update(rows=len(new),tickers=new.ticker.nunique(),date_min=str(new.date.min()),date_max=str(new.date.max()),
            rows_2025_2026=int(new.date.dt.year.isin([2025,2026]).sum()),duplicate_keys=int(new.duplicated(['ticker','date']).sum()))
        old=pd.read_parquet(a.frozen,columns=needed)
        old['date']=pd.to_datetime(old.date).astype('datetime64[ns]')
        wanted=set(old.ticker);available=set(new.ticker)
        report['frozen_tickers']=len(wanted);report['missing_frozen_tickers']=sorted(wanted-available)
        groups={str(t):g for t,g in new.groupby('ticker',sort=False)}
        results=[]
        for ticker,frozen in old.groupby('ticker',sort=True):
            if str(ticker) not in groups:continue
            try:
                _,evidence=reconcile_one(str(ticker),frozen,groups[str(ticker)])
                results.append(evidence)
            except Exception as exc:results.append(dict(ticker=str(ticker),status='FAIL',error=str(exc)))
        report['overlap_status_counts']=dict(Counter(x['status'] for x in results))
        report['reconciliations']=results
        report['nominal_historical_price_verified']=False
        report['full_world_coverage_approved']=False
    (out/'EXISTING_PRICE_AUDIT.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('reconciliations','missing_frozen_tickers')}),flush=True)
    target.unlink()


if __name__=='__main__':main()

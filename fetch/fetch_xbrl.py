"""PIT XBRL extraction from SEC companyfacts, preserving every filing version.

Frames select the last-filed value and do not supply the filing-version history
needed for this backtest. A missing companyfacts endpoint (404) is logged as
unavailable; HTTP/auth/server failures are errors, never a successful empty fetch.
https://www.sec.gov/search-filings/edgar-application-programming-interfaces
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

SEC_HEADERS = {'User-Agent': 'checklist-engine research https://github.com/SRoyaltyy/checklist-engine'}
CONCEPTS = ['Revenues','RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet',
 'NetIncomeLoss','OperatingIncomeLoss','GrossProfit','Assets','AssetsCurrent',
 'Liabilities','LiabilitiesCurrent','StockholdersEquity','LongTermDebt','LongTermDebtNoncurrent',
 'DebtCurrent','CashAndCashEquivalentsAtCarryingValue','CommonStockSharesOutstanding',
 'EarningsPerShareBasic','EarningsPerShareDiluted','ResearchAndDevelopmentExpense',
 'NetCashProvidedByUsedInOperatingActivities','CostOfRevenue','AccountsReceivableNetCurrent',
 'InventoryNet','PropertyPlantAndEquipmentNet','PaymentsToAcquirePropertyPlantAndEquipment']
COLUMNS = ['ticker','metric','source_metric','unit','period_start','period_end','filed','accn','form','val','yoy']
ALIASES = {'RevenueFromContractWithCustomerExcludingAssessedTax':'Revenues','SalesRevenueNet':'Revenues'}


def get_json(url, retries=4, allow_404=False):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=SEC_HEADERS),timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and allow_404:
                print('SKIP_404',url,flush=True)
                return None
            if exc.code not in (429,500,502,503,504) or attempt == retries-1:
                raise
        except (OSError,TimeoutError):
            if attempt == retries-1:
                raise
        time.sleep(2**attempt)
    raise RuntimeError('HTTP retry loop exhausted')


def company_rows(ticker, payload, concepts=CONCEPTS):
    rows = []
    facts = payload.get('facts',{})
    for taxonomy in ('us-gaap','dei'):
        for concept,data in facts.get(taxonomy,{}).items():
            if concept not in concepts:
                continue
            for unit,items in data.get('units',{}).items():
                if unit not in ('USD','shares','USD/shares'):
                    continue
                for item in items:
                    if not all(item.get(k) is not None for k in ('filed','end','val','accn')):
                        continue
                    if item.get('form') not in ('10-K','10-Q','10-K/A','10-Q/A','20-F','20-F/A','40-F','6-K'):
                        continue
                    rows.append(dict(ticker=ticker,metric=ALIASES.get(concept,concept),source_metric=concept,
                                     unit=unit,period_start=item.get('start'),period_end=item['end'],
                                     filed=item['filed'],accn=item['accn'],form=item['form'],val=float(item['val'])))
    return rows


def add_yoy(frame):
    """Only compare a prior-year fact that was public by this fact's filing date.
    Future restatements cannot change an earlier growth observation. Keep
    annual / quarterly / cumulative durations distinct.
    """
    frame = frame.copy()
    frame['yoy'] = np.nan
    for (_,metric),group in frame.groupby(['ticker','metric']):
        if metric not in ('Revenues','NetIncomeLoss'):
            continue
        ends = pd.to_datetime(group.period_end)
        starts = pd.to_datetime(group.period_start)
        durations = (ends-starts).dt.days
        filed = pd.to_datetime(group.filed)
        for idx,row in group.iterrows():
            end = pd.Timestamp(row.period_end)
            duration = (end-pd.Timestamp(row.period_start)).days
            target = end-pd.DateOffset(years=1)
            eligible = group[(abs((ends-target).dt.days)<=7)&
                             (abs(durations-duration)<=14)&(filed<=pd.Timestamp(row.filed))]
            if not len(eligible):
                continue
            prior = eligible.sort_values(['filed','accn']).iloc[-1].val
            if prior != 0:
                frame.loc[idx,'yoy'] = (row.val-prior)/abs(prior)
            elif row.val > 0:
                frame.loc[idx,'yoy'] = np.inf
    return frame


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--universe',required=True)
    ap.add_argument('--out',default='xbrl_out')
    ap.add_argument('--shard',type=int,default=0)
    ap.add_argument('--shards',type=int,default=8)
    ap.add_argument('--count',type=int,default=0)
    ap.add_argument('--resume',action='store_true')
    args=ap.parse_args()
    output=Path(args.out);output.mkdir(parents=True,exist_ok=True)
    target=output/f'xbrl_shard_{args.shard:03d}.parquet'
    progress=target.with_suffix('.progress.json')
    tickers=sorted(pd.read_parquet(args.universe,columns=['ticker']).ticker.unique())[args.shard::args.shards]
    if args.count: tickers=tickers[:args.count]
    mapping=get_json('https://www.sec.gov/files/company_tickers.json')
    cik_of={v['ticker'].upper().replace('-','.'):int(v['cik_str']) for v in mapping.values()}
    rows=[];done={};errors={}
    if args.resume and target.exists() and progress.exists():
        rows=pd.read_parquet(target).drop(columns='yoy',errors='ignore').to_dict('records')
        done=json.loads(progress.read_text()).get('done',{})
    def checkpoint():
        frame=pd.DataFrame(rows,columns=COLUMNS[:-1])
        frame=frame.drop_duplicates(['ticker','source_metric','unit','period_start','period_end','filed','accn'])
        frame=add_yoy(frame)
        frame.to_parquet(str(target)+'.tmp',index=False);os.replace(str(target)+'.tmp',target)
        progress.write_text(json.dumps(dict(done=done,errors=errors,requested=len(tickers),rows=len(frame)),indent=2))
    for i,ticker in enumerate(tickers):
        if ticker in done: continue
        cik=cik_of.get(ticker.upper().replace('-','.'))
        if cik is None:
            done[ticker]='NO_CIK'
        else:
            try:
                payload=get_json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',allow_404=True)
                batch=company_rows(ticker,payload) if payload else []
                rows.extend(batch)
                done[ticker]='OK' if batch else 'NO_FACTS'
            except Exception as exc:
                errors[ticker]=f'{type(exc).__name__}: {exc}'
        if (i+1)%25==0: checkpoint()
        time.sleep(1.0)  # eight shards share SEC's account/IP fair-use budget
    checkpoint()
    print(json.dumps(dict(file=str(target),rows=len(rows),done=len(done),errors=len(errors))),flush=True)
    if errors: raise SystemExit(1)

if __name__=='__main__': main()

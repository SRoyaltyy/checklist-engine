"""Rebuild every v2 column under future truncation; no sampled columns.
This verifies supplied inputs, not data blocks absent from them. Missing blocks
are separately rejected by the coverage gate.
"""
import argparse,json,copy
from pathlib import Path
import numpy as np
import pandas as pd
import facets_world as fw
from world_snapshot_v2 import context,ticker_snapshot,load_reconciled_bars


def before(frame,column,day,inclusive=False):
    if frame is None:return None
    values=pd.to_datetime(frame[column])
    return frame[values<=day if inclusive else values<day].copy()


def truncate_context(ctx,day):
    result=ctx.copy()
    # ETF date labels already carry a one-session shift (availability dates).
    result['etf']=before(ctx['etf'],'date',day,inclusive=True)
    result['breadth']=before(ctx['breadth'],'date',day)
    for key,column in [('earnings','report_date'),('an','date'),('xb','filed'),('gd','date'),('f13','file_date')]:
        result[key]={ticker:before(frame,column,day) for ticker,frame in ctx[key].items()}
    result['mkt']=before(ctx['mkt'],'date',day)
    result['fred']=before(ctx['fred'],'vintage_date',day)
    from world_fred import compile_timelines
    result['fred_timelines']=compile_timelines(result['fred'])  # independent truncated rebuild; never reuse the full cache
    dates={'si':'publication_date','shvol':'date','regsho':'date','halts':'halt_d','divs':'date','splits':'date','f4':'date'}
    result['ext']={ticker:{block:before(frame,dates[block],day) for block,frame in blocks.items()} for ticker,blocks in ctx['ext'].items()}
    if ctx['peers'] is not None:
        result['peers']=copy.copy(ctx['peers'])
        result['peers'].cluster_ret=before(ctx['peers'].cluster_ret,'date',day)
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tickers',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--supplemental-prices',default='')
    args=ap.parse_args();tickers=set(args.tickers.split(','));ctx=context(tickers,args.supplemental_prices)
    bars,_=load_reconciled_bars(tickers,args.supplemental_prices);checks=[];columns=set();bad=[]
    for ticker,frame in bars.groupby('ticker'):
        frame=frame.sort_values('date').reset_index(drop=True)
        full=ticker_snapshot(ticker,frame,ctx).set_index('date')
        # Include year boundaries and both candle-group and ordinary cut dates.
        selected=[]
        for year in range(2020,2027):
            positions=frame.index[(frame.date.dt.year==year)]
            for offset in (0,9,20,61):
                if len(positions)>offset:selected.append(int(positions[offset]))
        for position in selected:
            day=pd.Timestamp(frame.date.iloc[position])
            prefix=frame.iloc[:position+1]
            cut=ticker_snapshot(ticker,prefix,truncate_context(ctx,day)).set_index('date')
            left=full.loc[day].drop(labels=['ticker']);right=cut.loc[day].drop(labels=['ticker'])
            missing=sorted(set(left.index)-set(right.index))
            # Before a feed starts, its declared columns must remain unavailable
            # rather than materializing a fake zero. Account for every full column.
            right=right.reindex(left.index)
            a=left.to_numpy(float);b=right.to_numpy(float)
            equal=np.isclose(a,b,rtol=1e-6,atol=1e-7,equal_nan=True)
            failed=left.index[~equal].tolist();bad.extend(f'{ticker}:{day.date()}:{c}' for c in failed)
            columns.update(left.index)
            checks.append(dict(ticker=ticker,date=str(day.date()),columns=len(left),mismatches=failed,
                               unavailable_in_prefix=missing))
        print('LEAK_TICKER',ticker,'checks',len(selected),flush=True)
    summary=dict(status='FAIL' if bad or not checks else 'PASS',unique_columns=len(columns),
        comparisons=sum(x['columns'] for x in checks),cut_points=len(checks),mismatches=bad,checks=checks,
        scope='all supplied v2 columns; absent blocks remain coverage failures')
    Path(args.out).write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k not in ('checks','mismatches')}),flush=True)
    if bad or not checks:raise SystemExit(1)

if __name__=='__main__':main()

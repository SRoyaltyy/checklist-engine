"""Bounded offline diagnosis of the pinned M217 loop, never replacement values."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import talib


def diagnose(bars,limit=100000):
    if type(limit) is not int or limit<1:raise ValueError('diagnostic step limit must be positive')
    if not {'date','high','low','close'}<=set(bars) or bars.empty:raise ValueError('diagnostic requires nonempty dated HLC')
    dates=pd.DatetimeIndex(pd.to_datetime(bars.date))
    if dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:raise ValueError('diagnostic dates must be ordered and unique')
    c=bars.close.to_numpy(dtype='float64')
    atr=talib.ATR(bars.high.to_numpy(dtype='float64'),bars.low.to_numpy(dtype='float64'),c,timeperiod=14)
    last=c[0];count=0;problem=None;started=time.perf_counter()
    for t in range(1,len(c)):
        box=atr[t] if not np.isnan(atr[t]) and atr[t]>0 else 0.
        if box<=0:continue
        for sign in (1.,-1.):
            while c[t]>=last+box if sign>0 else c[t]<=last-box:
                following=last+box if sign>0 else last-box
                if following==last or count>=limit:
                    problem=dict(index=t,date=str(dates[t].date()),close=float(c[t]),atr14=float(box),
                                 last_brick=float(last),next_brick=float(following),
                                 stalled_float_addition=bool(following==last),ulp_at_last=float(abs(np.spacing(last))),
                                 estimated_remaining_bricks=float(abs(c[t]-last)/box),
                                 reason='FLOAT_STEP_CANNOT_ADVANCE' if following==last else 'BOUNDED_STEP_PROBE_LIMIT')
                    break
                last=following;count+=1
            if problem:break
        if problem:break
    return dict(status='READ_ONLY_BOUNDED_RENKO_DIAGNOSIS_NOT_A_VALUE_REPLACEMENT',input_rows=len(bars),
                exact_probe_brick_steps=count,probe_seconds=time.perf_counter()-started,first_problem=problem,
                replacement_numeric_values=False,world_gate='NOT_PROVEN',scoring_gate='CLOSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bars',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--limit',type=int,default=100000)
    args=parser.parse_args();raw=args.bars.read_bytes();report=diagnose(pd.read_parquet(args.bars),args.limit)
    report['raw_member_sha256']=hashlib.sha256(raw).hexdigest();report['raw_member_bytes']=len(raw)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

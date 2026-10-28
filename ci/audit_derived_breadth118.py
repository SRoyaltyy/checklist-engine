"""Offline read-only reproduction of the pinned derived-breadth118 findings.

Requires git object93d7393 and the three immutable public input files.
Run with PYTHONPATH=. from the repository; no provider or workflow action.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import types

import numpy as np
import pandas as pd
from world_context_native import native_intervals

parser=argparse.ArgumentParser()
parser.add_argument('--daily',type=Path,required=True)
parser.add_argument('--calendar',type=Path,required=True)
parser.add_argument('--full-history',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
head='93d7393920a125e0a26b2d52cd5b17c61d315d45'
raw=subprocess.check_output(['git','show',head+':breadth_derived.py'],cwd=repo)
module=types.ModuleType('reviewed_breadth118');exec(compile(raw,'reviewed_breadth118.py','exec'),module.__dict__)
for file,expected in ((args.daily,'22dfcd51f88d898a7bc156efa9d79677c769d207604f3a68aec065623d65b2c0'),
                      (args.calendar,'3904f3115c180d40f230e36facad6b585efed861f0e8af13225e4dfb8513d074'),
                      (args.full_history,'f322b9bf2b2af928fb5fd6f222904c3d2a35511da8e227fa9aad0e310d5dd8f5')):
    if hashlib.sha256(file.read_bytes()).hexdigest()!=expected:raise ValueError('review source differs: '+file.name)
daily=pd.read_parquet(args.daily)
calendar=pd.DatetimeIndex(pd.read_parquet(args.calendar).date).as_unit('ns')
native=module.derive_candles(daily,daily.date)
groups=[]
for tf in ('2d','5d','10d','21d'):
    expected=native_intervals(calendar,tf)
    keys=set(zip(expected.candle_start.astype(str),expected.source_candle_end.astype(str)))
    own=native.loc[native.timeframe==tf]
    wrong=[dict(start=str(r.candle_start.date()),end=str(r.date.date())) for r in own.itertuples()
           if (str(r.candle_start),str(r.date)) not in keys]
    groups.append(dict(timeframe=tf,rows=len(own),off_frozen_anchor=len(wrong),first_wrong=wrong[:1]))
dates=pd.bdate_range('2024-01-02',periods=6)
toy=pd.DataFrame(dict(date=dates,available_from=dates+pd.offsets.BDay(1),advance=2.,decline=1.,up_volume=20.,down_volume=10.))
hole=toy.drop(index=2)
bad=module.derive_candles(hole,dates).query("timeframe == '5d'")
full=module.derive(pd.read_parquet(args.full_history))
short=module.derive(daily)
first=pd.Timestamp('2020-01-02')
a=full.loc[full.date==first].iloc[0];b=short.loc[short.date==first].iloc[0]
out=dict(status='READ_ONLY_118_REVIEW_NOT_ACCEPTANCE',pr=118,head=head,
         code_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=hashlib.sha256(args.daily.read_bytes()).hexdigest(),
         calendar_sha256=hashlib.sha256(args.calendar.read_bytes()).hexdigest(),actual_rebuilt_native_rows=len(native),
         anchor_checks=groups,
         interior_missing_session=dict(input_sessions=len(hole),expected_bucket_sessions=5,actual_bucket_sessions=4,emitted_incomplete_rows=len(bad)),
         truncated_warmup=dict(date=str(first.date()),full_history_oscillator=float(a.mcclellan_oscillator),
                               truncated_history_oscillator=float(b.mcclellan_oscillator),
                               full_history_summation=float(a.mcclellan_summation),truncated_history_summation=float(b.mcclellan_summation)),
         decision='Do not promote 118 as native certification: retain original evidence, use frozen anchor, require every expected session, bind full-history warmup.',
         protected_world_action=False)
args.output.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))

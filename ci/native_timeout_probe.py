"""Bounded reproduction of the next entity after native shard 18 stopped."""
import argparse
import faulthandler
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    parser.add_argument('--worker',action='store_true');parser.add_argument('--timeframe',default='1d')
    args=parser.parse_args();root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    if args.worker:
        import pandas as pd
        import facets_world as fw
        from world_timeframes import completed_candles,PRICE_COLS
        bars=pd.read_parquet(root/'WKSP.bars.parquet')
        calendar=pd.DatetimeIndex(pd.read_parquet(root/'market_sessions.parquet').date)
        candles=completed_candles(bars,args.timeframe,session_calendar=calendar)
        print('TIMEOUT_PROBE_BEGIN',args.timeframe,len(candles),flush=True)
        faulthandler.dump_traceback_later(10,repeat=True)
        started=time.perf_counter()
        values=fw.compute_tv_extra(*(candles[c].to_numpy(float) for c in PRICE_COLS),dates=candles.date.to_numpy())
        faulthandler.cancel_dump_traceback_later()
        print('TIMEOUT_PROBE_RETURNED',len(values),time.perf_counter()-started,flush=True)
        return
    from ci import native_price_base as base
    from ci.native_price_blocks import sha,read_member,recipe_fingerprint,write_json
    from ci.release_assets import download_asset
    tag='native-price-inputs-v1-40336250454-1'
    file=download_asset(tag,'BUILD_INPUTS.json',root)
    if sha(file)!='a57aee6ae2dd3b2f444d2433bac8242f44b9346a5aea826f0250c96ed376ccf4':raise ValueError('input manifest differs')
    inputs=json.loads(file.read_text());inputs['inputs_tag']=tag
    if recipe_fingerprint()[0]!=inputs['recipe_fingerprint']:raise ValueError('probe is not the frozen recipe')
    calendar=download_asset(tag,'market_sessions.parquet',root)
    if sha(calendar)!=inputs['calendar_sha256']:raise ValueError('calendar differs')
    selected={r['ticker'] for r in inputs['records'] if r['ordinal']%16==2}
    original=base.download;base.download=download_asset
    try:parts,_=base.recover_base_parts('native-price-base-v1-40360947486-1-002',inputs,selected,root/'manifests')
    finally:base.download=original
    part=next(p for p in parts if 'WKSP' in p['tickers'])
    manifest=json.loads((root/'manifests'/(part['part']+'.json')).read_text())
    archive=download_asset(part['release'],part['part']+'.tar',root/'source')
    if sha(archive)!=part['archive_sha256']:raise ValueError('source archive differs')
    raw=read_member(archive,manifest,'WKSP'.encode().hex()+'.bars.parquet')
    (root/'WKSP.bars.parquet').write_bytes(raw);archive.unlink()
    report=dict(source_commit=os.environ['GITHUB_SHA'],ticker='WKSP',source_part=part,
                source_member_sha256=hashlib.sha256(raw).hexdigest(),recipe_fingerprint=inputs['recipe_fingerprint'],
                source_job=122011092503,source_run=40450227376,
                job_annotation='The job has exceeded the maximum execution time of 5h50m0s',
                inference='WKSP is next after SNAL/TXN/VSS in the exact recovered shard order; reproduce before another long retry',
                probes=[],world_gate='NOT_RUN',scoring_gate='CLOSED')
    for tf in ('1d','2d','5d','21d','monthly'):
        started=time.perf_counter()
        command=[sys.executable,'-m','ci.native_timeout_probe','--directory',str(root),'--worker','--timeframe',tf]
        try:
            result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
            row=dict(timeframe=tf,returncode=result.returncode,timed_out=False,
                     stdout=result.stdout.decode(errors='replace')[-2000:],stderr=result.stderr.decode(errors='replace')[-12000:])
        except subprocess.TimeoutExpired as exc:
            row=dict(timeframe=tf,timed_out=True,stdout=(exc.stdout or b'').decode(errors='replace')[-2000:],
                     stderr=(exc.stderr or b'').decode(errors='replace')[-12000:])
        row['seconds']=time.perf_counter()-started;report['probes'].append(row)
        print('BOUNDED_NATIVE_PROBE',json.dumps(row),flush=True)
        write_json(root/'NATIVE_TIMEOUT_PROBE.json',report)
        if row['timed_out']:break


if __name__=='__main__':main()

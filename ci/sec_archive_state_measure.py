"""Measure native filing states using immutable GitHub assets; no SEC access."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tarfile
import time

import numpy as np
import pandas as pd

from ci.release_assets import download_asset,gh_retry,publish_assets
from world_context_native import KEYS,native_intervals
from world_sec_facts import FactSelection,compile_fact_timeline,fact_values_at
from world_timeframes import TIMEFRAMES


def digest(raw):return hashlib.sha256(raw).hexdigest()


def selections():
    # Explicit parallel concepts: no silent revenue/share tag substitution.
    specs={name:FactSelection('us-gaap',metric,unit,'instant') for name,metric,unit in (
        ('assets','Assets','USD'),('liabilities','Liabilities','USD'),
        ('common_shares','CommonStockSharesOutstanding','shares'))}
    specs['entity_shares']=FactSelection('dei','EntityCommonStockSharesOutstanding','shares','instant')
    for name,metric in (('revenues','Revenues'),('contract_revenues','RevenueFromContractWithCustomerExcludingAssessedTax'),('net_income','NetIncomeLoss')):
        for period,bounds in (('quarter',(60,120)),('annual',(330,400))):
            specs[name+'_'+period]=FactSelection('us-gaap',metric,'USD','duration',bounds)
    return specs


def verified_facts(archive,manifest,quarantined):
    """Verify every member; read without extracting archive-controlled paths."""
    if digest(archive)!=manifest['archive_sha256']:raise ValueError('archive SHA differs')
    records=manifest['members'];expected={m['name']:m for m in records}
    if len(records)!=len(expected):raise ValueError('duplicate manifest member')
    bodies={}
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        members=source.getmembers()
        if len(members)!=len(expected) or {m.name for m in members}!=set(expected):raise ValueError('archive membership differs')
        for member in members:
            if not member.isfile() or Path(member.name).name!=member.name or '\\' in member.name:raise ValueError('invalid archive member')
            meta=expected[member.name]
            if member.size!=meta['bytes'] or member.size>64*1024*1024:raise ValueError('member size differs or exceeds bound')
            raw=source.extractfile(member).read()
            if digest(raw)!=meta['sha256']:raise ValueError('member SHA differs')
            bodies[member.name]=raw
    outputs=[]
    for name,raw in bodies.items():
        match=re.fullmatch(r'CIK(\d{10})\.facts\.parquet',name)
        if not match:continue
        cik=int(match[1])
        if cik in quarantined:raise ValueError('requested sample contains quarantined CIK')
        original=f'CIK{cik:010d}.companyfacts.json.gz'
        if original not in bodies:raise ValueError('original companyfacts missing')
        payload=json.loads(gzip.decompress(bodies[original]))
        if payload.get('cik')!=cik:raise ValueError('raw root CIK differs')
        frame=pd.read_parquet(io.BytesIO(raw))
        if frame.empty or not frame.cik.eq(cik).all():raise ValueError('numeric CIK differs or empty')
        # Reparse independently with the already audited source parser.
        from fetch.fetch_sec_world import numeric_facts
        pd.testing.assert_frame_equal(frame.reset_index(drop=True),numeric_facts(cik,payload).reset_index(drop=True),check_exact=True)
        outputs.append((cik,frame,dict(member=name,sha256=digest(raw),raw_member=original,raw_sha256=digest(bodies[original]))))
    if not outputs:raise ValueError('no numeric facts in selected archive')
    return outputs


def native_values(calendar,timeframe,timelines):
    bounds=native_intervals(calendar,timeframe)
    values=[bounds[list(KEYS)]]
    for name,timeline in timelines.items():
        values.append(fact_values_at(bounds.available_from,timeline,'sec_'+name).drop(columns='date'))
    return pd.concat(values,axis=1)


def prefix_proof(facts,cik,calendar,full,cut):
    cut=pd.Timestamp(cut)
    earlier=facts[pd.to_datetime(facts.filed)<cut]
    timelines={name:compile_fact_timeline(earlier,cik,spec) for name,spec in selections().items()}
    compared=0
    for tf in TIMEFRAMES:
        expected=full[tf][full[tf].available_from<=cut].reset_index(drop=True)
        actual=native_values(calendar[calendar<=cut],tf,timelines)
        pd.testing.assert_frame_equal(expected,actual,check_exact=True)
        compared+=len(expected)*(len(expected.columns)-len(KEYS))
    return dict(cut=str(cut.date()),timeframes=len(TIMEFRAMES),cells_compared=compared,mismatches=0)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    args=parser.parse_args();root=Path(args.directory);root.mkdir(parents=True,exist_ok=True)
    request_file=Path('ci/SEC_ARCHIVE_STATE_REQUEST.json');request=json.loads(request_file.read_text())
    files={}
    for key in ('source_manifest','source_archive'):
        file=download_asset(request['source_tag'],request[key],root)
        if digest(file.read_bytes())!=request[key+'_sha256']:raise ValueError(key+' pinned SHA differs')
        files[key]=file
    manifest=json.loads(files['source_manifest'].read_text())
    calendar_file=download_asset(request['inputs_tag'],'market_sessions.parquet',root)
    if digest(calendar_file.read_bytes())!=request['calendar_sha256']:raise ValueError('calendar pinned SHA differs')
    calendar=pd.DatetimeIndex(pd.read_parquet(calendar_file).date).as_unit('ns')
    sources=verified_facts(files['source_archive'].read_bytes(),manifest,set(request['quarantined_ciks']))
    started=time.perf_counter();proofs=[];members=[];coverage=[]
    output=root/'SEC_NATIVE_CIK_SAMPLE.tar'
    with tarfile.open(output,'w') as archive:
        for cik,facts,source in sources:
            timelines={name:compile_fact_timeline(facts,cik,spec) for name,spec in selections().items()}
            full={tf:native_values(calendar,tf,timelines) for tf in TIMEFRAMES}
            cuts=[prefix_proof(facts,cik,calendar,full,cut) for cut in request['cuts']]
            proofs.append(dict(cik=cik,source=source,prefix_checks=cuts,audits={name:t.attrs['audit'] for name,t in timelines.items()}))
            for name,frame in [(name+'.timeline',t) for name,t in timelines.items()]+list(full.items()):
                # Preserve all supplied native history and all chosen output columns.
                raw=frame.to_parquet(index=False,compression='zstd')
                restored=pd.read_parquet(io.BytesIO(raw))
                pd.testing.assert_frame_equal(frame,restored,check_exact=True)
                for column in frame.select_dtypes(include=['float64']):
                    if not np.array_equal(frame[column].to_numpy().view('uint64'),restored[column].to_numpy().view('uint64')):
                        raise ValueError('Parquet numeric bits differ')
                member=f'CIK{cik:010d}/{name}.parquet';info=tarfile.TarInfo(member);info.size=len(raw)
                archive.addfile(info,io.BytesIO(raw));members.append(dict(name=member,bytes=len(raw),sha256=digest(raw)))
                if name in TIMEFRAMES:
                    for column in frame:
                        if column.endswith('_value'):
                            coverage.append(dict(cik=cik,timeframe=name,column=column,rows=len(frame),known=int(frame[column].notna().sum())))
            print('SEC_ARCHIVED_CIK_COMPLETE',cik,len(facts),flush=True)
    report=dict(status='ARCHIVED_CIK_SAMPLE_MEASURED_NOT_FULL_WORLD',source_commit=os.environ['GITHUB_SHA'],
        request=request,request_sha256=digest(request_file.read_bytes()),ciks=len(sources),
        source_rows=sum(len(facts) for _,facts,_ in sources),timeframes=list(TIMEFRAMES),
        selections={name:asdict(spec) for name,spec in selections().items()},
        source_dependencies=[dict(name=file.name,bytes=file.stat().st_size,sha256=digest(file.read_bytes())) for file in [*files.values(),calendar_file]],
        native_archive=dict(name=output.name,bytes=output.stat().st_size,sha256=digest(output.read_bytes()),members=members),
        seconds=time.perf_counter()-started,proofs=proofs,world_gate='NOT_PROVEN',scoring_gate='CLOSED',
        identity_scope='CIK_ONLY_NO_HISTORICAL_TICKER_ASSIGNMENT',
        remaining=['full source universe and requested concept/settings registry','historical ticker identity and eligibility',
                   'question tree and quality gate','full dependency storage budget','comprehensive full-world leak proof'])
    status=root/'SEC_ARCHIVE_STATE_MEASURED.json';status.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    coverage_file=root/'SEC_NATIVE_SAMPLE_COVERAGE.csv';pd.DataFrame(coverage).to_csv(coverage_file,index=False)
    tag=f"sec-native-sample-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,output,coverage_file,status)
    gh_retry('release','edit',tag,'--draft=false')


if __name__=='__main__':main()

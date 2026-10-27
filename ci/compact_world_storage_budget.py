"""Measure raw-once/packed-answer storage; never approve an incomplete world."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

REPO=Path(__file__).resolve().parents[1]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def worker(root,recipe):
    sys.path[:0]=[str(recipe),str(REPO)]
    import resource
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import facets_world as fw
    from world_timeframes import TIMEFRAMES,completed_candles,candle_features,align_features
    from world_answer_cache import encode_answers,decode_answers,registry_bytes
    config=json.loads((root/'PROBE_INPUTS.json').read_text())
    calendar=pd.DatetimeIndex(pd.read_parquet(root/'market_sessions.parquet').date)
    query=calendar[calendar>=pd.Timestamp('2020-01-01')]
    funcs=fw.discover();samples=[];schemas={}
    for sample in config['samples']:
        raw=(root/sample['file']).read_bytes()
        if sha(raw)!=sample['sha256']:raise ValueError('raw price sample changed')
        bars=pd.read_parquet(io.BytesIO(raw));started=time.perf_counter()
        query=calendar[calendar>=pd.Timestamp('2020-01-01')]
        if config.get('restrict_query_to_source_sessions'):
            query=query[query.isin(pd.DatetimeIndex(bars.date))]
        source_years=len(bars[bars.date>=pd.Timestamp('2020-01-01')])/252
        archive_buffer=io.BytesIO();questions=0;constant=0;empty=0;packed_raw=0
        with tarfile.open(fileobj=archive_buffer,mode='w') as tar:
            for tf in TIMEFRAMES:
                native=completed_candles(bars,tf,session_calendar=calendar)
                frame=candle_features(native,funcs,timeframe=tf)
                values=frame.drop(columns='available_from')
                mean=values.rolling(20).mean();std=values.rolling(20).std(ddof=0)
                previous=values.shift(1)
                answers={};registry=[]
                for name in values:
                    x=values[name]
                    for facet,left,right in (('rising1',x,previous[name]),('above_mean20',x,mean[name]),
                                              ('above_mean_plus_sd20',x,mean[name]+std[name])):
                        question=name+':'+facet
                        valid=np.isfinite(left)&np.isfinite(right)
                        answers[question]=np.where(valid,(left>right).astype(float),np.nan)
                        registry.append(dict(question_id=question+'__'+tf,outcomes=[0,1],
                                             formula=facet+' on '+name+' in completed '+tf+' candles; finite operands required, otherwise missing; available_from <= D'))
                native_answers=pd.DataFrame(answers)
                native_answers['available_from']=frame.available_from
                aligned=align_features(query,native_answers,tf).drop(columns='date')
                if list(aligned)!=[q['question_id'] for q in registry]:raise ValueError('diagnostic registry/order differs')
                questions+=len(registry)
                for start in range(0,len(registry),128):
                    own_registry=registry[start:start+128];own=aligned.iloc[:,start:start+128]
                    provenance=dict(input_manifest_sha256=config['inputs_sha256'],recipe_fingerprint=config['recipe_fingerprint'],
                        question_tree_sha256=sha(registry_bytes(own_registry)),
                        row_keys_sha256=sha(sample['ticker'].encode()+query.asi8.tobytes()),
                        eligibility_mask_sha256=sha(np.ones(len(query),dtype=np.uint8).tobytes()))
                    payload,meta=encode_answers(own,own_registry,provenance)
                    decoded=decode_answers(payload,meta,own_registry,provenance)
                    pd.testing.assert_frame_equal(decoded,own.astype(object).where(own.notna(),None),check_dtype=False)
                    schema=registry_bytes(own_registry);schemas[sha(schema)]=schema
                    for suffix,data in (('.zst',payload),('.json',json.dumps(meta,sort_keys=True).encode())):
                        member=tarfile.TarInfo(f'{tf}_{start:05d}'+suffix);member.size=len(data);member.mtime=0
                        tar.addfile(member,io.BytesIO(data))
                    packed_raw+=meta['raw_bytes']
                nonblank=aligned.notna().sum();unique=aligned.nunique(dropna=True)
                constant+=int(((unique<=1)&(nonblank>0)).sum());empty+=int((nonblank==0).sum())
        container=bytes(pa.Codec('zstd',compression_level=9).compress(archive_buffer.getvalue()))
        name=sample['ticker'].encode().hex()+'.diagnostic_answers.tar.zst';(root/name).write_bytes(container)
        row=dict(ticker=sample['ticker'],input_rows=len(bars),query_rows=len(query),query_stock_years=source_years,
                 raw_daily_bytes=len(raw),diagnostic_questions=questions,constant_questions=constant,
                 empty_questions=empty,packed_uncompressed_bytes=packed_raw,answer_container_bytes=len(container),
                 answer_container_sha256=sha(container),bytes_per_stock_year=(len(raw)+len(container))/source_years,
                 seconds=time.perf_counter()-started,roundtrip='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT')
        samples.append(row);print('COMPACT_STORAGE_SAMPLE',json.dumps(row),flush=True)
    registry_file=root/'DIAGNOSTIC_REGISTRIES.json'
    registry_file.write_text(json.dumps({key:json.loads(value) for key,value in schemas.items()},sort_keys=True,separators=(',',':')))
    result=dict(samples=samples,shared_registry_bytes=registry_file.stat().st_size,
                peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (root/'COMPACT_STORAGE_WORKER.json').write_text(json.dumps(result,indent=2)+'\n')


def run(root,request):
    import pandas as pd
    from ci.release_assets import download_asset
    from ci.native_price_blocks import read_member
    root.mkdir(parents=True,exist_ok=True)
    file=download_asset(request['inputs_tag'],'BUILD_INPUTS.json',root);raw=file.read_bytes()
    if sha(raw)!=request['inputs_sha256']:raise ValueError('input manifest differs')
    inputs=json.loads(raw)
    calendar=download_asset(request['inputs_tag'],'market_sessions.parquet',root)
    if sha(calendar.read_bytes())!=inputs['calendar_sha256']:raise ValueError('calendar differs')
    meta=download_asset(request['compact_source'],request['compact_part']+'.json',root/'source')
    manifest=json.loads(meta.read_text())
    if manifest['recipe_fingerprint']!=inputs['recipe_fingerprint']:raise ValueError('source recipe differs')
    archive=download_asset(request['compact_source'],request['compact_part']+'.tar',root/'source')
    if sha(archive.read_bytes())!=manifest['archive_sha256']:raise ValueError('source archive differs')
    samples=[]
    for ticker in request['sample_tickers']:
        name=ticker.encode().hex()+'.bars.parquet';raw=read_member(archive,manifest,name)
        (root/name).write_bytes(raw);samples.append(dict(ticker=ticker,file=name,sha256=sha(raw)))
    archive.unlink()
    recipe=root/'corrected-recipe';recipe.mkdir(exist_ok=True)
    subprocess.run(['git','fetch','--depth=1','origin',request['corrected_commit']],cwd=REPO,check=True)
    files={}
    for name in inputs['recipe_files']:
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('unsafe recipe path')
        raw=subprocess.check_output(['git','show',request['corrected_commit']+':'+name],cwd=REPO)
        path=recipe/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);files[name]=sha(raw)
    fingerprint=sha(json.dumps(files,sort_keys=True).encode())
    if fingerprint!=request['corrected_recipe_fingerprint']:raise ValueError('corrected recipe fingerprint differs')
    config=dict(samples=samples,inputs_sha256=request['inputs_sha256'],recipe_fingerprint=fingerprint)
    (root/'PROBE_INPUTS.json').write_text(json.dumps(config,indent=2)+'\n')
    subprocess.run([sys.executable,str(Path(__file__).resolve()),'--directory',str(root),'--worker','--recipe',str(recipe)],check=True,cwd=REPO)
    measured=json.loads((root/'COMPACT_STORAGE_WORKER.json').read_text())
    count=inputs['selected_tickers'];largest=max(s['raw_daily_bytes']+s['answer_container_bytes'] for s in measured['samples'])
    estimate=largest*count*1.25+measured['shared_registry_bytes']
    from collections import Counter
    largest_shard=max(Counter(r['feature_shard'] for r in inputs['records']).values())
    report=dict(status='PRICE_STORAGE_SAMPLE_ONLY_WORLD_BUDGET_INCOMPLETE',request=request,measurement=measured,
                source_commit=os.environ['GITHUB_SHA'],price_scope_projected_bytes=estimate,price_scope_projected_gb=estimate/1e9,
                projected_existing_shard_seconds=max(s['seconds'] for s in measured['samples'])*largest_shard*1.25+1800,
                hard_world_cap_bytes=100000000000,full_world_estimate_bytes=None,
                full_world_cap_gate='NOT_PROVEN; all nonprice runtime dependencies, actual complete question tree and PIT eligibility remain unmeasured',
                eligibility='UNFILTERED_CONSERVATIVE_SAMPLE; all-true mask is not historical tradeability approval',
                persisted=['raw daily OHLCV once','shared registered outcome dictionaries','packed diagnostic fixed-outcome chunks'],
                recomputed=['all 22 native candle grids','all 1044 numeric features per timeframe','diagnostic rolling comparisons'],
                dropped_semantic_items=[],comparison_families='REQUIRED; not dropped; complete comparator storage is outside this price-only probe',
                constant_empty_policy='Measured and logged; retained in probe, no silent question pruning',
                limitation='Three deterministic entities from one source part. Diagnostic questions are not the completed v3 tree. Global cache coordination and every nonprice dependency still require measurement.',
                full_world_gate='NOT_RUN',scoring_gate='CLOSED')
    (root/'COMPACT_WORLD_STORAGE_BUDGET_V1.json').write_text(json.dumps(report,indent=2)+'\n')
    print('COMPACT_PRICE_SCOPE_ESTIMATE_GB',estimate/1e9,'WORLD_CAP_NOT_PROVEN',flush=True)
    if estimate>report['hard_world_cap_bytes']:raise RuntimeError('even the price-only diagnostic storage exceeds the hard world cap')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    parser.add_argument('--worker',action='store_true');parser.add_argument('--recipe')
    args=parser.parse_args();root=Path(args.directory).resolve()
    if args.worker:worker(root,Path(args.recipe));return
    request=json.loads(Path('ci/COMPACT_WORLD_STORAGE_REQUEST.json').read_text())
    run(root,request)


if __name__=='__main__':main()

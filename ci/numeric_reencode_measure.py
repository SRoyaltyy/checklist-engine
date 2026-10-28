"""Benchmark reversible codecs on persisted native arrays, never indicators."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import time

REPO=Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
import numpy as np
import pyarrow as pa
from world_numeric_codec import PREDICTOR_CHOICES,decode_numeric,encode_numeric

FRAMES=tuple(f'{i}d' for i in range(1,22))+('monthly',)
REQUEST=REPO/'ci/NUMERIC_REENCODE_REQUEST.json'


def digest(raw):return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def expanded(raw,limit):
    chunks=[];remaining=limit+1
    with pa.CompressedInputStream(pa.BufferReader(raw),'zstd') as source:
        while remaining:
            chunk=source.read(min(1<<20,remaining))
            if not chunk:break
            chunks.append(chunk);remaining-=len(chunk)
    decoded=b''.join(chunks)
    if len(decoded)>limit:raise ValueError('numeric container exceeds expansion bound')
    return decoded


def checked_members(packed,limit=1000000000):
    bodies={}
    with tarfile.open(fileobj=io.BytesIO(expanded(packed,limit))) as source:
        for member in source:
            if not member.isfile() or member.name in bodies or member.size>limit:
                raise ValueError('invalid numeric archive member')
            bodies[member.name]=source.extractfile(member).read()
    expected={tf+suffix for tf in FRAMES for suffix in ('.numeric.zst','.json','.dates.zst')}
    if set(bodies)!=expected:raise ValueError('native archive timeframe/member set differs')
    return bodies


def choose_encoding(values,columns,provenance):
    original=np.ascontiguousarray(values,dtype='<f8').tobytes();trials=[];best=None
    for mode in PREDICTOR_CHOICES:
        started=time.perf_counter();payload,metadata=encode_numeric(values,columns,provenance,predictors=mode)
        restored=decode_numeric(payload,metadata,columns,provenance)
        if restored.tobytes()!=original:raise ValueError('candidate numeric bits differ')
        trials.append(dict(predictors=list(mode),bytes=len(payload),seconds=time.perf_counter()-started,
                           roundtrip='ALL_FLOAT64_BITS_EXACT'))
        if best is None or len(payload)<len(best[0]):best=(payload,metadata)
    return *best,trials


def reencode(source_file,registry_file,stock,root):
    if file_digest(source_file)!=stock['container_sha256']:raise ValueError('persisted source container fingerprint differs')
    registry_raw=Path(registry_file).read_bytes();registry=json.loads(registry_raw)
    if set(registry)!=set(FRAMES):raise ValueError('column registry timeframe set differs')
    members=checked_members(Path(source_file).read_bytes());output=io.BytesIO();reports=[];source_hashes={}
    measured={r['timeframe']:r for r in stock['timeframes']}
    if set(measured)!=set(FRAMES):raise ValueError('source measurement timeframe set differs')
    with tarfile.open(fileobj=output,mode='w') as target:
        for tf in FRAMES:
            old=json.loads(members[tf+'.json']);columns=registry[tf]['columns'];provenance=old['provenance']
            if (old['ticker']!=stock['ticker'] or old['timeframe']!=tf or old['rows']!=measured[tf]['native_rows'] or
                len(columns)!=measured[tf]['columns'] or provenance['recipe_fingerprint']!=stock['recipe_fingerprint']):
                raise ValueError('stored numeric stock/shape/recipe differs')
            dates=expanded(members[tf+'.dates.zst'],old['rows']*8)
            if (len(dates)!=old['rows']*8 or digest(dates)!=old['dates_sha256'] or
                digest(stock['ticker'].encode()+dates)!=provenance['row_keys_sha256']):raise ValueError('stored dates or row identity differs')
            values=decode_numeric(members[tf+'.numeric.zst'],old,columns,provenance)
            payload,new,trials=choose_encoding(values,columns,provenance)
            # Preserve every source metadata field, overriding only codec fields.
            metadata=dict(old,**new);metadata['reencoded_from_compressed_sha256']=old['compressed_sha256']
            source_hashes[tf]=(old['raw_sha256'],old['dates_sha256'])
            for suffix,raw in (('.numeric.zst',payload),('.json',json.dumps(metadata,sort_keys=True,allow_nan=False).encode()),
                               ('.dates.zst',members[tf+'.dates.zst'])):
                member=tarfile.TarInfo(tf+suffix);member.size=len(raw);member.mtime=0;target.addfile(member,io.BytesIO(raw))
            reports.append(dict(timeframe=tf,native_rows=len(values),columns=len(columns),
                original_numeric_bytes=len(members[tf+'.numeric.zst']),chosen_numeric_bytes=len(payload),
                chosen_predictors=new['predictors'],source_numeric_sha256=old['raw_sha256'],trials=trials))
            print('NATIVE_CODEC_FRAME_COMPLETE',stock['ticker'],tf,len(payload),new['predictors'],flush=True)
    packed=bytes(pa.Codec('zstd',compression_level=19).compress(output.getvalue()))
    root=Path(root);root.mkdir(parents=True,exist_ok=True);file=root/(stock['ticker'].encode().hex()+'.all_native_values.tar.zst');file.write_bytes(packed)
    # Independent persisted-container readback, not only in-memory trial checks.
    restored_members=checked_members(file.read_bytes())
    for tf in FRAMES:
        metadata=json.loads(restored_members[tf+'.json'])
        values=decode_numeric(restored_members[tf+'.numeric.zst'],metadata,registry[tf]['columns'],metadata['provenance'])
        if digest(values.tobytes())!=source_hashes[tf][0]:raise ValueError('persisted reconstructed values differ')
        if digest(expanded(restored_members[tf+'.dates.zst'],metadata['rows']*8))!=source_hashes[tf][1]:raise ValueError('persisted dates differ')
    return dict(ticker=stock['ticker'],source_container_sha256=stock['container_sha256'],source_rows=stock['source_rows'],
                source_container_bytes=Path(source_file).stat().st_size,container_bytes=len(packed),container_sha256=digest(packed),
                registry_sha256=digest(registry_raw),registry_bytes=len(registry_raw),timeframes=reports,
                roundtrip='ALL_STORED_VALUE_AND_DATE_BITS_EXACT',indicator_calls=0,
                retained='ALL_SOURCE_NATIVE_ROWS_ALL_COLUMNS_ALL_22_TIMEFRAMES_INCLUDING_PRE2020')


def worker(root):
    import resource
    config=json.loads((root/'WORKER.json').read_text());started=time.perf_counter()
    result=reencode(config['source_file'],config['registry_file'],config['stock'],root)
    result.update(seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (root/'REENCODE_STOCK.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')


def run(root,request):
    from ci.compact_world_build import limited_process
    from ci.release_assets import download_asset,gh_retry,publish_assets
    root.mkdir(parents=True,exist_ok=True)
    source=download_asset(request['source_release'],'NUMERIC_RETENTION_MEASURED.json',root/'source')
    if file_digest(source)!=request['source_report_sha256']:raise ValueError('source sample report changed')
    report=json.loads(source.read_text());stocks={r['ticker']:r for r in report['samples']}
    if report['errors'] or report['status']!='FULL_NUMERIC_RETENTION_MEASURED_SAMPLE_ONLY':raise ValueError('source sample incomplete')
    if len(request['sample_tickers'])!=len(set(request['sample_tickers'])) or set(request['sample_tickers'])!=set(stocks):
        raise ValueError('all persisted source samples required exactly once')
    denominator=REPO/'docs/NATIVE_ROW_DENOMINATOR_V1.json'
    if file_digest(denominator)!=request['denominator_sha256']:raise ValueError('verified universe row denominator changed')
    counts=json.loads(denominator.read_text())['native_rows_by_timeframe']
    results=[];errors=[];assets=[];registries={}
    for ticker in request['sample_tickers']:
        stock=stocks[ticker];stem=ticker.encode().hex();own=root/stem;own.mkdir(exist_ok=True)
        archive=download_asset(request['source_release'],stem+'.all_native_values.tar.zst',root/'source')
        registry=download_asset(request['source_release'],stem+'.column_registry.json',root/'source')
        (own/'WORKER.json').write_text(json.dumps(dict(stock=stock,source_file=str(archive.resolve()),registry_file=str(registry.resolve()))))
        outcome=limited_process([sys.executable,str(Path(__file__).resolve()),'--worker','--directory',str(own.resolve())],own,request['stock_timeout_seconds'])
        if outcome['reason']:errors.append(dict(ticker=ticker,**outcome));continue
        result=json.loads((own/'REENCODE_STOCK.json').read_text());results.append(result);assets.append(own/(stem+'.all_native_values.tar.zst'))
        registries.setdefault(result['registry_sha256'],registry)
    weighted=None
    if results:
        weighted=sum(counts[tf]*sum(next(r['chosen_numeric_bytes']/r['native_rows'] for r in stock['timeframes'] if r['timeframe']==tf) for stock in results)/len(results) for tf in FRAMES)
    summary=dict(status='REENCODE_MEASURED_SAMPLE_ONLY' if not errors and len(results)==len(request['sample_tickers']) else 'INCOMPLETE_REENCODE_SAMPLE',
        source_commit=os.environ['GITHUB_SHA'],request=request,source_report_sha256=file_digest(source),denominator_sha256=file_digest(denominator),
        samples=results,errors=errors,weighted_numeric_payload_projection_bytes=weighted,
        shared_registries=[dict(asset=file.name,sha256=digest_,bytes=file.stat().st_size) for digest_,file in registries.items()],
        projection_excludes=['date/container overhead','answers','raw/shared/nonprice dependencies','additional question intermediates'],
        numeric_payload_only_under_100GB=not errors and len(results)==len(stocks) and weighted is not None and weighted<100000000000,
        full_world_estimate_bytes=None,world_gate='NOT_PROVEN',scoring_gate='CLOSED',indicator_calls=0,approved_world_run_untouched=40621517496)
    status=root/'NUMERIC_REENCODE_MEASURED.json';status.write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    tag=f"numeric-reencode-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'])
    publish_assets(tag,*assets,*registries.values(),status);gh_retry('release','edit',tag,'--draft=false')
    print('WEIGHTED_REENCODE_NUMERIC_PAYLOAD_GB',None if weighted is None else weighted/1e9,flush=True)
    if errors:raise RuntimeError('sample incomplete; retained evidence published and no acceptance inferred')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    if args.worker:worker(args.directory)
    else:
        import subprocess
        from ci.release_assets import describe_failure
        try:run(args.directory,json.loads(REQUEST.read_text()))
        except subprocess.CalledProcessError as exc:
            print('NUMERIC_REENCODE_API_FAILURE',describe_failure(exc),flush=True)
            raise

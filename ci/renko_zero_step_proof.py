"""GitHub-only bounded proof of a separate Renko zero-distance recipe.

Keep module imports free of math before the worker installs its bound recipe.
No active production request or historical output is changed here.
"""
import argparse
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

from ci.renko_recipe import BASE_COMMIT,BASE_FINGERPRINT,derive,fingerprint,sha

REPO=Path(__file__).resolve().parents[1]
REQUEST=REPO/'ci/RENKO_ZERO_STEP_PROOF_REQUEST.json'
FRAMES=[str(n)+'d' for n in range(1,22)]+['monthly']


def validate_request(request):
    tickers=[s['ticker'] for s in request['stocks']]
    if len(tickers)!=3 or set(tickers)!={'MAN','MNTS','EYE'}:
        raise ValueError('Renko proof requires exactly the original three unique stocks')
    if request['target']['member']!='45514c54.bars.parquet':
        raise ValueError('Renko proof target must remain the authenticated EQLT input')
    if not 0<request['worker_timeout_seconds']<=900:
        raise ValueError('Renko proof must use bounded isolated workers')


def validate_checks(checks):
    if (len(checks)!=22 or [r['timeframe'] for r in checks]!=FRAMES
            or any(r['columns']!=1044 or r['rows']<=0 or r['numeric_cells']!=r['rows']*1044
                   or r['mismatches']!=0 for r in checks)):
        raise ValueError('Renko proof requires complete exact 22-frame numeric evidence')


def numeric_receipt(frame,columns,expected=None):
    import numpy as np
    if list(frame.drop(columns='available_from'))!=columns:raise ValueError('Renko proof changed numeric column registry/order')
    values=np.ascontiguousarray(frame[columns].to_numpy(dtype='<f8'))
    dates=frame.available_from.to_numpy(dtype='datetime64[ns]').view('<i8')
    result=dict(rows=len(frame),columns=len(columns),numeric_cells=int(values.size),
                raw_sha256=sha(values.tobytes()),dates_sha256=sha(dates.tobytes()))
    different={} if expected is None else {key:dict(expected=expected[key],actual=result[key])
                                            for key in ('rows','columns','raw_sha256','dates_sha256') if result[key]!=expected[key]}
    if different:raise ValueError('Renko candidate differs from persisted legacy numeric/date bits: '+json.dumps(different,sort_keys=True))
    return dict(result,mismatches=0)


def numeric_worker(root,recipe):
    # The orchestrator imports world_timeframes, so it must not enter this
    # process before the frozen/derived recipe is installed in sys.path.
    sys.path[:0]=[str(recipe),str(REPO)]
    import resource
    import numpy as np
    import pandas as pd
    import facets_world as fw
    import world_timeframes as wt
    if Path(fw.__file__).resolve().parent!=recipe or Path(wt.__file__).resolve().parent!=recipe:
        raise ValueError('Renko proof loaded unbound math')
    config=json.loads((root/'WORKER.json').read_text(encoding='utf-8'))
    raw=Path(config['bars']).read_bytes()
    if sha(raw)!=config['source_sha256']:raise ValueError('Renko proof raw input changed')
    calendar_file=Path(config['calendar'])
    if sha(calendar_file.read_bytes())!=config['calendar_sha256']:raise ValueError('Renko proof calendar changed')
    registry_file=Path(config['registry'])
    if sha(registry_file.read_bytes())!=config['registry_sha256']:raise ValueError('Renko proof registry changed')
    bars=pd.read_parquet(io.BytesIO(raw));calendar=pd.DatetimeIndex(pd.read_parquet(calendar_file).date)
    registry=json.loads(registry_file.read_text(encoding='utf-8'));funcs=fw.discover();checks=[];started=time.perf_counter()
    reference=config.get('expected_checks',[])
    if reference:validate_checks(reference)
    if list(wt.TIMEFRAMES)!=FRAMES:raise ValueError('Renko frozen timeframe grid differs')
    expected={r['timeframe']:r for r in reference}
    for tf in wt.TIMEFRAMES:
        frame=wt.candle_features(wt.completed_candles(bars,tf,session_calendar=calendar),funcs,timeframe=tf)
        columns=registry[tf]['columns']
        if len(columns)!=1044:raise ValueError('Renko proof requires every1044 registered numeric columns')
        try:receipt=numeric_receipt(frame,columns,expected.get(tf))
        except ValueError:
            observed=numeric_receipt(frame,columns)
            mismatch=dict(ticker=config['ticker'],mode=config['mode'],timeframe=tf,actual=observed,expected=expected.get(tf),
                          module_paths={name:module.__file__ for name,module in sys.modules.items()
                                        if name.startswith(('world_','facets_world')) and getattr(module,'__file__',None)})
            (root/'MISMATCH.json').write_text(json.dumps(mismatch,indent=2)+'\n',encoding='utf-8')
            raise
        receipt['timeframe']=tf
        if config['ticker']=='EQLT':
            if not np.isfinite(frame[['tv_renko_dir','tv_renko_n']].to_numpy(dtype='float64')).all():
                raise ValueError('guarded EQLT Renko became unavailable')
        checks.append(receipt)
        print('RENKO_NUMERIC_FRAME',config['ticker'],tf,receipt['numeric_cells'],flush=True)
    validate_checks(checks)
    result=dict(ticker=config['ticker'],mode=config['mode'],raw_source_sha256=sha(raw),checks=checks,
                seconds=time.perf_counter()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (root/'NUMERIC_PROOF.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


def run(root,request):
    validate_request(request)
    from ci.compact_world_build import snapshot,limited_process
    from ci.release_assets import download_asset,gh_retry,publish_assets
    root.mkdir(parents=True,exist_ok=True)
    def fetch(binding,directory):
        file=download_asset(binding['release'],binding['asset'],directory)
        if sha(file.read_bytes())!=binding['sha256']:raise ValueError('Renko proof source differs: '+binding['asset'])
        return file
    parent_file=fetch(request['parent_proof'],root/'sources');parent=json.loads(parent_file.read_text(encoding='utf-8'))
    if (parent['errors'] or parent['stock_recipe_fingerprint']!=BASE_FINGERPRINT
            or len(parent['samples'])!=3 or {r['ticker'] for r in parent['samples']}!={'MAN','MNTS','EYE'}):
        raise ValueError('Renko parent proof differs')
    for sample in parent['samples']:validate_checks(sample['checks'])
    runtime={name:importlib.metadata.version(name) for name in ('numpy','pandas','pyarrow','TA-Lib')}
    if runtime!=parent['environment']['packages']:raise ValueError('Renko proof runtime differs from original exact reference')
    original,calendar=snapshot(root/'original',dict(inputs_tag=request['inputs_tag'],inputs_sha256=request['inputs_sha256'],
                                                  corrected_commit=BASE_COMMIT,corrected_recipe_fingerprint=BASE_FINGERPRINT))
    inputs=json.loads((root/'original'/'BUILD_INPUTS.json').read_text(encoding='utf-8'))
    old_files={name:(original/name).read_bytes() for name in inputs['recipe_files']};new_files=derive(old_files)
    recipe_metadata=json.loads((REPO/'recipes/renko_zero_step_v1/RECIPE.json').read_text(encoding='utf-8'))
    if fingerprint(new_files)!=request['candidate_fingerprint'] or recipe_metadata['fingerprint']!=request['candidate_fingerprint']:
        raise ValueError('Renko candidate recipe identity differs')
    if sha((REPO/'recipes/renko_zero_step_v1/facets_world.py').read_bytes())!=sha(new_files['facets_world.py']):
        raise ValueError('published Renko override differs from exact frozen patch')
    candidate=root/'candidate';candidate.mkdir(exist_ok=True)
    for name,raw in new_files.items():
        file=candidate/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
    registry=fetch(request['registry'],root/'sources')
    references={r['ticker']:r for r in parent['samples']};results=[];errors=[];assets=[]
    def process(ticker,bars,recipe,mode,expected=()):
        own=root/(ticker.lower()+'_'+mode);own.mkdir(exist_ok=True)
        config=dict(ticker=ticker,bars=str(bars.resolve()),source_sha256=sha(bars.read_bytes()),calendar=str(calendar.resolve()),
                    calendar_sha256=sha(calendar.read_bytes()),registry=str(registry.resolve()),registry_sha256=sha(registry.read_bytes()),
                    mode=mode,expected_checks=list(expected))
        (own/'WORKER.json').write_text(json.dumps(config),encoding='utf-8')
        outcome=limited_process([sys.executable,'-m','ci.renko_zero_step_proof','--directory',str(own.resolve()),
                                 '--worker','--recipe',str(recipe.resolve())],own,request['worker_timeout_seconds'])
        if outcome['reason']:
            mismatch=own/'MISMATCH.json'
            errors.append(dict(ticker=ticker,mode=mode,**outcome,
                               mismatch=json.loads(mismatch.read_text(encoding='utf-8')) if mismatch.exists() else None));return None
        result=json.loads((own/'NUMERIC_PROOF.json').read_text(encoding='utf-8'))
        if (result['ticker']!=ticker or result['mode']!=mode or result['raw_source_sha256']!=config['source_sha256']):
            raise ValueError('Renko worker receipt binding differs')
        validate_checks(result['checks']);results.append(result);return result
    for binding in request['stocks']:
        ticker=binding['ticker']
        if binding['sha256']!=references[ticker]['raw_source_sha256']:raise ValueError('Renko stock sample changed from parent')
        bars=fetch(binding,root/'sources')
        process(ticker,bars,original,'original_reference',references[ticker]['checks'])
        process(ticker,bars,candidate,'candidate_legacy_comparison',references[ticker]['checks'])
    spy=fetch(request['benchmark'],root/'sources')
    if request['benchmark']['sha256']!=parent['etf']['raw_source_sha256']:raise ValueError('Renko benchmark sample changed')
    baseline=process('SPY',spy,original,'original_reference')
    if baseline is not None:process('SPY',spy,candidate,'candidate_legacy_comparison',baseline['checks'])
    target_result=None;answer_result=None
    if not errors:
        target=request['target'];archive=fetch(target['archive'],root/'target_source')
        with tarfile.open(archive) as source:
            raw=source.extractfile(target['member']).read()
        if sha(raw)!=target['member_sha256']:raise ValueError('Renko target raw member differs')
        bars=root/target['member'];bars.write_bytes(raw);assets.append(bars)
        target_result=process('EQLT',bars,candidate,'guarded_target')
        if target_result is not None:
            for name,expected in request['answer_code_sha256'].items():
                if sha((REPO/name).read_bytes())!=expected:raise ValueError('Renko answer worker/encoder differs')
            own=root/'eqlt_answers';own.mkdir(exist_ok=True)
            shutil.copyfile(bars,own/bars.name);shutil.copyfile(calendar,own/'market_sessions.parquet')
            config=dict(samples=[dict(ticker='EQLT',file=bars.name,sha256=sha(raw))],inputs_sha256=request['inputs_sha256'],
                        recipe_fingerprint=request['candidate_fingerprint'],restrict_query_to_source_sessions=True)
            (own/'PROBE_INPUTS.json').write_text(json.dumps(config),encoding='utf-8')
            outcome=limited_process([sys.executable,'-m','ci.compact_world_storage_budget','--directory',str(own.resolve()),
                                     '--worker','--recipe',str(candidate.resolve())],own,request['worker_timeout_seconds'])
            if outcome['reason']:errors.append(dict(ticker='EQLT',mode='packed_answers',**outcome))
            else:
                answer_result=json.loads((own/'COMPACT_STORAGE_WORKER.json').read_text(encoding='utf-8'))
                row=answer_result['samples'][0]
                if (row['ticker']!='EQLT' or row['diagnostic_questions']!=68904 or row['query_rows']!=1712
                        or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'
                        or sha((own/'DIAGNOSTIC_REGISTRIES.json').read_bytes())!=request['diagnostic_registry_sha256']):
                    raise ValueError('Renko guarded answer shape/schema differs')
                payload=own/'45514c54.diagnostic_answers.tar.zst'
                if sha(payload.read_bytes())!=row['answer_container_sha256']:raise ValueError('Renko guarded answer payload differs')
                assets.extend([payload,own/'DIAGNOSTIC_REGISTRIES.json'])
    recipe_file=root/'RENKO_RECIPE_V1.json';recipe_file.write_text(json.dumps(recipe_metadata,indent=2)+'\n',encoding='utf-8')
    override=root/'facets_world_renko_zero_step_v1.py';override.write_bytes(new_files['facets_world.py'])
    complete=(not errors and len(results)==9 and target_result is not None and answer_result is not None
              and {(r['ticker'],r['mode']) for r in results}=={
                  ('MAN','original_reference'),('MNTS','original_reference'),('EYE','original_reference'),
                  ('MAN','candidate_legacy_comparison'),('MNTS','candidate_legacy_comparison'),('EYE','candidate_legacy_comparison'),
                  ('SPY','original_reference'),('SPY','candidate_legacy_comparison'),('EQLT','guarded_target')})
    report=dict(status='RENKO_GUARD_SAMPLE_EXACT_WITH_NEW_TARGET_ONLY' if complete else 'INCOMPLETE_RENKO_GUARD_PROOF',
                source_commit=os.environ['GITHUB_SHA'],request=request,base_fingerprint=BASE_FINGERPRINT,candidate_fingerprint=fingerprint(new_files),
                changed_recipe_files=[n for n in old_files if old_files[n]!=new_files[n]],runtime=runtime,python=sys.version,
                results=results,errors=errors,guarded_answer_result=answer_result,
                original_reference_numeric_cells=sum(c['numeric_cells'] for r in results if r['ticker'] in references and r['mode']=='candidate_legacy_comparison' for c in r['checks']),
                authority='James/Cyrus exact-recompute sample plan; new version for a previously nonterminating input, no published-value replacement.',
                active_runs_untouched=[40621517496,40792865480,40795819366],full_universe_conversion_gate='NOT_RUN',
                full_world_gate='NOT_PROVEN',full_dependency_budget_gate='NOT_PROVEN',scoring_gate='CLOSED',
                retained_assets=[dict(asset=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in [recipe_file,override,*assets]])
    file=root/'RENKO_ZERO_STEP_PROOF_V1.json';file.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    tag=f"renko-zero-step-proof-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
             '--notes','Isolated new float64 Renko recipe, exact legacy3-stock/SPY sample plus guarded EQLT; full world/scoring remain closed.')
    publish_assets(tag,file,recipe_file,override,*assets);gh_retry('release','edit',tag,'--draft=false')
    reread=download_asset(tag,file.name,root/'public-readback')
    if sha(reread.read_bytes())!=sha(file.read_bytes()):raise ValueError('Renko public proof readback differs')
    print('RENKO_ZERO_STEP_PROOF_COMPLETE',tag,report['status'],len(results),flush=True)
    if report['status']=='INCOMPLETE_RENKO_GUARD_PROOF':raise ValueError('Renko exact proof incomplete; original data/runs unchanged')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--worker',action='store_true');parser.add_argument('--recipe',type=Path);args=parser.parse_args()
    if args.worker:numeric_worker(args.directory.resolve(),args.recipe.resolve())
    else:run(args.directory,json.loads(REQUEST.read_text(encoding='utf-8')))

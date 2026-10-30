"""Diagnostic-only numeric/profile/prefix trace; never replace retained values."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

from ci.release_assets import download_asset,gh_retry,publish_assets

ROOT=Path(__file__).resolve().parents[1]
REPLAY=dict(release='row0-part172-replay-measured-v1-41059646552-1',asset='ROW0_PART172_REPLAY_V1.json',
    sha256='0d2067913197775a4a9092fda4cce674cd36caf66ca1637b12bee551e548debf')
INPUTS=dict(release='compact-world-build-v1-41058023781-1-inputs',asset='COMPACT_WORLD_BUILD_PLAN.json',
    sha256='92a327dd424589bf8a7e1b748feac5fecd6475b73bbd893b191ced93e6a9f18a')
TARGETS=('FEIM','HHS','JHI','NKTR','OCGN','ABX','AMTD','CATO','DJCO','BPOP')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def checked(binding,root):
    file=download_asset(binding['release'],binding['asset'],root)
    if sha(file.read_bytes())!=binding['sha256']:raise ValueError('numeric trace source changed: '+binding['asset'])
    return file


def decode_codes(contents,stem,registry):
    import numpy as np
    import pyarrow as pa
    meta=json.loads(contents[stem+'.json']);chunk=contents[stem+'.zst'];schema=registry[meta['registry_sha256']]
    from world_answer_cache import registry_bytes
    if sha(registry_bytes(schema))!=meta['registry_sha256'] or any(q['outcomes']!=[0,1] for q in schema):
        raise ValueError('trace registry differs')
    if len(chunk)!=meta['compressed_bytes'] or sha(chunk)!=meta['compressed_sha256']:raise ValueError('trace compressed chunk differs')
    stride=(meta['rows']+7)//8
    if meta['raw_bytes']!=len(schema)*2*stride or meta['raw_bytes']>1000000:raise ValueError('trace bitplane bound differs')
    raw=bytes(pa.Codec('zstd').decompress(chunk,meta['raw_bytes']))
    if sha(raw)!=meta['raw_sha256']:raise ValueError('trace raw bits differ')
    planes=np.unpackbits(np.frombuffer(raw,dtype=np.uint8).reshape(len(schema),2,stride),axis=2,bitorder='little')
    if planes[:,:,meta['rows']:].any():raise ValueError('trace padding differs')
    codes=planes[:,0,:meta['rows']]+2*planes[:,1,:meta['rows']]
    if (codes>2).any():raise ValueError('trace invalid code')
    return meta,schema,codes


def selectors(old_blob,new_blob,registry,control=False):
    import numpy as np
    from ci.row0_part172_replay import members
    old,new=members(old_blob),members(new_blob)
    if set(old)!=set(new):raise ValueError('trace packet members differ')
    wanted={'RETURN_SKEW20:rising1__1d','HURST_RS20:rising1__1d','HV10:rising1__2d'}
    result=[]
    for name in sorted(n for n in old if n.endswith('.json')):
        a,b=json.loads(old[name]),json.loads(new[name]);stem=name[:-5]
        schema=registry[a['registry_sha256']]
        use_control=control and any(q['question_id'] in wanted for q in schema)
        if a['raw_sha256']==b['raw_sha256'] and not use_control:continue
        ma,sa,ca=decode_codes(old,stem,registry);mb,sb,cb=decode_codes(new,stem,registry)
        pa0=dict(ma['provenance']);pb0=dict(mb['provenance']);pa0.pop('recipe_fingerprint');pb0.pop('recipe_fingerprint')
        if sa!=sb or pa0!=pb0 or ma['rows']!=mb['rows']:raise ValueError('trace row/input/mask binding differs')
        locations=list(zip(*np.where(ca!=cb)))
        if use_control:locations.extend((q,min(217,ma['rows']-1)) for q,row in enumerate(sa) if row['question_id'] in wanted)
        for q,r in locations:
            result.append(dict(question_id=sa[int(q)]['question_id'],query_row=int(r),old_code=int(ca[q,r]),
                               replay_code=int(cb[q,r]),row_keys_sha256=pa0['row_keys_sha256']))
    return result


def prepare(root):
    root.mkdir(parents=True,exist_ok=True)
    old_request=json.loads((ROOT/'ci/TERMINAL_PRICE_RECOVERY_REQUEST.json').read_text(encoding='utf-8'))
    binding=json.loads((ROOT/'docs/COMPOSED_PRICE_DIAGNOSTIC_BINDING_V1.json').read_text(encoding='utf-8'))
    original=json.loads(checked(old_request['base_plan'],root/'original').read_bytes())
    current=json.loads(checked(INPUTS,root/'current').read_bytes())
    composition=json.loads(checked(binding,root/'reference').read_bytes())
    replay=json.loads(checked(REPLAY,root/'replay').read_bytes())
    if replay['completed']!=50 or replay['mismatched_cells']!=166 or replay['errors']:raise ValueError('trace replay counterexample differs')
    part=original['parts'][172]
    if part not in current['parts'] or len(part['tickers'])!=50:raise ValueError('trace source part differs')
    registry_binding=dict(release=INPUTS['release'],asset='DIAGNOSTIC_REGISTRIES.json',sha256=current['request']['registry_sha256'])
    registry_file=checked(registry_binding,root/'registry');registry=json.loads(registry_file.read_bytes())
    refs={r['ticker']:r for r in composition['completed']};new_rows={r['ticker']:r for r in replay['results']};stocks=[]
    for ticker in TARGETS:
        old=refs[ticker];new=new_rows[ticker];index=part['tickers'].index(ticker)//5
        old_file=checked(dict(release=old['release'],asset=old['asset'],sha256=old['answer_container_sha256']),root/'packets'/ticker/'old')
        new_file=checked(dict(release=f'compact-world-build-v1-41059646552-1-{index:03d}',asset=old['asset'],sha256=new['replay_sha256']),root/'packets'/ticker/'new')
        selected=selectors(old_file.read_bytes(),new_file.read_bytes(),registry,ticker in ('DJCO','BPOP'))
        changed=sum(r['old_code']!=r['replay_code'] for r in selected)
        if changed!=new['mismatched_cells'] or not selected:raise ValueError('trace selector coverage differs: '+ticker)
        stocks.append(dict(ticker=ticker,query_rows=old['query_rows'],selectors=selected))
    if sum(sum(r['old_code']!=r['replay_code'] for r in s['selectors']) for s in stocks)!=166:raise ValueError('trace must retain all166 known counterexamples')
    plan=dict(request=current['request'],source_part=part,stocks=stocks,registry_binding=registry_binding,
        scope='DIAGNOSE_ALL_8_MISMATCH_STOCKS_PLUS_2_PREDECLARED_CONTROLS_NOT_A_PRODUCTION_RECIPE_OR_FULL_P4',
        profile_policy='BASELINE_A_AND_B_CLEAN_PROCESSES;NO_NUMPY_DISPATCH;EXACT_PREFIX_COMPARISON',scoring_gate='CLOSED')
    file=root/'NUMERIC_RUNTIME_TRACE_PLAN_V1.json';file.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    tag=f"price-numeric-runtime-trace-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title',tag,
        '--notes','Predeclared diagnostic-only trace of all166 bit counterexamples across8 stocks plus2 matched controls. Existing published bits, recipes, protected run/draft and scoring unchanged.')
    publish_assets(tag,file);gh_retry('release','edit',tag,'--draft=false')
    with open(os.environ['GITHUB_OUTPUT'],'a') as stream:
        stream.write('inputs_release='+tag+'\nplan_sha256='+sha(file.read_bytes())+'\nmatrix='+json.dumps(list(range(10)))+'\n')


def bit_differences(a,b):
    import numpy as np
    if a.shape!=b.shape:raise ValueError('numeric trace shapes differ')
    changed=a.view(np.uint64)!=b.view(np.uint64)
    known=np.isfinite(a)&np.isfinite(b)
    return dict(bit_differences=int(changed.sum()),known_value_differences=int((changed&known).sum()),
                known_missing_differences=int((np.isfinite(a)!=np.isfinite(b)).sum()))


def worker(root,recipe):
    sys.path[:0]=[str(recipe.resolve()),str(ROOT)]
    import contextlib
    import platform
    import numpy as np
    import pandas as pd
    import world_bar_statistics as bs
    import world_timeframes as wt
    for module in (bs,wt):
        if Path(module.__file__).resolve().parent!=recipe.resolve():raise ValueError('numeric trace loaded unbound math')
    config=json.loads((root/'WORKER.json').read_bytes());bars_file=Path(config['bars']);calendar_file=Path(config['calendar'])
    if sha(bars_file.read_bytes())!=config['bars_sha256'] or sha(calendar_file.read_bytes())!=config['calendar_sha256']:
        raise ValueError('numeric trace raw inputs differ')
    bars=pd.read_parquet(bars_file);calendar=pd.DatetimeIndex(pd.read_parquet(calendar_file).date)
    query=calendar[(calendar>=pd.Timestamp('2020-01-01'))&calendar.isin(pd.DatetimeIndex(bars.date))]
    if len(query)!=config['stock']['query_rows']:raise ValueError('numeric trace query count differs')
    row_hash=sha(config['stock']['ticker'].encode()+query.asi8.tobytes())
    if any(s['row_keys_sha256']!=row_hash for s in config['stock']['selectors']):raise ValueError('numeric trace query identities differ')
    cpu=np._core._multiarray_umath
    runtime_text=io.StringIO()
    with contextlib.redirect_stdout(runtime_text):np.show_runtime()
    trace=[];log_arrays=[];results=[];prefixes=[];arrays={};original_np=bs.np
    class Observer:
        def __getattr__(self,key):return getattr(original_np,key)
        def log(self,value,*args,**kwargs):
            result=original_np.log(value,*args,**kwargs)
            if isinstance(value,pd.Series):
                a=value.to_numpy();b=result.to_numpy()
                log_arrays.append(b.copy())
                trace.append(dict(rows=len(a),ratio_sha256=sha(a.tobytes()),log_sha256=sha(b.tobytes()),
                    ratio_alignment64=int(a.ctypes.data%64),ratio_strides=list(a.strides)))
            return result
    bs.np=Observer()
    for tf in sorted({s['question_id'].rsplit('__',1)[1] for s in config['stock']['selectors']}):
        native=wt.completed_candles(bars,tf,session_calendar=calendar)
        inputs=[native[c].to_numpy(dtype=float) for c in wt.PRICE_COLS]
        values=bs.bar_statistics(*inputs,timeframe=tf)
        fields=sorted(values);matrix=np.column_stack([values[k] for k in fields]);arrays[tf]=matrix
        full_log=log_arrays[-1];arrays[tf+'_log_returns']=full_log
        arrays[tf+'_dates']=native.available_from.to_numpy(dtype='datetime64[ns]').view('int64')
        selected=[s for s in config['stock']['selectors'] if s['question_id'].endswith('__'+tf)];cuts=set()
        positions=np.searchsorted(native.available_from.to_numpy(dtype='datetime64[ns]'),query.to_numpy(dtype='datetime64[ns]'),side='right')-1
        for item in selected:
            field,facet=item['question_id'].rsplit('__',1)[0].rsplit(':',1);index=int(positions[item['query_row']])
            result=dict(item,timeframe=tf,native_index=index)
            if field not in values or index<1:
                result.update(status='UNSUPPORTED_OR_INSUFFICIENT',missing=field);results.append(result);continue
            x=pd.Series(values[field]);left=x.iloc[index]
            if facet=='rising1':right=x.shift(1).iloc[index]
            elif facet=='above_mean20':right=x.rolling(20).mean().iloc[index]
            elif facet=='above_mean_plus_sd20':right=(x.rolling(20).mean()+x.rolling(20).std(ddof=0)).iloc[index]
            else:raise ValueError('unbound diagnostic facet')
            code=0 if not np.isfinite([left,right]).all() else 1+int(left>right)
            result.update(status='TRACED',profile_code=code,value_bits=f'{np.float64(left).view(np.uint64):016x}',
                comparison_bits=f'{np.float64(right).view(np.uint64):016x}')
            results.append(result);cuts.update((index+1,min(len(native),index+3)))
        if config['prefix_checks']:
            for length in sorted(cuts):
                shorter=bs.bar_statistics(*(a[:length] for a in inputs),timeframe=tf)
                target=np.column_stack([shorter[k] for k in fields])
                stats=bit_differences(matrix[:length],target)
                by_field={field:int((matrix[:length,j].view(np.uint64)!=target[:,j].view(np.uint64)).sum())
                          for j,field in enumerate(fields) if not np.array_equal(matrix[:length,j].view(np.uint64),target[:,j].view(np.uint64))}
                prefixes.append(dict(timeframe=tf,prefix_native_rows=length,changed_fields=by_field,
                    log_return_prefix=bit_differences(full_log[:length],log_arrays[-1]),**stats))
    bs.np=original_np
    output=dict(ticker=config['stock']['ticker'],profile=config['profile'],runtime=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
        libc=platform.libc_ver(),machine=platform.machine(),cpu_baseline=cpu.__cpu_baseline__,cpu_dispatch=cpu.__cpu_dispatch__,cpu_features=cpu.__cpu_features__,
        disable_cpu_features=os.environ.get('NPY_DISABLE_CPU_FEATURES',''),show_runtime=runtime_text.getvalue()),
        bound_module_sha256={module.__name__:sha(Path(module.__file__).read_bytes()) for module in (bs,wt)},
        observed_log_calls=trace,selectors=results,prefix_checks=prefixes,
        numeric_sha256={key:sha(value.tobytes()) for key,value in arrays.items()},scoring_gate='CLOSED')
    (root/'TRACE.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8');np.savez_compressed(root/'TRACE_VALUES.npz',**arrays)


def run_stock(root,tag,index,pin):
    # Parent may import current math; all measured work runs in fresh children.
    from ci.compact_world_build import snapshot
    from ci.native_price_blocks import read_member
    root.mkdir(parents=True,exist_ok=True)
    plan=json.loads(checked(dict(release=tag,asset='NUMERIC_RUNTIME_TRACE_PLAN_V1.json',sha256=pin),root).read_bytes());stock=plan['stocks'][index]
    recipe,calendar=snapshot(root/'bound',plan['request']);part=plan['source_part']
    manifest=json.loads(download_asset(part['release'],part['part']+'.json',root/'source').read_bytes())
    if manifest['archive_sha256']!=part['archive_sha256'] or manifest['inputs_tag']!=plan['request']['inputs_tag']:raise ValueError('numeric trace raw manifest differs')
    archive=download_asset(part['release'],part['part']+'.tar',root/'source')
    if sha(archive.read_bytes())!=part['archive_sha256']:raise ValueError('numeric trace raw archive differs')
    raw=read_member(archive,manifest,stock['ticker'].encode().hex()+'.bars.parquet');bars=root/'bars.parquet';bars.write_bytes(raw)
    command=[sys.executable,'-c','import json,numpy as n;u=n._core._multiarray_umath;print(json.dumps([x for x in u.__cpu_dispatch__ if u.__cpu_features__.get(x)]))']
    dispatch=json.loads(subprocess.check_output(command,text=True));profiles={}
    for profile in ('baseline_a','baseline_b','no_numpy_dispatch'):
        own=root/profile;own.mkdir(exist_ok=True);config=dict(stock=stock,bars=str(bars.resolve()),bars_sha256=sha(raw),calendar=str(calendar.resolve()),
            calendar_sha256=sha(calendar.read_bytes()),profile=profile,prefix_checks=True)
        (own/'WORKER.json').write_text(json.dumps(config),encoding='utf-8');env=dict(os.environ)
        if profile=='no_numpy_dispatch':env['NPY_DISABLE_CPU_FEATURES']=','.join(dispatch)
        subprocess.run([sys.executable,'-m','ci.price_numeric_runtime_trace','worker','--directory',str(own.resolve()),'--recipe',str(recipe.resolve())],
            check=True,timeout=600,env=env)
        profiles[profile]=json.loads((own/'TRACE.json').read_bytes())
    import numpy as np
    comparisons=[]
    with np.load(root/'baseline_a/TRACE_VALUES.npz',allow_pickle=False) as a:
        for profile in ('baseline_b','no_numpy_dispatch'):
            with np.load(root/profile/'TRACE_VALUES.npz',allow_pickle=False) as b:
                comparisons.append(dict(profile=profile,by_array={key:bit_differences(a[key],b[key]) for key in a.files if not key.endswith('_dates')}))
    result=dict(status='DIAGNOSTIC_COMPLETE_NOT_A_FIX_OR_P4_APPROVAL',source_commit=os.environ['GITHUB_SHA'],ticker=stock['ticker'],
        plan_sha256=pin,profiles=profiles,profile_comparisons=comparisons,scoring_gate='CLOSED',production_changes='NONE')
    file=root/'NUMERIC_RUNTIME_STOCK_TRACE_V1.json';file.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    release=f"price-numeric-runtime-trace-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
    gh_retry('release','create',release,'--draft','--target',os.environ['GITHUB_SHA'],'--title',release);publish_assets(release,file)
    gh_retry('release','edit',release,'--draft=false');print('NUMERIC_RUNTIME_TRACE_COMPLETE',stock['ticker'],flush=True)


def finalize(root,tag,pin):
    root.mkdir(parents=True,exist_ok=True);plan=json.loads(checked(dict(release=tag,asset='NUMERIC_RUNTIME_TRACE_PLAN_V1.json',sha256=pin),root).read_bytes())
    rows=[];errors=[]
    for index,stock in enumerate(plan['stocks']):
        release=f"price-numeric-runtime-trace-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:03d}"
        try:
            file=download_asset(release,'NUMERIC_RUNTIME_STOCK_TRACE_V1.json',root/str(index));doc=json.loads(file.read_bytes())
            if doc['ticker']!=stock['ticker'] or doc['source_commit']!=os.environ['GITHUB_SHA'] or doc['plan_sha256']!=pin:raise ValueError('trace result identity differs')
            rows.append(dict(ticker=stock['ticker'],release=release,sha256=sha(file.read_bytes()),
                baseline_repeat_bit_differences=sum(r['bit_differences'] for r in doc['profile_comparisons'][0]['by_array'].values()),
                dispatch_bit_differences=sum(r['bit_differences'] for r in doc['profile_comparisons'][1]['by_array'].values()),
                baseline_prefix_bit_differences=sum(r['bit_differences'] for r in doc['profiles']['baseline_a']['prefix_checks']),
                selector_codes={p:dict(old_matches=sum(s.get('profile_code')==s['old_code'] for s in d['selectors']),replay_matches=sum(s.get('profile_code')==s['replay_code'] for s in d['selectors']),total=len(d['selectors'])) for p,d in doc['profiles'].items()}))
        except Exception as exc:errors.append(dict(ticker=stock['ticker'],error=str(exc)))
    result=dict(status='DIAGNOSTIC_COMPLETE' if len(rows)==10 and not errors else 'DIAGNOSTIC_INCOMPLETE',source_commit=os.environ['GITHUB_SHA'],
        plan_sha256=pin,results=rows,errors=errors,cause='REQUIRES_REVIEW_OF_PROFILE_AND_PREFIX_TRACES',production_changes='NONE',scoring_gate='CLOSED')
    file=root/'NUMERIC_RUNTIME_TRACE_V1.json';file.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    release=f"price-numeric-runtime-trace-measured-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release','create',release,'--draft','--target',os.environ['GITHUB_SHA'],'--title',release);publish_assets(release,file);gh_retry('release','edit',release,'--draft=false')
    print(json.dumps(result),flush=True)
    if errors:raise ValueError('numeric trace incomplete; evidence retained')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('prepare','worker','stock','finalize'));parser.add_argument('--directory',required=True)
    parser.add_argument('--recipe',type=Path);parser.add_argument('--inputs-release');parser.add_argument('--index',type=int);parser.add_argument('--plan-sha256')
    args=parser.parse_args();root=Path(args.directory)
    if args.operation=='prepare':prepare(root)
    elif args.operation=='worker':worker(root,args.recipe)
    elif args.operation=='stock':run_stock(root,args.inputs_release,args.index,args.plan_sha256)
    else:finalize(root,args.inputs_release,args.plan_sha256)

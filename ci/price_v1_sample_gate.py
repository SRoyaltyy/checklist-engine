"""Owner-scoped row-0 measurement, with predeclared100-name all-column PIT sample."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
PLAN=dict(release='compact-world-build-v1-41071592258-1-inputs',asset='COMPACT_WORLD_BUILD_PLAN.json',
          sha256='b6258f6e57587d88f15088d2750153b6a8a926ab702bc6b7082bec0ffe4a0c8c')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def scope():return json.loads((ROOT/'dictionary/PRICE_V1_SCOPE_V1.json').read_text(encoding='utf-8'))


def select(names,policy):
    if len(names)!=len(set(names)) or len(names)!=8439:raise ValueError('sample requires exact retained cohort')
    seed=policy['sample_seed']
    return sorted(names,key=lambda t:(sha((seed+t).encode()),t))[:policy['sample_size']]


def compare(a,b):
    import numpy as np
    a=np.asarray(a,dtype='float64');b=np.asarray(b,dtype='float64')
    if a.shape!=b.shape:raise ValueError('prefix shapes differ')
    known_a=~np.isnan(a);known_b=~np.isnan(b)
    changed=(known_a!=known_b)|(known_a&known_b&(a.view(np.uint64)!=b.view(np.uint64)))
    return dict(cells=int(a.size),different_cells=int(changed.sum()),
                missing_differences=int((known_a!=known_b).sum()),example_indices=np.flatnonzero(changed)[:5].tolist())


def align_prefix(expected,rebuilt):
    import pandas as pd
    a=pd.DatetimeIndex(expected.available_from).as_unit('ns');b=pd.DatetimeIndex(rebuilt.available_from).as_unit('ns')
    if a.has_duplicates or b.has_duplicates:raise ValueError('duplicate prefix availability')
    differences=[]
    if not a.equals(b):
        differences=[dict(field='available_from',different_cells=len(a.symmetric_difference(b)),
            expected_only=[str(d) for d in a.difference(b)[:5]],rebuilt_only=[str(d) for d in b.difference(a)[:5]])]
    common=a.intersection(b)
    return expected.set_index('available_from').reindex(common),rebuilt.set_index('available_from').reindex(common),differences


def checked(binding,root):
    from ci.release_assets import download_asset
    file=download_asset(binding['release'],binding['asset'],root/binding['release'])
    if sha(file.read_bytes())!=binding['sha256']:raise ValueError('sample source binding differs')
    return file


def publish(tag,files,note):
    from ci.release_assets import gh_retry,publish_assets
    gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],'--notes',note)
    publish_assets(tag,*files);gh_retry('release','edit',tag,'--draft=false')


def prepare(root):
    from world_replay_quarantine import load_policy,filter_parts
    policy=scope();plan=json.loads(checked(PLAN,root).read_bytes());quarantine=load_policy()
    expected,_=filter_parts(plan['raw_source_parts'],quarantine)
    if (plan['parts']!=expected or plan['accepted_tickers']!=8439
        or plan['request']['registry_sha256']!=policy['registry_sha256']):raise ValueError('current cohort/schema differs')
    registry_file=checked(dict(release=PLAN['release'],asset='DIAGNOSTIC_REGISTRIES.json',sha256=policy['registry_sha256']),root)
    registry=json.loads(registry_file.read_bytes());questions=[q for rows in registry.values() for q in rows]
    fields=sorted({q['question_id'].split(':',1)[0] for q in questions})
    ids=[q['question_id'] for q in questions]
    if len(ids)!=68904 or len(set(ids))!=68904 or len(fields)!=1044 or set(fields)&set(policy['deferred_fields']):raise ValueError('produced/deferred registry differs')
    names=[t for part in plan['parts'] for t in part['tickers']];sample=select(names,policy)
    result=dict(format='PRICE_V1_SAMPLE_PLAN_V1',source_plan=PLAN,request=plan['request'],scope=policy,
        cohort_names=names,sample=sample,price_fields=fields,parts=plan['parts'],original_universe=8727,
        source_coverage_pct=100*len(names)/8727,quarantine_names=sorted(r['ticker'] for r in quarantine['records']),
        timeframes=[str(i)+'d' for i in range(1,22)]+['monthly'],
        source_commit=os.environ['GITHUB_SHA'])
    file=root/'PRICE_V1_SAMPLE_PLAN_V1.json';write(file,result)
    tag=f"price-v1-sample-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-inputs"
    publish(tag,[file,ROOT/'dictionary/PRICE_V1_SCOPE_V1.json'],'Predeclared100-name sample, all1044 produced price fields/22 native timeframes; nine explicit DEFERRED_V2_FIELD fields. No protected producer mutation.')
    with open(os.environ['GITHUB_OUTPUT'],'a') as out:
        out.write('inputs_release='+tag+'\nplan_sha256='+sha(file.read_bytes())+'\nmatrix='+json.dumps(list(range(10)))+'\n')


def worker(root,recipe):
    sys.path[:0]=[str(recipe.resolve()),str(ROOT)]
    import numpy as np
    import pandas as pd
    import facets_world as fw
    import world_timeframes as wt
    if any(Path(m.__file__).resolve().parent!=recipe.resolve() for m in (fw,wt)):raise ValueError('unbound price math')
    config=json.loads((root/'WORKER.json').read_bytes())
    bars_file=root/'bars.parquet';calendar_file=root/'market_sessions.parquet'
    if sha(bars_file.read_bytes())!=config['bars_sha256'] or sha(calendar_file.read_bytes())!=config['calendar_sha256']:
        raise ValueError('price sample raw/calendar differs')
    bars=pd.read_parquet(bars_file);calendar=pd.DatetimeIndex(pd.read_parquet(calendar_file).date)
    funcs=fw.discover();coverage=[];checks=[]
    for tf in wt.TIMEFRAMES:
        native=wt.completed_candles(bars,tf,session_calendar=calendar)
        full=wt.candle_features(native,funcs,timeframe=tf)
        fields=sorted(c for c in full if c!='available_from')
        if len(full) and fields!=config['price_fields']:raise ValueError('sample produced schema differs: '+tf)
        if len(full) and not (native.date.to_numpy()<full.available_from.to_numpy()).all():raise ValueError('source candle not before availability')
        for field in config['price_fields']:
            values=full[field] if field in full else pd.Series(dtype=float)
            valid=values.notna();dates=full.loc[valid,'available_from'] if len(full) else pd.Series(dtype='datetime64[ns]')
            coverage.append(dict(timeframe=tf,field=field,rows=len(full),nonblank=int(valid.sum()),
                infinite=int(np.isinf(values.to_numpy(dtype=float)).sum()),
                first=str(dates.min())[:10] if len(dates) else '',last=str(dates.max())[:10] if len(dates) else ''))
        for cut in config['prefix_cuts']:
            cut=pd.Timestamp(cut);prior=bars[bars.date<cut];cal=calendar[calendar<=cut]
            candles=wt.completed_candles(prior,tf,session_calendar=cal)
            rebuilt=wt.candle_features(candles,funcs,timeframe=tf)
            expected=full[full.available_from<=cut].reset_index(drop=True)
            if len(rebuilt) and sorted(c for c in rebuilt if c!='available_from')!=fields:raise ValueError('sample prefix schema differs')
            expected,rebuilt,differences=align_prefix(expected,rebuilt);cells=0
            for field in fields if len(expected) else []:
                stats=compare(expected[field],rebuilt[field]);cells+=stats['cells']
                if stats['different_cells']:differences.append(dict(field=field,**stats))
            checks.append(dict(timeframe=tf,cut=str(cut.date()),rows=len(rebuilt),columns=len(fields),cells=cells,differences=differences))
        print('PRICE_SAMPLE_TIMEFRAME',config['ticker'],tf,len(full),flush=True)
    result=dict(ticker=config['ticker'],raw_sha256=config['bars_sha256'],calendar_sha256=config['calendar_sha256'],
        recipe_fingerprint=config['recipe_fingerprint'],coverage=coverage,checks=checks,
        runtime=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__),
        status='FAIL_OBSERVED_PREFIX_DIFFERENCES' if any(c['differences'] for c in checks) else 'PASS_SAMPLE_ONLY')
    with gzip.open(root/'STOCK_PRICE_SAMPLE_V1.json.gz','wt',encoding='utf-8') as out:json.dump(result,out,allow_nan=False)


def chunk(root,inputs,index,pin):
    import shutil
    from ci.compact_world_build import snapshot
    from ci.native_price_blocks import read_member
    from ci.release_assets import download_asset
    plan=json.loads(checked(dict(release=inputs,asset='PRICE_V1_SAMPLE_PLAN_V1.json',sha256=pin),root).read_bytes())
    recipe,calendar=snapshot(root,plan['request']);wanted=plan['sample'][index*10:(index+1)*10]
    records=[];files=[]
    for part in plan['parts']:
        names=[t for t in wanted if t in part['tickers']]
        if not names:continue
        source=root/'source'/sha(part['release'].encode())
        manifest=json.loads(download_asset(part['release'],part['part']+'.json',source).read_bytes())
        archive=download_asset(part['release'],part['part']+'.tar',source)
        if manifest['archive_sha256']!=part['archive_sha256'] or sha(archive.read_bytes())!=part['archive_sha256']:raise ValueError('sample archive differs')
        for ticker in names:
            own=root/ticker.encode().hex();own.mkdir(exist_ok=True)
            raw=read_member(archive,manifest,ticker.encode().hex()+'.bars.parquet');(own/'bars.parquet').write_bytes(raw)
            shutil.copyfile(calendar,own/'market_sessions.parquet')
            write(own/'WORKER.json',dict(ticker=ticker,bars_sha256=sha(raw),calendar_sha256=sha(calendar.read_bytes()),
                price_fields=plan['price_fields'],prefix_cuts=plan['scope']['prefix_cuts'],recipe_fingerprint=plan['request']['corrected_recipe_fingerprint']))
            subprocess.run([sys.executable,'-m','ci.price_v1_sample_gate','worker','--directory',str(own.resolve()),'--recipe',str(recipe.resolve())],check=True,timeout=600)
            file=own/'STOCK_PRICE_SAMPLE_V1.json.gz'
            with gzip.open(file,'rt',encoding='utf-8') as stream:stock=json.load(stream)
            records.append(dict(ticker=ticker,status=stock['status'],asset=ticker.encode().hex()+'.sample.json.gz',sha256=sha(file.read_bytes())))
            dest=root/records[-1]['asset'];shutil.copyfile(file,dest);files.append(dest)
            (own/'bars.parquet').unlink()
        archive.unlink()
    if set(r['ticker'] for r in records)!=set(wanted):raise ValueError('sample chunk incomplete')
    file=root/'PRICE_SAMPLE_CHUNK_V1.json';write(file,dict(plan_sha256=pin,records=records))
    tag=f"price-v1-sample-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:02d}"
    publish(tag,[file,*files],'Actual all-column native price coverage and exact prefix measurements; sample only, no full P4 claim.')


def verdict(plan,stocks):
    if len(stocks)!=100 or {s['ticker'] for s in stocks}!=set(plan['sample']):raise ValueError('all100 predeclared samples required')
    grid={(tf,field) for tf in plan['timeframes'] for field in plan['price_fields']}
    cuts={(tf,cut) for tf in plan['timeframes'] for cut in plan['scope']['prefix_cuts']}
    for stock in stocks:
        if (len(stock['coverage'])!=len(grid) or {(r['timeframe'],r['field']) for r in stock['coverage']}!=grid
            or len(stock['checks'])!=len(cuts) or {(r['timeframe'],r['cut']) for r in stock['checks']}!=cuts):
            raise ValueError('sample all-column/timeframe/cut measurement incomplete')
        for row in stock['checks']:
            if row['rows'] and (row['columns']!=len(plan['price_fields']) or row['cells']!=row['rows']*row['columns']):
                raise ValueError('sample prefix comparison incomplete')
    failures=[dict(ticker=s['ticker'],timeframe=c['timeframe'],cut=c['cut'],differences=c['differences'])
              for s in stocks for c in s['checks'] if c['differences']]
    return dict(format='ROW0_PRICE_WORLD_GATE_V2',authority_commit=plan['scope']['authority_commit'],
        price_v1_gate='FAIL' if failures or plan['source_coverage_pct']<95 else 'PASS',
        retained_names=8439,original_universe=8727,source_coverage_pct=plan['source_coverage_pct'],
        sample_names=plan['sample'],sample_stocks=100,price_columns_per_timeframe=len(plan['price_fields']),
        native_timeframes=22,cut_checks=sum(len(s['checks']) for s in stocks),
        compared_cells=sum(c['cells'] for s in stocks for c in s['checks']),
        prefix_mismatch_blocks=len(failures),prefix_failures=failures,
        deferred_fields={f:'DEFERRED_V2_FIELD' for f in plan['scope']['deferred_fields']},
        nonprice_families='DEFERRED_V2',existing_eligibility_mask='UNCHANGED_NOT_REPLACED_BY_ALL_TRUE',
        full_cohort_price_PIT='UNMEASURED_NOT_A_ROW0_BLOCKER_UNDER_OWNER_SCOPE',
        complete_world_and_canonical_answers='DOWNSTREAM_INCOMPLETE',scoring_gate='CLOSED',
        rebuild_handoff='REQUEST_TASKFORCE_IF_PASS' if not failures and plan['source_coverage_pct']>=95 else 'NOT_REQUESTED_OBSERVED_PRICE_FAILURE',protected_source_mutations='NONE')


def finalize(root,inputs,pin):
    plan=json.loads(checked(dict(release=inputs,asset='PRICE_V1_SAMPLE_PLAN_V1.json',sha256=pin),root).read_bytes());stocks=[];bindings=[]
    for index in range(10):
        tag=f"price-v1-sample-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}-{index:02d}"
        from ci.release_assets import download_asset
        chunk=json.loads(download_asset(tag,'PRICE_SAMPLE_CHUNK_V1.json',root/tag).read_bytes())
        if chunk['plan_sha256']!=pin:raise ValueError('sample chunk plan differs')
        for record in chunk['records']:
            file=checked(dict(release=tag,asset=record['asset'],sha256=record['sha256']),root)
            with gzip.open(file,'rt',encoding='utf-8') as stream:stock=json.load(stream)
            if stock['ticker']!=record['ticker'] or stock['recipe_fingerprint']!=plan['request']['corrected_recipe_fingerprint']:raise ValueError('sample body binding differs')
            stocks.append(stock);bindings.append(dict(release=tag,**record))
    report=verdict(plan,stocks);report.update(run=int(os.environ['GITHUB_RUN_ID']),source_commit=os.environ['GITHUB_SHA'],plan_sha256=pin,stock_bindings=bindings)
    totals={}
    for stock in stocks:
        for row in stock['coverage']:
            key=row['timeframe'],row['field'];out=totals.setdefault(key,dict(timeframe=key[0],field=key[1],rows=0,nonblank=0,infinite=0,first='',last=''))
            for name in ('rows','nonblank','infinite'):out[name]+=row[name]
            if row['first']:out['first']=min(out['first'],row['first']) if out['first'] else row['first']
            if row['last']:out['last']=max(out['last'],row['last'])
    coverage=root/'PRICE_V1_SAMPLE_COVERAGE_V1.csv.gz'
    with gzip.open(coverage,'wt',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['timeframe','field','rows','nonblank','infinite','first','last','nonblank_pct']);writer.writeheader()
        for key in sorted(totals):
            row=totals[key];writer.writerow(dict(row,nonblank_pct=100*row['nonblank']/row['rows'] if row['rows'] else 'UNMEASURED'))
    report['coverage_rows']=len(totals);report['zero_nonblank_field_timeframes']=[dict(timeframe=k[0],field=k[1]) for k,r in totals.items() if not r['nonblank']]
    report['coverage_sha256']=sha(coverage.read_bytes());file=root/'ROW0_PRICE_WORLD_GATE_V2.json';write(file,report)
    tag=f"row0-price-world-gate-v2-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    publish(tag,[file,coverage,ROOT/'dictionary/PRICE_V1_SCOPE_V1.json'],'Owner0b57c09 price-only row-0 gate:100 predeclared stocks, all produced price columns, actual coverage and exact two-cut prefix measurements. Read verdict; not full-world/P4/scoring approval.')
    print('ROW0_PRICE_WORLD_GATE_V2',report['price_v1_gate'],report['compared_cells'],report['prefix_mismatch_blocks'],flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','chunk','worker','finalize']);parser.add_argument('--directory',required=True)
    parser.add_argument('--inputs-release');parser.add_argument('--index',type=int);parser.add_argument('--plan-sha256');parser.add_argument('--recipe')
    args=parser.parse_args();root=Path(args.directory).resolve();root.mkdir(parents=True,exist_ok=True)
    if args.action=='prepare':prepare(root)
    elif args.action=='worker':worker(root,Path(args.recipe))
    elif args.action=='chunk':chunk(root,args.inputs_release,args.index,args.plan_sha256)
    else:raise SystemExit(0 if finalize(root,args.inputs_release,args.plan_sha256)['price_v1_gate']=='PASS' else 1)

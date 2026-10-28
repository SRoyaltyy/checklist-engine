"""P3b structural + measured-answer gate. This is not a probability miner.

Questions and answer tallies are streamed CSVs. No empirical PASS is possible
without a provenance-bound 200-stock, 2020-2022 sample. Coverage is by item,
facet, derivative, candle size, lookback, threshold and both directions.
"""
import argparse,csv,gzip,hashlib,itertools,json,re,statistics
from datetime import date
from collections import Counter,defaultdict
from pathlib import Path
CORE_FACETS=('absolute','own_history','peer_relative','position','direction','crossing','extremes','divergence','persistence','state_change')
REQUIRED=('question_id','item_id','block','derivative','facet','candle_days','lookback','threshold','direction','formula','inputs','pit_rule','answer_set')
OPPOSITES=({'above','below'},{'up','down'},{'buy','sell'},{'upgrade','downgrade'},{'present','absent'},{'positive','negative'})


def rows(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',encoding='utf-8-sig',newline='') as stream:yield from csv.DictReader(stream)


def tree_digest(files):
    digest=hashlib.sha256()
    for file in sorted(files,key=str):
        with open(file,'rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def variable_digest(variables):
    return hashlib.sha256(json.dumps(variables,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def outcome_keys(text):
    values=json.loads(text)
    if not isinstance(values,list) or not values or any(type(v) not in (str,int,float,bool) for v in values):
        raise ValueError('fixed non-null scalar answer set required')
    keys=[json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False) for v in values]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate answer outcomes')
    numbers=[v for v in values if type(v) in (int,float)]
    if len(numbers)!=len(set(numbers)):raise ValueError('duplicate numeric answer outcomes')
    return set(keys)


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key '+key)
        result[key]=value
    return result


def sample_evidence(sample,file):
    errors=[]
    if file is None:return ['sample stock-day evidence missing']
    if sample.get('sample_rows_sha256')!=tree_digest([file]):errors.append('sample stock-day fingerprint differs')
    keys=set();tickers=set();years=set()
    try:
        for row in rows(file):
            ticker=row['ticker'];day=date.fromisoformat(row['date'])
            if not ticker.strip() or row['date']!=day.isoformat():raise ValueError('noncanonical stock-day key')
            key=(ticker,day)
            if key in keys:errors.append('duplicate sample stock-day')
            keys.add(key);tickers.add(ticker);years.add(day.year)
        if tickers!=set(sample.get('tickers',[])):errors.append('sample stock-day ticker membership differs')
        if years!=set(sample.get('years',[])):errors.append('sample stock-day year membership differs')
        if len(keys)!=sample.get('rows'):errors.append('sample stock-day row count differs')
    except (KeyError,ValueError,TypeError) as exc:errors.append('invalid sample stock-day evidence: '+str(exc))
    return errors


def evaluate(catalog,tree_files,tally_files,sample,exemptions=(),variables=(),sample_rows=None):
    items={r['item_id']:r for r in catalog}
    exemption={(r['item_id'],r['facet']):r['reason'].strip() for r in exemptions if r.get('reason','').strip()}
    fail=defaultdict(set);facets=defaultdict(Counter);grid=defaultdict(lambda:defaultdict(set))
    count=Counter();qids=set();formulas=set();owners={};tallies={};declared={}
    global_errors=sample_evidence(sample,sample_rows)
    if len(items)!=len(catalog):global_errors.append('duplicate catalog item')
    if any(not r.get('item_id') or not r.get('block') or type(r.get('is_price_volume')) is not bool for r in catalog):
        global_errors.append('invalid catalog metadata')
    if not variables:global_errors.append('declared variable grid missing')
    if sample.get('variable_grid_sha256')!=variable_digest(variables):global_errors.append('sample variable grid fingerprint differs')
    if sample.get('tallies_sha256')!=tree_digest(tally_files):global_errors.append('sample tally fingerprint differs')
    seen_exemptions=set()
    for entry in exemptions:
        key=(entry.get('item_id'),entry.get('facet'))
        if key in seen_exemptions or key[0] not in items or key[1] not in CORE_FACETS or not entry.get('reason','').strip():
            global_errors.append('invalid or duplicate semantic exemption')
        seen_exemptions.add(key)
    for spec in variables:
        try:
            key=(spec['item_id'],spec['facet'],spec['derivative'])
            windows=spec['lookbacks'];thresholds=spec['thresholds'];directions=spec['directions']
            valid=(all(isinstance(v,str) and v.strip() for v in key) and key[0] in items and key[1] in CORE_FACETS and
                   all(isinstance(axis,list) for axis in (windows,thresholds,directions)) and
                   len(windows)>=3 and all(type(n) is int and n>0 for n in windows) and len(set(windows))==len(windows) and
                   len(thresholds)>=3 and all(isinstance(t,str) and t.strip() for t in thresholds) and len(set(thresholds))==len(thresholds) and
                   len(set(directions))==len(directions) and any(pair<=set(directions) for pair in OPPOSITES))
            if not valid or key in declared:raise ValueError('invalid or duplicate declared variable grid')
            declared[key]=(set(windows),set(thresholds),set(directions))
        except (KeyError,TypeError,ValueError) as exc:global_errors.append('invalid declared grid: '+str(exc))
    for file in tally_files:
        for row in rows(file):
            qid=row.get('question_id','')
            if qid in tallies:global_errors.append('duplicate tally '+qid)
            try:
                outcomes=json.loads(row['answer_counts'],object_pairs_hook=unique_object)
                if not isinstance(outcomes,dict) or any(type(v) is not int or v<0 for v in outcomes.values()):raise ValueError('noninteger/negative answer count')
                if not re.fullmatch(r'[0-9]+',row['n_total']):raise ValueError('invalid n_total')
                total=int(row['n_total']);nonblank=sum(outcomes.values())
            except (KeyError,ValueError,TypeError) as exc:
                global_errors.append('invalid answer tally '+qid+': '+str(exc));continue
            if sample.get('rows') and total!=int(sample['rows']):global_errors.append('tally does not cover the declared sample '+qid)
            if nonblank>total:
                global_errors.append('invalid answer counts '+qid)
            tallies[qid]=(100*nonblank/total if total else 0,len([v for v in outcomes.values() if v>0])<=1,set(outcomes))
    for file in tree_files:
        for row in rows(file):
            iid=row.get('item_id','');qid=row.get('question_id','')
            if iid not in items:global_errors.append('unknown item '+iid);continue
            missing=[k for k in REQUIRED if not str(row.get(k,'')).strip()]
            if missing:fail[iid].add('blank metadata: '+','.join(missing));continue
            if row['block']!=items[iid]['block']:fail[iid].add('question block differs from catalog')
            try:allowed=outcome_keys(row['answer_set'])
            except (ValueError,TypeError):fail[iid].add('invalid fixed answer set');allowed=set()
            if qid in qids:fail[iid].add('duplicate question id')
            qids.add(qid);owners[qid]=iid
            formula=hashlib.sha256(row['formula'].strip().encode()).hexdigest()
            if formula in formulas:fail[iid].add('duplicate formula')
            formulas.add(formula)
            facet=row['facet'];facets[iid][facet]+=1;count[iid]+=1
            try:k=int(row['candle_days']);n=int(row['lookback'])
            except ValueError:fail[iid].add('non-integer candle/lookback');continue
            if k not in range(1,22) or n<1:fail[iid].add('invalid candle/lookback')
            cell=grid[(iid,facet,row['derivative'],k)]
            cell['windows'].add(n);cell['thresholds'].add(row['threshold']);cell['directions'].add(row['direction'])
            if (n,row['threshold'],row['direction']) in cell['combinations']:fail[iid].add('duplicate variable combination')
            cell['combinations'].add((n,row['threshold'],row['direction']))
            spec=declared.get((iid,facet,row['derivative']))
            if spec is None:fail[iid].add('question has no declared variable grid')
            elif n not in spec[0] or row['threshold'] not in spec[1] or row['direction'] not in spec[2]:fail[iid].add('question outside declared variable grid')
            if qid not in tallies:fail[iid].add('missing measured answer tally')
            else:
                pct,constant,outcomes=tallies[qid]
                if not outcomes<=allowed:fail[iid].add('measured outcome outside fixed answer set')
                if pct<1:fail[iid].add('question >99% blank')
                if constant:fail[iid].add('constant question')
    if len(set(sample.get('tickers',[])))<200:global_errors.append('sample contains fewer than 200 unique stocks')
    if set(sample.get('years',[]))!={2020,2021,2022}:global_errors.append('sample years must be 2020-2022')
    if int(sample.get('rows',0))<len(set(sample.get('tickers',[]))):global_errors.append('sample row count is smaller than its stock count')
    if not re.fullmatch(r'[0-9a-f]{64}',str(sample.get('input_manifest_sha256',''))):global_errors.append('sample input provenance missing or invalid')
    if sample.get('question_tree_sha256')!=tree_digest(tree_files):global_errors.append('sample is not bound to this exact question tree')
    if set(tallies)-qids:global_errors.append('tallies contain unknown question IDs')
    for iid,item in items.items():
        derivatives={key[2] for key in grid if key[0]==iid}|{key[2] for key in declared if key[0]==iid}
        if not derivatives:fail[iid].add('no derivative questions')
        for facet in CORE_FACETS:
            if facets[iid][facet]==0:
                if not exemption.get((iid,facet)):fail[iid].add('missing facet '+facet)
                continue
            for derivative in derivatives:
                for k in range(1,22):
                    cell=grid.get((iid,facet,derivative,k),{})
                    if len(cell.get('windows',()))<3:fail[iid].add(f'{facet}: fewer than 3 windows / missing derivative-candle cell')
                    if len(cell.get('thresholds',()))<3:fail[iid].add(f'{facet}: fewer than 3 thresholds/settings')
                    if not any(pair<=cell.get('directions',set()) for pair in OPPOSITES):fail[iid].add(f'{facet}: missing opposite direction')
                    spec=declared.get((iid,facet,derivative))
                    if spec is not None and any(combination not in cell.get('combinations',set()) for combination in itertools.product(*spec)):
                        fail[iid].add(f'{facet}: incomplete declared variable cross-product')
    price=[count[iid] for iid,item in items.items() if item.get('is_price_volume')]
    reference=statistics.median(price) if price else 0
    block_counts=defaultdict(list)
    for iid,item in items.items():block_counts[item['block']].append(count[iid])
    block_ratios={block:statistics.median(values)/reference if reference else 0 for block,values in block_counts.items()}
    output=[]
    for iid,item in items.items():
        measured=[tallies[q] for q,owner in owners.items() if owner==iid and q in tallies]
        ratio=block_ratios[item['block']]
        if not item.get('is_price_volume') and ratio<.5:fail[iid].add('block median depth below 50% of price/volume')
        if global_errors:fail[iid].update(global_errors)
        output.append(dict(item_id=iid,block=item['block'],facets_covered=sum(facets[iid][f]>0 or bool(exemption.get((iid,f))) for f in CORE_FACETS),
            facets_total=len(CORE_FACETS),question_count=count[iid],median_non_blank_pct=statistics.median(x[0] for x in measured) if measured else 0,
            constant_pct=100*sum(x[1] for x in measured)/len(measured) if measured else 100,
            depth_ratio_vs_price_median=ratio,status='FAIL' if fail[iid] else 'PASS',reasons='; '.join(sorted(fail[iid]))))
    return output,dict(facets),global_errors


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--catalog',required=True);ap.add_argument('--tree',nargs='+',required=True)
    ap.add_argument('--tallies',nargs='*',default=[]);ap.add_argument('--sample',required=True)
    ap.add_argument('--exemptions');ap.add_argument('--variables',required=True);ap.add_argument('--sample-rows',required=True)
    ap.add_argument('--out',required=True);args=ap.parse_args()
    catalog=json.loads(Path(args.catalog).read_text(encoding='utf-8'));sample=json.loads(Path(args.sample).read_text(encoding='utf-8'))
    exemptions=list(rows(args.exemptions)) if args.exemptions else []
    variables=json.loads(Path(args.variables).read_text(encoding='utf-8'))
    report,facets,errors=evaluate(catalog,args.tree,args.tallies,sample,exemptions,variables,args.sample_rows)
    target=Path(args.out);target.mkdir(parents=True,exist_ok=True)
    with open(target/'QUESTION_QUALITY.csv','w',encoding='utf-8',newline='') as stream:
        fields=list(report[0]) if report else ['item_id','block','status','reasons']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(report)
    (target/'QUESTION_FACET_COUNTS.json').write_text(json.dumps(facets,indent=2))
    summary=dict(items=len(report),passed=sum(r['status']=='PASS' for r in report),failed=sum(r['status']=='FAIL' for r in report),global_errors=errors)
    summary['status']='FAIL' if summary['failed'] or errors or not report else 'PASS'
    summary['evidence']=dict(gate_code_sha256=tree_digest([__file__]),
        sample_manifest_sha256=tree_digest([args.sample]),sample_rows_sha256=tree_digest([args.sample_rows]),
        question_tree_sha256=tree_digest(args.tree),tallies_sha256=tree_digest(args.tallies),
        variable_grid_sha256=variable_digest(variables),input_manifest_sha256=sample.get('input_manifest_sha256'))
    (target/'QUESTION_QUALITY_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
    if summary['failed'] or errors or not report:raise SystemExit(1)

if __name__=='__main__':main()

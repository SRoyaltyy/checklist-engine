"""P3b structural + measured-answer gate. This is not a probability miner.

Questions and answer tallies are streamed CSVs. No empirical PASS is possible
without a provenance-bound 200-stock, 2020-2022 sample. Coverage is by item,
facet, derivative, candle size, lookback, threshold and both directions.
"""
import argparse,csv,gzip,hashlib,json,statistics
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


def evaluate(catalog,tree_files,tally_files,sample,exemptions=()):
    items={r['item_id']:r for r in catalog}
    exemption={(r['item_id'],r['facet']):r['reason'].strip() for r in exemptions if r.get('reason','').strip()}
    fail=defaultdict(set);facets=defaultdict(Counter);grid=defaultdict(lambda:defaultdict(set))
    count=Counter();qids=set();formulas=set();owners={};tallies={}
    global_errors=[]
    for file in tally_files:
        for row in rows(file):
            qid=row['question_id']
            if qid in tallies:global_errors.append('duplicate tally '+qid)
            outcomes=json.loads(row['answer_counts'])
            total=int(row['n_total']);nonblank=sum(int(v) for v in outcomes.values())
            if sample.get('rows') and total!=int(sample['rows']):global_errors.append('tally does not cover the declared sample '+qid)
            if nonblank>total or min([total,*[int(v) for v in outcomes.values()]])<0:
                global_errors.append('invalid answer counts '+qid)
            tallies[qid]=(100*nonblank/total if total else 0,len([v for v in outcomes.values() if int(v)>0])<=1)
    for file in tree_files:
        for row in rows(file):
            iid=row.get('item_id','');qid=row.get('question_id','')
            if iid not in items:global_errors.append('unknown item '+iid);continue
            missing=[k for k in REQUIRED if not str(row.get(k,'')).strip()]
            if missing:fail[iid].add('blank metadata: '+','.join(missing));continue
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
            if qid not in tallies:fail[iid].add('missing measured answer tally')
            else:
                pct,constant=tallies[qid]
                if pct<1:fail[iid].add('question >99% blank')
                if constant:fail[iid].add('constant question')
    if len(set(sample.get('tickers',[])))<200:global_errors.append('sample contains fewer than 200 unique stocks')
    if set(sample.get('years',[]))!={2020,2021,2022}:global_errors.append('sample years must be 2020-2022')
    if int(sample.get('rows',0))<len(set(sample.get('tickers',[]))):global_errors.append('sample row count is smaller than its stock count')
    if not sample.get('input_manifest_sha256'):global_errors.append('sample input provenance missing')
    if sample.get('question_tree_sha256')!=tree_digest(tree_files):global_errors.append('sample is not bound to this exact question tree')
    for iid,item in items.items():
        derivatives={key[2] for key in grid if key[0]==iid}
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
    ap.add_argument('--exemptions');ap.add_argument('--out',required=True);args=ap.parse_args()
    catalog=json.loads(Path(args.catalog).read_text());sample=json.loads(Path(args.sample).read_text())
    exemptions=list(rows(args.exemptions)) if args.exemptions else []
    report,facets,errors=evaluate(catalog,args.tree,args.tallies,sample,exemptions)
    target=Path(args.out);target.mkdir(parents=True,exist_ok=True)
    with open(target/'QUESTION_QUALITY.csv','w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(report[0]));writer.writeheader();writer.writerows(report)
    (target/'QUESTION_FACET_COUNTS.json').write_text(json.dumps(facets,indent=2))
    summary=dict(items=len(report),passed=sum(r['status']=='PASS' for r in report),failed=sum(r['status']=='FAIL' for r in report),global_errors=errors)
    (target/'QUESTION_QUALITY_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
    if summary['failed'] or errors or not report:raise SystemExit(1)

if __name__=='__main__':main()

"""Read immutable price archives, verify fingerprints, and audit every frozen bridge."""
import argparse,collections,hashlib,io,json,os,re,tarfile,time,urllib.request,urllib.parse
from pathlib import Path
import pandas as pd
from price_reconcile import reconcile_one
from fetch.fetch_world_prices import chart_rows,provider_symbol,period_end

def request(url,binary=False,auth=True):
    headers={'User-Agent':'checklist-engine research cyrus-checklist@users.noreply.github.com'}
    if auth:headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    if binary and auth:headers['Accept']='application/octet-stream'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=180) as response:raw=response.read()
            return raw if binary else json.loads(raw)
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-tag',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    import facets_world as fw
    frozen=fw.load_bars();indices=frozen.groupby('ticker',observed=True).indices
    requested=set(indices);results={};source_reports={};duplicates=[]
    api='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']
    release=request(api+'/releases/tags/'+a.source_tag);assets={};page=1
    while True:
        batch=request(api+f"/releases/{release['id']}/assets?per_page=100&page={page}")
        assets.update({v['name']:v for v in batch})
        if len(batch)<100:break
        page+=1
    manifests=sorted(n for n in assets if re.fullmatch(r'prices_shard_\d+_attempt_\d+_part_\d+\.json',n))
    archive_failures=[]
    for n in manifests:
        manifest=json.loads(request(assets[n]['url'],binary=True))
        source_reports.update(manifest['report']['completed'])
        raw=request(assets[n.replace('.json','.tar')]['url'],binary=True)
        if hashlib.sha256(raw).hexdigest()!=manifest['archive_sha256']:raise ValueError('archive fingerprint mismatch '+n)
        members={m['name']:m for m in manifest['members']}
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            if set(tar.getnames())!=set(members):raise ValueError('archive member mismatch '+n)
            for member in tar:
                data=tar.extractfile(member).read();meta=members[member.name]
                if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('source member fingerprint mismatch')
                if member.name.endswith('.events.parquet'):continue
                ticker=bytes.fromhex(member.name.removesuffix('.parquet')).decode()
                if ticker in results:duplicates.append(ticker);continue
                if ticker not in requested:results[ticker]=dict(status='NOT_IN_FROZEN_UNIVERSE');continue
                new=pd.read_parquet(io.BytesIO(data));old=frozen.iloc[indices[ticker]]
                try:
                    _,report=reconcile_one(ticker,old,new)
                    results[ticker]=report
                except Exception as exc:
                    results[ticker]=dict(ticker=ticker,status='FAIL',reason=str(exc),frozen_rows=len(old),supplemental_rows=len(new),frozen_first=str(old.date.min())[:10],frozen_last=str(old.date.max())[:10],source_first=str(new.date.min())[:10],source_last=str(new.date.max())[:10])
        print('BRIDGE_ARCHIVE_CHECKED',n,len(results),flush=True)
    alternatives={}
    for ticker,meta in sorted(source_reports.items()):
        if meta['last']>='2026-10-23':continue
        url='https://query2.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(provider_symbol(ticker),safe='')+'?'+urllib.parse.urlencode(dict(period1=631152000,period2=period_end('2026-10-23'),interval='1d',events='div,splits'))
        try:
            payload=request(url,auth=False);frame,events=chart_rows(ticker,payload)
            frame=frame[frame.date<=pd.Timestamp('2026-10-23')]
            target=out/(ticker.encode().hex()+'.query2.parquet');frame.to_parquet(target,index=False)
            alternatives[ticker]=dict(status='FETCHED',url=url,rows=len(frame),first=str(frame.date.min())[:10],last=str(frame.date.max())[:10],sha256=hashlib.sha256(target.read_bytes()).hexdigest(),used_as_replacement=False)
        except Exception as exc:alternatives[ticker]=dict(status='ERROR',url=url,error=str(exc),used_as_replacement=False)
        time.sleep(1)
    counts=collections.Counter(r['status'] for r in results.values())
    summary=dict(source_tag=a.source_tag,source_commit=os.environ['GITHUB_SHA'],requested=len(requested),audited=len(results),counts=dict(counts),missing=sorted(requested-set(results)),duplicate_source_names=duplicates,all_archives_verified=True,alternative_stale_sources=alternatives,nominal_historical_price_verified=False,world_coverage_approved=False,results=results)
    (out/'FULL_PRICE_RECONCILIATION_AUDIT.json').write_text(json.dumps(summary,indent=2))
    rows=[dict(ticker=t,**{k:v for k,v in r.items() if k!='ticker'}) for t,r in sorted(results.items())]
    pd.DataFrame(rows).to_csv(out/'FULL_PRICE_RECONCILIATION_AUDIT.csv',index=False)
    print(json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)
    failed=[dict(ticker=t,**{k:v for k,v in r.items() if k!='ticker'}) for t,r in results.items() if r['status']!='PASS']
    print('BRIDGE_FAILURES',json.dumps(failed),flush=True)

if __name__=='__main__':main()

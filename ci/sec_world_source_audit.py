"""Summarize all durable SEC source receipts; keep identity and source gaps explicit."""
import argparse,collections,hashlib,json,os,re,urllib.request
from pathlib import Path

def get(url,binary=False):
    headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'checklist-engine-source-audit'}
    if binary:headers['Accept']='application/octet-stream'
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as response:raw=response.read()
    return raw if binary else json.loads(raw)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);api='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']
    release=get(api+'/releases/tags/'+a.tag);assets=[];page=1
    while True:
        batch=get(api+f"/releases/{release['id']}/assets?per_page=100&page={page}");assets.extend(batch)
        if len(batch)<100:break
        page+=1
    identity_asset=next(x for x in assets if x['name']=='SEC_WORLD_IDENTITIES.json')
    identity_raw=get(identity_asset['url'],True);identities=json.loads(identity_raw)
    latest={};receipts=[]
    for asset in assets:
        m=re.fullmatch(r'sec_world_shard_(\d+)_attempt_(\d+)_part_(\d+)\.json',asset['name'])
        if m:
            shard,attempt,part=map(int,m.groups())
            if shard not in latest or (attempt,part)>latest[shard][0]:latest[shard]=((attempt,part),asset)
    completed={};errors={};requested=[]
    for _,asset in latest.values():
        raw=get(asset['url'],True);receipt=json.loads(raw);report=receipt['report']
        completed.update(report['completed']);errors.update(report['errors']);requested.extend(report['requested'])
        receipts.append(dict(name=asset['name'],sha256=hashlib.sha256(raw).hexdigest(),source_commit=receipt['source_commit']))
    mapped={str(cik) for cik in identities['ciks']}
    report=dict(status='SOURCE_RECEIPT_AUDIT_WITH_GAPS' if errors or mapped-set(completed) else 'SOURCE_RECEIPT_AUDIT_PASS',
        tag=a.tag,asset_count=len(assets),identity_sha256=hashlib.sha256(identity_raw).hexdigest(),
        identity_statuses=identities['statuses'],current_map_status=identities.get('current_map_status'),
        requested_ciks=len(mapped),receipted_ciks=len(set(map(str,requested))),completed_ciks=len(completed),
        missing_ciks=sorted(mapped-set(completed)-set(errors)),errors=errors,shards=len(latest),
        numeric_fact_rows=sum(r.get('fact_rows',0) for r in completed.values()),
        fact_statuses=dict(collections.Counter(r['facts_status'] for r in completed.values())),
        submission_statuses=dict(collections.Counter(r['submissions_status'] for r in completed.values())),
        submission_files=sum(r.get('submission_files',0) for r in completed.values()),
        first_filed=min((r['first_filed'] for r in completed.values() if r.get('first_filed')),default=None),
        last_filed=max((r['last_filed'] for r in completed.values() if r.get('last_filed')),default=None),
        receipts=receipts,completed=completed,scope='Receipt counts only. Not a snapshot/identity/coverage approval; raw archive hashes are independently checked when consumed.')
    (out/'SEC_WORLD_SOURCE_AUDIT.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('completed','receipts')}),flush=True)
if __name__=='__main__':main()

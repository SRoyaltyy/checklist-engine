"""Reparse every selected SEC archive; verify hashes, CIKs, facts and explicit quarantine."""
import argparse,gzip,hashlib,io,json,os,re,tarfile,time,urllib.request
from pathlib import Path
import pandas as pd
from fetch.fetch_sec_world import numeric_facts
def get(url,binary=False):
    headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'User-Agent':'checklist-engine-source-integrity'}
    if binary:headers['Accept']='application/octet-stream'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=180) as response:raw=response.read()
            return raw if binary else json.loads(raw)
        except Exception:
            if attempt==3:raise
            time.sleep(2**attempt)
def catalog(api,tag):
    release=get(api+'/releases/tags/'+tag);assets={};page=1
    while True:
        batch=get(api+f"/releases/{release['id']}/assets?per_page=100&page={page}")
        assets.update({v['name']:v for v in batch})
        if len(batch)<100:break
        page+=1
    return assets
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base-tag',required=True);ap.add_argument('--repair-tag',required=True);ap.add_argument('--shard',type=int,required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);api='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']
    base=catalog(api,a.base_tag);identity_raw=get(base['SEC_WORLD_IDENTITIES.json']['url'],True);identities=json.loads(identity_raw)
    if hashlib.sha256(identity_raw).hexdigest()!='0f62ee169a82dcb7fcdd339fd2606c2de6ef41b886c8ea3d253e620578967f25':raise ValueError('Original CIK assignment changed')
    selected_tag=a.repair_tag if a.shard==9 else a.base_tag
    assets=catalog(api,a.repair_tag) if a.shard==9 else base
    names=sorted(n for n in assets if re.fullmatch(rf'sec_world_shard_{a.shard:03d}_attempt_\d+_part_\d+\.json',n))
    if not names:raise ValueError('No selected source archives')
    requested=set(map(int,identities['ciks'][a.shard::16]));verified={};archives=[];last_report={}
    for name in names:
        receipt_raw=get(assets[name]['url'],True);receipt=json.loads(receipt_raw);last_report=receipt['report']
        raw=get(assets[name.replace('.json','.tar')]['url'],True)
        if hashlib.sha256(raw).hexdigest()!=receipt['archive_sha256']:raise ValueError('Archive hash mismatch '+name)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            expected={r['name']:r for r in receipt['members']}
            if set(tar.getnames())!=set(expected) or len(tar.getmembers())!=len(expected):raise ValueError('Archive member mismatch')
            payloads={}
            for member in tar:
                data=tar.extractfile(member).read();meta=expected[member.name]
                if len(data)!=meta['bytes'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('Member hash mismatch '+member.name)
                payloads[member.name]=data
            for filename,data in payloads.items():
                match=re.fullmatch(r'CIK(\d{10})\.facts\.parquet',filename)
                if not match:continue
                cik=int(match.group(1));prefix=f'CIK{cik:010d}'
                if cik not in requested or cik in verified:raise ValueError('Wrong or repeated CIK')
                facts=json.loads(gzip.decompress(payloads[prefix+'.companyfacts.json.gz']))
                official=json.loads(gzip.decompress(payloads[prefix+'.submissions.json.gz']))
                if int(official.get('cik',-1))!=cik:raise ValueError('Official submission identity mismatch')
                quarantine=facts.get('cik') is None;source_record=last_report['completed'][str(cik)]
                if quarantine and (not source_record.get('identity_quarantined') or source_record.get('identity_binding')!='official_submissions_cik_and_exact_entity_name'):raise ValueError('Missing root CIK not quarantined')
                rebuilt=numeric_facts(cik,facts,official_identity=official if quarantine else None)
                stored=pd.read_parquet(io.BytesIO(data))
                pd.testing.assert_frame_equal(stored,rebuilt,check_dtype=False,check_exact=True)
                if len(stored)!=source_record['fact_rows']:raise ValueError('Receipt rows disagree with reparsed facts')
                verified[cik]=dict(cik=cik,fact_rows=len(stored),quarantined=quarantine,root_cik=facts.get('cik'),official_cik=int(official['cik']),entity_name=facts.get('entityName'),source_tag=selected_tag,raw_sha256=hashlib.sha256(payloads[prefix+'.companyfacts.json.gz']).hexdigest(),parquet_sha256=hashlib.sha256(data).hexdigest())
        archives.append(dict(receipt=name,receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(),archive_sha256=receipt['archive_sha256']))
        print('SEC_FULL_ARCHIVE_VERIFIED',name,len(verified),flush=True)
    missing=sorted(requested-set(verified))
    if missing or last_report.get('errors'):raise ValueError('Incomplete selected source '+json.dumps(dict(missing=missing,errors=last_report.get('errors'))))
    report=dict(status='INTEGRITY_PASS_WITH_QUARANTINE' if any(r['quarantined'] for r in verified.values()) else 'INTEGRITY_PASS',shard=a.shard,requested_ciks=len(requested),verified_ciks=len(verified),numeric_fact_rows=sum(r['fact_rows'] for r in verified.values()),quarantined=[r for r in verified.values() if r['quarantined']],archives=archives,verified=verified,base_tag=a.base_tag,selected_tag=selected_tag,scope='Full raw source reparse only. Quarantine and unmapped universe names remain; no complete world-state approval.')
    (out/f'SEC_FULL_SOURCE_PROOF_{a.shard:03d}.json').write_text(json.dumps(report,indent=2))
    print('SEC_FULL_SOURCE_PROOF',json.dumps({k:v for k,v in report.items() if k not in ('archives','verified')}),flush=True)
if __name__=='__main__':main()

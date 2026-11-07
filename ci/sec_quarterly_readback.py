"""Independent complete quarterly raw/parquet readback on GitHub Actions only."""
import argparse
from datetime import date,datetime,timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path,PurePosixPath
import re
from urllib.parse import urljoin,urlsplit

from ci import release_assets as releases
from ci.sec_quarterly_readback_core import FIELDS,RowHash,columns,raw_window,require

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/'ci/SEC_QUARTERLY_READBACK_REQUEST.json'
FINAL='SEC_QUARTERLY_FIXED_FIELDS_V2.json'
PAGES={'form345':'https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets',
       'form13f':'https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets'}


def digest(path):return releases._digest(path).removeprefix('sha256:')
def api(path):return json.loads(releases._read('api','repos/SRoyaltyy/checklist-engine/'+path))


def validate_request(value):
    require(set(value)=={'version','execute','sources'} and value['version']==1 and type(value['execute']) is bool,'quarterly readback request differs')
    require(isinstance(value['sources'],dict) and set(value['sources'])<=set(PAGES),'readback source kinds differ')
    if value['execute']:require(set(value['sources'])==set(PAGES),'enabled quarterly audit requires both complete source kinds')
    for spec in value['sources'].values():
        require(set(spec)=={'run','attempt','commit','receipt_sha256'},'readback source anchors differ')
        require(all(re.fullmatch('[1-9][0-9]*',str(spec[k])) for k in ('run','attempt')),'invalid quarterly run/attempt')
        require(bool(re.fullmatch('[0-9a-f]{40}',spec['commit'])) and bool(re.fullmatch('[0-9a-f]{64}',spec['receipt_sha256'])),'invalid quarterly commit/fingerprint')
    return value


class Remote:
    def __init__(self,tag,commit,root):
        self.tag=tag;self.root=root;self.seen=set();self.release=releases.release_info(tag)
        require(not self.release['draft'] and self.release['target_commitish']==commit,'related public release commit differs')
        assets=[];page=1
        while True:
            batch=api(f"releases/{self.release['id']}/assets?per_page=100&page={page}");assets.extend(batch)
            if len(batch)<100:break
            page+=1
        self.inventory={a['name']:a for a in assets}
        require(len(self.inventory)==len(assets),'duplicate remote asset names')
        releases._DOWNLOAD_INVENTORIES[('SRoyaltyy/checklist-engine',tag)]=self.inventory

    def get(self,name):
        path=releases.download_asset(self.tag,name,self.root);self.seen.add(name)
        print('QUARTERLY_READBACK_ASSET',self.tag,name,path.stat().st_size,flush=True)
        return path

    def json(self,name,sha=None):
        path=self.get(name)
        if sha is not None:require(digest(path)==sha,'frozen related receipt differs')
        value=json.loads(path.read_bytes());path.unlink();return value

    def manifest(self,bindings,final):
        result={b['name']:b for b in bindings}
        require(len(result)==len(bindings) and set(self.inventory)==set(result)|{final},'unbound/missing/duplicate quarterly assets')
        for name,b in result.items():
            a=self.inventory[name]
            require(a['state']=='uploaded' and a['size']==b['bytes'] and a['digest']=='sha256:'+b['sha256'],'quarterly asset fingerprint differs: '+name)
        return result


def actual_success(spec,paths):
    run=api(f"actions/runs/{spec['run']}/attempts/{spec['attempt']}")
    require(run['status']=='completed' and run['conclusion']=='success' and run['head_sha']==spec['commit']
        and run['path'] in paths,'quarterly source actual run is not successful or differs')


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.links.extend(v for k,v in attrs if k=='href' and v)


def catalog(html,kind,end_year):
    parser=Links();parser.feed(html);records={};names={}
    for link in parser.links:
        url=urljoin(PAGES[kind],link);u=urlsplit(url);name=PurePosixPath(u.path).name
        if u.scheme!='https' or u.hostname not in ('sec.gov','www.sec.gov') or not name.lower().endswith('_'+kind+'.zip'):continue
        require(not(u.username or u.password or u.query or u.fragment) and u.port in (None,443),'unexpected source index URL')
        quarter=re.fullmatch(r'(20\d{2})q([1-4])_'+kind+r'\.zip',name,re.I)
        if quarter:
            year,q=map(int,quarter.groups());start=date(year,q*3-2,1);years=[year]
            row=dict(label=f'{year}Q{q}',nominal_year=year,nominal_quarter=q,filename_start_date=None,filename_end_date=None)
        else:
            match=re.fullmatch(r'(\d{2}[A-Za-z]{3}20\d{2})-(\d{2}[A-Za-z]{3}20\d{2})_'+kind+r'\.zip',name,re.I)
            require(bool(match),'unrecognized official quarterly source name')
            start,end=(datetime.strptime(v,'%d%b%Y').date() for v in match.groups());years=[start.year,end.year]
            require(start<=end and (end-start).days<=366,'invalid source filename range')
            row=dict(label=start.isoformat()+'_'+end.isoformat(),nominal_year=None,nominal_quarter=None,
                filename_start_date=start.isoformat(),filename_end_date=end.isoformat())
        if max(years)<2020 or min(years)>end_year:continue
        require(name.lower() not in names or names[name.lower()]==url,'ambiguous official source ZIP basename')
        names[name.lower()]=url;records[url]=(start,dict(url=url,name=name,**row))
    require(bool(records),'empty official quarterly source index')
    return [r for _,r in sorted(records.values(),key=lambda x:(x[0],x[1]['name']))]


def selected_ciks(report,root):
    import pyarrow.parquet as pq
    proof=report['bulk_prerequisite'];remote=Remote(proof['release'],proof['commit'],root/'bulk-audit')
    audit=remote.json('SEC_BULK_PUBLIC_READBACK_V1.json',proof['receipt_sha256'])
    require(audit['status']=='PASS' and audit['format']=='SEC_BULK_PUBLIC_READBACK_V1'
        and audit['reader_commit']==proof['commit'] and audit['coverage']['retained_names']==8439
        and audit['verification_scope']=='ALL_PUBLISHED_RETAINED_RAW_MEMBERS_AND_ALL_PARQUET_ROW_VALUES'
        and 'companyfacts' in audit['unfiltered_zip_readback_kinds'],'bulk prerequisite scope differs')
    actual_success(dict(run=audit['actual_run_id'],attempt=audit['actual_attempt'],commit=proof['commit']),{'.github/workflows/sec_bulk_readback.yml'})
    source=audit['source'];require(proof['producer']==source,'bulk prerequisite producer differs')
    tag=f"nai-sec-bulk-v2-{source['run']}-{source['attempt']}";bulk=Remote(tag,source['commit'],root/'bulk-input')
    source_report=bulk.json('SEC_BULK_COVERAGE_V2.json',source['receipt_sha256'])
    require(source_report['status']=='PASS_BOTH_BULK_SOURCES_RETAINED_EXTRACTION'
        and source_report['source_commit']==source['commit'] and source_report['retained_names']==8439,'bulk source snapshot incomplete')
    identities=[];bindings=[]
    for binding in source_report['assets']:
        if binding['name'].startswith('sec_identity_map_v2-') and binding['name'].endswith('.parquet'):
            path=bulk.get(binding['name']);require(digest(path)==binding['sha256'] and path.stat().st_size==binding['bytes'],'identity baseline bytes differ')
            identities.extend(pq.read_table(path).to_pylist());path.unlink();bindings.append(binding)
    require(len(identities)==8439 and len({r['ticker'] for r in identities})==8439,'identity cohort membership differs')
    require(all(not r['historical_join_allowed'] and r['valid_from'] is None and r['valid_to_exclusive'] is None for r in identities),'historical ownership was inferred')
    selected={c for row in identities for c in row['candidate_ciks']}
    require(bool(selected) and 1790169 not in selected,'retrieval integrity quarantine differs')
    expected=dict(release=tag,producer=source,assets=bindings,retained_names=8439,retrieval_ciks=len(selected),
                  identity_scope='RETRIEVAL_CANDIDATES_NOT_HISTORICAL_OWNERSHIP')
    require(report['identity_source']==expected,'quarterly retrieval baseline differs')
    return selected


def arrow_schema(kind,table):
    import pyarrow as pa
    names=columns(kind,table);types={k:pa.string() for k in names};types['source_row']=pa.int64()
    types['issuer_cik' if kind=='form345' else 'filing_manager_cik']=pa.int64()
    if kind=='form345':types['retained_retrieval_candidate']=pa.bool_()
    return pa.schema([(k,types[k]) for k in names])


def parquet_group(remote,bindings,kind,window,table):
    import pyarrow.parquet as pq
    names=sorted(n for n,b in bindings.items() if b['kind']=='fixed_source_parquet'
        and b['source_window']==window['label'] and b['table']==table)
    signature=RowHash();key='issuer_cik' if kind=='form345' else 'filing_manager_cik'
    safe=re.sub('[^A-Za-z0-9_-]','_',window['label'])
    for part,name in enumerate(names):
        require(name==f'sec_{kind}_{safe}_{table.lower()}-{part:05d}.parquet','quarterly parquet sequence/name differs')
        b=bindings[name];require(b['source_zip']==window['name'] and b['source_cik_field']==key,'parquet source/CIK role differs')
        path=remote.get(name);ciks=set();count=0;unknown_parent=0
        with pq.ParquetFile(path) as file:
            require(file.schema_arrow.equals(arrow_schema(kind,table)),'quarterly parquet schema differs')
            require(hashlib.sha256(str(file.schema_arrow).encode()).hexdigest()==b['schema_sha256'],'quarterly schema hash differs')
            for batch in file.iter_batches(batch_size=50000):
                for row in batch.to_pylist():
                    signature.add([row[k] for k in columns(kind,table)]);count+=1
                    if row[key] is not None:ciks.add(row[key])
                    unknown_parent+=row['parent_link_status']=='SOURCE_SUBMISSION_MISSING'
            require(count==file.metadata.num_rows==b['rows'] and sorted(ciks)==b['source_ciks']
                and unknown_parent==b['parent_link_failures'],'actual parquet rows/CIK set/parent failures differ')
        path.unlink()
    return signature.result()


def audit_kind(kind,spec,root):
    actual_success(spec,{'.github/workflows/nai_sec_quarterly_v2.yml',f'.github/workflows/nai_sec_{kind}.yml'})
    tag=f"nai-sec-quarterly-v2-{kind}-{spec['run']}-{spec['attempt']}";remote=Remote(tag,spec['commit'],root/'data')
    report=remote.json(FINAL,spec['receipt_sha256'])
    require(report['status']=='PASS_ALL_PUBLISHED_QUARTERLY_FIXED_FIELDS_SOURCE_ONLY' and report['kind']==kind
        and report['actual_run_id']==str(spec['run']) and report['actual_attempt']==str(spec['attempt'])
        and report['source_commit']==spec['commit'] and report['release']==tag,'quarterly producer source/status differs')
    require(report['scoring_gate']=='CLOSED' and report['world_gate']=='NOT_PROVEN' and not report['free_text_features']
        and report['scope']=='ALL_FIXED_SOURCE_ROWS_NOT_A_HISTORICAL_TICKER_OR_STOCK_DATE_JOIN','quarterly producer scope differs')
    bindings=remote.manifest(report['assets'],FINAL);selected=selected_ciks(report,root)
    source_spec=report['profile_source'];profile_remote=None;profiles={};profile_bindings={}
    if source_spec:
        actual_success(source_spec,{'.github/workflows/sec_quarterly_profile.yml'})
        source_tag=f"sec-quarterly-profile-v2-{kind}-{source_spec['run']}-{source_spec['attempt']}"
        profile_remote=Remote(source_tag,source_spec['commit'],root/'profile')
        source_profile=profile_remote.json('SEC_QUARTERLY_SOURCE_PROFILE_V2.json',source_spec['receipt_sha256'])
        require(source_profile['status']=='PASS_PUBLISHED_SOURCE_CATALOG_ONLY' and source_profile['kind']==kind
            and source_profile['source_commit']==source_spec['commit'] and source_profile['release']==source_tag
            and source_profile['actual_run_id']==str(source_spec['run'])
            and source_profile['actual_attempt']==str(source_spec['attempt']),'source profile scope differs')
        profile_bindings=profile_remote.manifest(source_profile['assets'],'SEC_QUARTERLY_SOURCE_PROFILE_V2.json')
        require([w['window'] for w in source_profile['windows']]==source_profile['published_catalog'],'source profile catalog incomplete')
        profiles={w['window']['name']:w for w in source_profile['windows']}
        require(report['index']==source_profile['index'] and report['index_lineage']==dict(release=source_tag,
            receipt_sha256=source_spec['receipt_sha256'],source_commit=source_spec['commit']),'source index lineage differs')
    index_remote=profile_remote or remote;index=index_remote.get(kind+'_official_index.html')
    require(index.stat().st_size==report['index']['bytes'] and digest(index)==report['index']['sha256']
        and report['index']['url']==PAGES[kind],'original official index bytes differ')
    expected=catalog(index.read_text(encoding='utf-8'),kind,datetime.fromisoformat(report['index']['finished_at']).year);index.unlink()
    require(expected==report['published_catalog']==[w['window'] for w in report['windows']],'published source window omission/catalog differs')
    results=[];totals={}
    for entry in report['windows']:
        window=entry['window'];name=window['name'];source=entry['source']
        require(remote.json(name+'.source.json')==dict(window=window,source=source,source_commit=spec['commit']),'quarterly input receipt differs')
        require(remote.json(name+'.fixed.json')==entry,'quarterly fixed receipt differs')
        if profile_remote:
            original=profiles[name];require(profile_remote.json(name+'.json')==original,'original source schema receipt differs')
            require(profile_remote.json(name+'.source.json')==dict(window=window,source=original['source'],
                source_commit=source_spec['commit']),'original source acquisition receipt differs')
            lineage=dict(release=profile_remote.tag,asset=name,profile_receipt='SEC_QUARTERLY_SOURCE_PROFILE_V2.json',
                profile_receipt_sha256=source_spec['receipt_sha256'],schema_receipt=name+'.json',
                schema_receipt_sha256=profile_bindings[name+'.json']['sha256'],source_commit=source_spec['commit'])
            require(source==dict(original['source'],reused_from=lineage) and entry['profile']==original['profile'],
                    'cached quarterly acquisition times/profile lineage differs')
        raw=(profile_remote or remote).get(name)
        require(raw.stat().st_size==source['bytes'] and digest(raw)==source['sha256'] and source['url']==window['url'],'full original quarterly ZIP differs')
        actual,raw_hashes=raw_window(raw,kind,window['label'],selected);raw.unlink()
        require(actual==entry['extraction'],'independent raw-derived table metadata differs: '+window['label'])
        measured={t['table']:t for t in entry['profile']['tables']};verified={}
        for table,signature in raw_hashes.items():
            meta=actual['tables'][table]
            require(meta['rows']==measured[table]['rows'] and meta['source_columns']==measured[table]['columns'],'profile/raw table count/header differs')
            require(parquet_group(remote,bindings,kind,window,table)==signature,'full source/parquet values differ: '+window['label']+'/'+table)
            verified[table]=signature;totals[table]=totals.get(table,0)+signature['rows']
        results.append(dict(window=window['label'],tables=verified))
        print('QUARTERLY_READBACK_WINDOW',kind,window['label'],'PASS',flush=True)
    require(remote.seen==set(remote.inventory),'quarterly producer assets were not all read')
    if profile_remote:require(profile_remote.seen==set(profile_remote.inventory),'quarterly profile assets were not all read')
    return dict(source=spec,status='PASS',windows_verified=len(results),full_original_zips_verified=len(results),
        data_assets_checked=len(remote.seen),profile_assets_checked=len(profile_remote.seen) if profile_remote else 0,
        rows_by_table=totals,window_row_digests=results,scoring_gate='CLOSED',historical_issuer_join='NOT_PROVEN')


def run(root):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_REPOSITORY')=='SRoyaltyy/checklist-engine',
            'quarterly readback runs only on the authorized GitHub runner')
    request=validate_request(json.loads(REQUEST.read_bytes()));require(request['execute'],'quarterly readback disabled')
    root.mkdir(parents=True,exist_ok=True)
    report=dict(format='SEC_QUARTERLY_PUBLIC_READBACK_V1',status='FAIL',actual_run_id=os.environ['GITHUB_RUN_ID'],
        actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],reader_commit=os.environ['GITHUB_SHA'],sources=request['sources'],
        started_at=datetime.now(timezone.utc).isoformat(),datasets={},scoring_gate='CLOSED',world_gate='NOT_PROVEN',
        verification_scope='ALL_PUBLISHED_FIXED_FIELDS_AND_PARENT_DATE_UNIT_CIK_ANNOTATIONS')
    try:
        for kind,spec in request['sources'].items():report['datasets'][kind]=audit_kind(kind,spec,root/kind)
        report['status']='PASS'
    except Exception as exc:
        report['error']=dict(type=type(exc).__name__,message=str(exc));raise
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat();path=root/'SEC_QUARTERLY_PUBLIC_READBACK_V1.json'
        path.write_text(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n',encoding='utf-8')
        tag=f"sec-quarterly-readback-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
        releases.gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],
            '--title',tag,'--notes',report['status']+' independent quarterly fixed-field readback. Scoring CLOSED.')
        releases.publish_assets(tag,path);releases.gh_retry('release','edit',tag,'--draft=false')
        print('SEC_QUARTERLY_READBACK_FINAL',report['status'],tag,flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,default=Path('sec-quarterly-readback-output'))
    run(parser.parse_args().directory)

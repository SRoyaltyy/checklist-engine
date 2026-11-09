"""Authenticate quarterly caches and the retained retrieval set; no issuer inference."""
import json

from ci import release_assets as releases
from ci.sec_bulk_retained import digest


def api(path):return json.loads(releases._read('api','repos/SRoyaltyy/checklist-engine/'+path))


def verified_release(tag,commit):
    release=releases.release_info(tag)
    if release['draft'] or release['target_commitish']!=commit:raise ValueError('quarterly source release anchor differs')
    return release


def retained_ciks(prerequisite,root):
    import pyarrow.parquet as pq
    source=prerequisite['producer'];tag=f"nai-sec-bulk-v2-{source['run']}-{source['attempt']}"
    verified_release(tag,source['commit'])
    path=releases.download_asset(tag,'SEC_BULK_COVERAGE_V2.json',root/'retained-input')
    if digest(path)!=source['receipt_sha256']:raise ValueError('retained source receipt differs')
    report=json.loads(path.read_bytes());path.unlink()
    if (report['status']!='PASS_BOTH_BULK_SOURCES_RETAINED_EXTRACTION'
            or report['source_commit']!=source['commit'] or report['retained_names']!=8439):
        raise ValueError('retained source snapshot is not the verified complete producer')
    identities=[];bindings=[]
    for binding in report['assets']:
        if binding['name'].startswith('sec_identity_map_v2-') and binding['name'].endswith('.parquet'):
            path=releases.download_asset(tag,binding['name'],root/'retained-input')
            if path.stat().st_size!=binding['bytes'] or digest(path)!=binding['sha256']:
                raise ValueError('retained identity bytes differ')
            identities.extend(pq.read_table(path).to_pylist());path.unlink();bindings.append(binding)
    if len(identities)!=8439 or len({r['ticker'] for r in identities})!=8439:
        raise ValueError('retained source membership count differs')
    if any(r['historical_join_allowed'] or r['valid_from'] is not None or r['valid_to_exclusive'] is not None for r in identities):
        raise ValueError('source retrieval candidates cannot imply historical ownership')
    selected={c for row in identities for c in row['candidate_ciks']}
    if not selected or 1790169 in selected:raise ValueError('retained source CIK quarantine differs')
    return selected,dict(release=tag,producer=source,assets=bindings,retained_names=8439,
        retrieval_ciks=len(selected),identity_scope='RETRIEVAL_CANDIDATES_NOT_HISTORICAL_OWNERSHIP')


class ProfileCache:
    def __init__(self,kind,spec,root):
        self.kind=kind;self.spec=spec;self.root=root
        self.tag=f"sec-quarterly-profile-v2-{kind}-{spec['run']}-{spec['attempt']}"
        verified_release(self.tag,spec['commit'])
        run=api(f"actions/runs/{spec['run']}/attempts/{spec['attempt']}")
        if (run['status']!='completed' or run['conclusion']!='success' or run['head_sha']!=spec['commit']
                or run['path']!='.github/workflows/sec_quarterly_profile.yml'):
            raise ValueError('quarterly profile actual run is not the successful bound source')
        path=releases.download_asset(self.tag,'SEC_QUARTERLY_SOURCE_PROFILE_V2.json',root/'profile-input')
        if digest(path)!=spec['receipt_sha256']:raise ValueError('quarterly profile receipt fingerprint differs')
        report=json.loads(path.read_bytes());path.unlink()
        if (report['status']!='PASS_PUBLISHED_SOURCE_CATALOG_ONLY' or report['kind']!=kind
                or report['source_commit']!=spec['commit'] or report['release']!=self.tag
                or report['actual_run_id']!=str(spec['run']) or report['actual_attempt']!=str(spec['attempt'])):
            raise ValueError('quarterly profile is not a complete matching source catalog')
        windows=report['windows'];catalog=report['published_catalog']
        if not windows or [w['window'] for w in windows]!=catalog:
            raise ValueError('quarterly profile omitted published source windows')
        self.report=report;self.windows=windows
        self.bindings={b['name']:b for b in report['assets']}
        if len(self.bindings)!=len(report['assets']):raise ValueError('duplicate profile source asset binding')

    def checked(self,name):
        binding=self.bindings[name]
        path=releases.download_asset(self.tag,name,self.root/'profile-input')
        if path.stat().st_size!=binding['bytes'] or digest(path)!=binding['sha256']:
            raise ValueError('cached quarterly source bytes differ: '+name)
        return path

    def get(self,window_receipt):
        window=window_receipt['window'];name=window['name']
        metadata=self.checked(name+'.json');receipt=json.loads(metadata.read_bytes());metadata.unlink()
        if receipt!=window_receipt:raise ValueError('cached quarterly schema receipt differs from root')
        path=self.checked(name);source=receipt['source']
        if source['url']!=window['url'] or source['sha256']!=digest(path) or source['bytes']!=path.stat().st_size:
            raise ValueError('cached quarterly acquisition differs from raw source')
        return path,dict(source,reused_from=dict(release=self.tag,asset=name,
            profile_receipt='SEC_QUARTERLY_SOURCE_PROFILE_V2.json',profile_receipt_sha256=self.spec['receipt_sha256'],
            schema_receipt=name+'.json',schema_receipt_sha256=self.bindings[name+'.json']['sha256'],
            source_commit=self.spec['commit'])),receipt['profile']

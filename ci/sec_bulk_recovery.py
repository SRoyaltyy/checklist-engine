"""Reuse authenticated complete SEC stages/source ZIPs without new vendor requests."""
import json

from ci import release_assets as releases


def checked_receipt(spec,name,root):
    release=releases.release_info(spec['release'])
    if release['draft'] or release['target_commitish']!=spec['commit']:
        raise ValueError('recovery release is not public or its commit differs')
    path=releases.download_asset(spec['release'],name,root/'recovery-receipts')
    if releases._digest(path)!='sha256:'+spec['receipt_sha256']:
        raise ValueError('recovery receipt fingerprint differs')
    value=json.loads(path.read_bytes())
    if value['source_commit']!=spec['commit'] or value['release']!=spec['release']:
        raise ValueError('recovery receipt source binding differs')
    return value


def submissions(spec,root,selected,publisher):
    """A failed whole run may contain a complete, independently auditable stage."""
    old=checked_receipt(spec,'SEC_BULK_COVERAGE_V2.json',root)
    stage=old['stages'].get('submissions',{})
    if (old.get('retained_names')!=8439
            or old.get('identity_map_lf_sha256')!='50323efcd9855061501d88010d8e812371fda7c9dd48d3a54c0f5f19cdad97ce'
            or old.get('join_keys_lf_sha256')!='5e6d83f56bdb2a765ad5a9bf76219f82fdbe76ff2b93acd3f9ca12fa2e3233e2'
            or old.get('scoring_gate')!='CLOSED'
            or old.get('filing_record_model')!='SOURCE_OBSERVATIONS_NOT_CANONICAL_ACCESSIONS'
            or stage.get('status')!='PASS_RETAINED_SOURCE_EXTRACTION'
            or stage.get('filing_record_model')!='SOURCE_OBSERVATIONS_WITH_CONFLICT_FIELDS'
            or set(stage['populated_ciks'])|set(stage['missing_archive_ciks'])|set(stage['ciks_without_output_rows'])!=set(selected)
            or old['coverage']['retrieval_ciks']!=len(selected)):
        raise ValueError('submissions recovery is not a complete matching retrieval stage')
    bindings=[b for b in old['assets'] if b['name'].startswith('sec_submissions_')]
    def total(prefix,field):return sum(b.get(field,0) for b in bindings if b['name'].startswith(prefix))
    if (not bindings
            or total('sec_submissions_filings_retained-','rows')!=stage['rows']
            or total('sec_submissions_entities_retained-','rows')!=stage['entity_rows']
            or total('sec_submissions_raw-','members')!=stage['source_members']
            or not any(b['name'].startswith('sec_submissions_raw-') and b['name'].endswith('.json') for b in bindings)):
        raise ValueError('recovery lacks retained submissions evidence')
    for binding in bindings:
        path=releases.download_asset(spec['release'],binding['name'],root/'recovery-submissions')
        if path.stat().st_size!=binding['bytes'] or releases._digest(path)!='sha256:'+binding['sha256']:
            raise ValueError('recovered submissions asset differs')
        metadata={k:v for k,v in binding.items() if k not in ('name','bytes','sha256','kind')}
        result=publisher.emit(path,binding['kind'],**metadata)
        if result!=binding:raise ValueError('recovered submissions publication binding differs')
    if old['inputs']['submissions']['url']!='https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip':
        raise ValueError('recovered submissions source URL differs')
    source=dict(old['inputs']['submissions'],reused_from=dict(release=spec['release'],
        receipt='SEC_BULK_COVERAGE_V2.json',receipt_sha256=spec['receipt_sha256'],source_commit=spec['commit'],
        scope='COMPLETE_SUBMISSIONS_STAGE_FROM_EXPLICIT_PARTIAL_RUN'))
    return source,stage


def companyfacts(spec,root):
    old=checked_receipt(spec,'SEC_COMPANYFACTS_SOURCE_DIAGNOSTIC_V1.json',root)
    if old['status']!='PASS_EXACT_SOURCE_DIAGNOSTIC_NOT_DATA_EXTRACTION':
        raise ValueError('source ZIP diagnostic did not finish')
    bindings=[b for b in old['assets'] if b['kind']=='official_unfiltered_source_zip']
    if len(bindings)!=1 or bindings[0]['name']!='companyfacts.zip':raise ValueError('missing exact cached source ZIP')
    binding=bindings[0];source=old['source']
    if (source['url']!='https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip'
            or source['sha256']!=binding['sha256'] or source['bytes']!=binding['bytes']):
        raise ValueError('cached source acquisition differs')
    path=releases.download_asset(spec['release'],'companyfacts.zip',root/'recovery-companyfacts')
    if path.stat().st_size!=source['bytes'] or releases._digest(path)!='sha256:'+source['sha256']:
        raise ValueError('cached official ZIP bytes differ')
    return path,dict(source,reused_from=dict(release=spec['release'],asset='companyfacts.zip',
        receipt='SEC_COMPANYFACTS_SOURCE_DIAGNOSTIC_V1.json',receipt_sha256=spec['receipt_sha256'],
        source_commit=spec['commit'],scope='EXACT_OFFICIAL_UNFILTERED_SOURCE_ZIP'))

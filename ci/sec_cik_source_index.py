"""Bind every already audited SEC CIK to immutable source members, without tickers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from sec_ticker_history import canonical_cik

PROOF_TAG='sec-world-proof-v5-40283469118-1'


def digest(raw):return hashlib.sha256(raw).hexdigest()


def checked_json(raw,expected,label):
    if digest(raw)!=expected:raise ValueError(label+' SHA differs')
    return json.loads(raw)


def build_index(summary,load):
    """load(tag, name) supplies bytes; every downloaded document is hash-bound."""
    if summary['status']!='INTEGRITY_PASS_WITH_QUARANTINE':raise ValueError('source proof status differs')
    proofs=summary['proof_files']
    if len(proofs)!=16 or len({p['name'] for p in proofs})!=16:raise ValueError('complete sixteen-shard proof required')
    expected_quarantine={r['cik'] for r in summary['quarantined']}
    if expected_quarantine!={1790169}:raise ValueError('explicit identity quarantine differs')
    all_rows={};archives=[];seen_shards=set();quarantined=[]
    for spec in proofs:
        proof=checked_json(load(PROOF_TAG,spec['name']),spec['sha256'],'CIK proof')
        if proof['status'] not in ('INTEGRITY_PASS','INTEGRITY_PASS_WITH_QUARANTINE'):raise ValueError('shard source proof failed')
        shard=proof['shard'];tag=proof['selected_tag']
        if type(shard) is not int or not 0<=shard<16 or shard in seen_shards:raise ValueError('source shard differs or repeated')
        if tag!=summary['selected_sources'][str(shard)]:raise ValueError('selected source tag differs')
        seen_shards.add(shard);records=proof['verified'];mapped={}
        if proof['verified_ciks']!=len(records):raise ValueError('CIK proof count differs')
        if sum(r['fact_rows'] for r in records.values())!=proof['numeric_fact_rows']:raise ValueError('CIK proof fact rows differ')
        for ref in proof['archives']:
            name=ref['receipt']
            if not re.fullmatch(rf'sec_world_shard_{shard:03d}_attempt_\d+_part_\d+\.json',name):raise ValueError('source receipt path differs')
            manifest=checked_json(load(tag,name),ref['receipt_sha256'],'source receipt')
            if manifest['archive_sha256']!=ref['archive_sha256']:raise ValueError('source archive fingerprint differs')
            members=manifest['members'];by_name={m['name']:m for m in members}
            if len(members)!=len(by_name):raise ValueError('duplicate source manifest member')
            archive=dict(source_tag=tag,receipt=name,receipt_sha256=ref['receipt_sha256'],
                archive=name[:-5]+'.tar',archive_sha256=ref['archive_sha256'],
                archive_member_bytes=sum(m['bytes'] for m in members),members=len(members))
            archives.append(archive)
            for member in members:
                match=re.fullmatch(r'CIK(\d{10})\.facts\.parquet',member['name'])
                if not match:continue
                cik=int(match[1]);record=records.get(str(cik));prefix=f'CIK{cik:010d}'
                if record is None or cik in mapped or cik in all_rows:raise ValueError('unproven or duplicate source CIK')
                raw=by_name.get(prefix+'.companyfacts.json.gz');official=by_name.get(prefix+'.submissions.json.gz')
                if raw is None or official is None:raise ValueError('paired raw/official CIK source missing')
                if (record['cik']!=cik or record['official_cik']!=cik or record['source_tag']!=tag or
                    record['raw_sha256']!=raw['sha256'] or record['parquet_sha256']!=member['sha256']):raise ValueError('CIK source identity/member fingerprint differs')
                is_quarantined=bool(record['quarantined'])
                if is_quarantined!=(cik in expected_quarantine) or (not is_quarantined and canonical_cik(record['root_cik'])!=cik):raise ValueError('CIK identity quarantine differs')
                row=dict(cik=cik,shard=shard,fact_rows=record['fact_rows'],quarantined=is_quarantined,
                    identity_scope='CIK_ONLY_NO_HISTORICAL_TICKER_ASSIGNMENT',
                    source_archive=archive,raw_member=raw,numeric_member=member,official_submissions_member=official,
                    entity_name=record['entity_name'],historical_ticker_mapping='UNPROVEN')
                mapped[cik]=row
                if is_quarantined:quarantined.append(row)
        if set(mapped)!={int(cik) for cik in records}:raise ValueError('proof CIK has no unique source archive')
        all_rows.update(mapped)
    if len(all_rows)!=summary['verified_ciks'] or sum(r['fact_rows'] for r in all_rows.values())!=summary['numeric_fact_rows']:
        raise ValueError('complete source universe counts differ')
    if len(archives)!=summary['archives_verified'] or {r['cik'] for r in quarantined}!=expected_quarantine:
        raise ValueError('complete archive/quarantine inventory differs')
    eligible=[r for _,r in sorted(all_rows.items()) if not r['quarantined']]
    return dict(status='COMPLETE_AUDITED_CIK_SOURCE_INDEX_NOT_NATIVE_WORLD',source_proof_release=PROOF_TAG,
        source_proof_commit=summary['proof_source_commit'],source_proof_files=proofs,
        source_cik_records=len(all_rows),eligible_ciks=len(eligible),quarantined_ciks=quarantined,
        source_fact_rows=sum(r['fact_rows'] for r in all_rows.values()),eligible_fact_rows=sum(r['fact_rows'] for r in eligible),
        archives=archives,records=eligible,provider_requests=0,world_gate='NOT_PROVEN',scoring_gate='CLOSED',
        verification_scope='All sixteen proof and 208 receipt hashes/identities bound; archive payloads inherit prior full-reparse proof, not reread by this index builder',
        remaining=['native CIK-state production beyond the existing 20-CIK sample','complete financial concept/settings/question registry',
                   'historical stock/CIK ownership and tradeability','full dependency storage budget and comprehensive leak gate'])


def main():
    from ci.release_assets import download_asset
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    summary=json.loads(Path('docs/SEC_FULL_SOURCE_PROOF_SUMMARY.json').read_text())
    def load(tag,name):return download_asset(tag,name,args.directory/'source'/tag).read_bytes()
    result=build_index(summary,load);file=args.directory/'SEC_CIK_SOURCE_INDEX_V1.json'
    file.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('CIK_SOURCE_INDEX',result['eligible_ciks'],result['eligible_fact_rows'],digest(file.read_bytes()),flush=True)


if __name__=='__main__':main()

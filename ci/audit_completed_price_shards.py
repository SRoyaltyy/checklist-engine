"""Offline provenance audit of completed price shards; no compute or publication."""
import argparse
import hashlib
import json
from pathlib import Path


FINAL='PRICE_ANSWER_SHARD_COMPLETE_WITH_EXPLICIT_EXCLUSIONS_NOT_FULL_WORLD'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def audit(plan_raw,shards,inventories,inputs_release,producer_commit,plan_sha256):
    if sha(plan_raw)!=plan_sha256:raise ValueError('pinned plan fingerprint differs')
    plan=json.loads(plan_raw);request=plan['request'];parts=plan['parts']
    planned=[ticker for part in parts for ticker in part['tickers']]
    if (len(planned)!=len(set(planned)) or len(planned)!=plan['accepted_tickers'] or
        plan['accepted_tickers']+plan['source_excluded_tickers']!=plan['original_universe']):
        raise ValueError('plan universe membership differs')
    if set(shards)!=set(inventories):raise ValueError('summary/inventory index membership differs')
    reports=[];done=[];excluded=[];payload_bytes=0;release_bytes=0
    for index,raw in sorted(shards.items()):
        if type(index) is not int or not 0<=index<len(parts):raise ValueError('unknown source part index')
        state=json.loads(raw);inventory=inventories[index];tag=inputs_release.removesuffix('-inputs')+f'-{index:03d}'
        if (inventory['tag']!=tag or inventory['draft'] or state['status']!=FINAL or
            state['inputs_release']!=inputs_release or state['source_commit']!=producer_commit or
            state['recipe_fingerprint']!=request['corrected_recipe_fingerprint'] or state['source_part']!=parts[index]):
            raise ValueError('completed shard source/version/release differs')
        assets={a['name']:a for a in inventory['assets']}
        if len(assets)!=len(inventory['assets']):raise ValueError('duplicate release asset')
        if any(a.get('state')!='uploaded' or type(a['size']) is not int or a['size']<=0 for a in assets.values()):
            raise ValueError('nonfinal or invalid release asset')
        summary=assets['COMPACT_WORLD_SHARD.json']
        if summary['size']!=len(raw) or summary['digest']!='sha256:'+sha(raw):raise ValueError('summary asset fingerprint differs')
        names=[r['ticker'] for r in state['completed']+state['excluded']]
        if len(names)!=len(set(names)) or set(names)!=set(parts[index]['tickers']):raise ValueError('shard stock membership differs')
        known_assets=set();own_bytes=0
        for row in state['completed']:
            expected=row['ticker'].encode().hex()+'.diagnostic_answers.tar.zst'
            if row['release']!=tag or row['asset']!=expected or row['asset'] in known_assets:
                raise ValueError('stock payload identity differs')
            asset=assets[expected];known_assets.add(expected)
            if (asset['size']!=row['answer_container_bytes'] or asset['digest']!='sha256:'+row['answer_container_sha256'] or
                row['shared_registry_sha256']!=request['registry_sha256'] or
                row['diagnostic_questions']!=68904 or row['roundtrip']!='ALL_CELLS_EXACT_WITH_MISSING_DISTINCT'):
                raise ValueError('stock payload/schema fingerprint differs')
            own_bytes+=asset['size'];done.append(row['ticker'])
        payloads={name for name in assets if name.endswith('.diagnostic_answers.tar.zst')}
        if payloads!=known_assets or own_bytes!=state['answer_bytes']:raise ValueError('orphan payload or byte total differs')
        for row in state['excluded']:
            if not row.get('reason'):raise ValueError('stock exclusion reason missing')
            excluded.append(dict(row,index=index))
        own_release_bytes=sum(a['size'] for a in assets.values());payload_bytes+=own_bytes;release_bytes+=own_release_bytes
        reports.append(dict(index=index,release=tag,summary_sha256=sha(raw),completed=len(state['completed']),
                            excluded=len(state['excluded']),payload_bytes=own_bytes,release_bytes=own_release_bytes))
    complete=len(shards)==len(parts);coverage=100*len(done)/plan['original_universe']
    size_cuts=[r['ticker'] for r in excluded if r['reason']=='ANSWER_STORAGE_BUDGET']
    price_gate=('PENDING_UNFINISHED_SHARDS' if not complete else
                'PASS_PRICE_COVERAGE_ONLY' if coverage>=95 else 'FAIL_BELOW_95_PERCENT_ORIGINAL')
    storage_policy='FAIL_LEGACY_SIZE_EXCLUSIONS_REQUIRE_RECOVERY' if size_cuts else 'NO_SIZE_EXCLUSIONS_IN_AUDITED_SHARDS'
    return dict(status='COMPLETE_PRICE_METADATA_AUDIT_NOT_WORLD' if complete else 'PARTIAL_COMPLETED_PRICE_METADATA_AUDIT_NOT_WORLD',
        inputs_release=inputs_release,producer_commit=producer_commit,plan_sha256=sha(plan_raw),
        audit_code_sha256=sha(Path(__file__).read_bytes()),
        inventory_snapshot_sha256=sha(json.dumps(inventories,sort_keys=True,separators=(',',':')).encode()),
        source_stitch_sha256=plan['source_stitch_sha256'],recipe_fingerprint=request['corrected_recipe_fingerprint'],
        shared_registry_sha256=request['registry_sha256'],original_universe=plan['original_universe'],
        source_accepted_tickers=plan['accepted_tickers'],source_excluded_tickers=plan['source_excluded_tickers'],
        audited_shards=len(shards),planned_shards=len(parts),unaudited_shards=sorted(set(range(len(parts)))-set(shards)),
        completed_tickers=len(done),build_excluded_tickers=len(excluded),confirmed_completed_percent_original=coverage,
        payload_bytes=payload_bytes,release_bytes_including_checkpoints=release_bytes,
        exclusions=excluded,legacy_size_exclusions_requiring_recovery=size_cuts,price_coverage_gate=price_gate,
        storage_policy=storage_policy,price_budget_gate='NOT_MEASURED_FULL_DEPENDENCY_CLOSURE_REQUIRED',
        payload_verification='RELEASE_SIZE_SHA256_AND_WORKER_ROUNDTRIP_ASSERTION_NOT_INDEPENDENT_PAYLOAD_DECODE',
        shards=reports,world_gate='NOT_PROVEN',scoring_gate='CLOSED')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--inputs-release',required=True);parser.add_argument('--producer-commit',required=True)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    inventories={int(i):v for i,v in json.loads((args.directory/'INVENTORIES.json').read_text()).items()}
    shards={i:(args.directory/f'{i:03d}.json').read_bytes() for i in inventories}
    report=audit((args.directory/'PLAN.json').read_bytes(),shards,inventories,args.inputs_release,args.producer_commit,args.plan_sha256)
    args.out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('status','audited_shards','completed_tickers','build_excluded_tickers','payload_bytes','price_coverage_gate','storage_policy')}))


if __name__=='__main__':main()

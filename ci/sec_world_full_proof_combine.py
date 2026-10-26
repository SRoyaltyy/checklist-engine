"""Combine all 16 raw SEC integrity proofs without hiding quarantine or mapping gaps."""
import hashlib,json,os
from pathlib import Path
def main():
    root=Path('sec-full-proof');files=sorted(root.glob('SEC_FULL_SOURCE_PROOF_*.json'))
    files=[p for p in files if p.name!='SEC_FULL_SOURCE_PROOF_SUMMARY.json']
    reports=[json.loads(p.read_text()) for p in files]
    if len(reports)!=16 or {r['shard'] for r in reports}!=set(range(16)):raise ValueError('Incomplete shard proof grid')
    ciks=[int(cik) for r in reports for cik in r['verified']]
    if len(ciks)!=4034 or len(set(ciks))!=4034:raise ValueError('Incomplete or repeated CIK proof')
    quarantine=[record for r in reports for record in r['quarantined']]
    if {r['cik'] for r in quarantine}!={1790169}:raise ValueError('Unexpected quarantine set')
    summary=dict(status='INTEGRITY_PASS_WITH_QUARANTINE',verified_ciks=len(ciks),numeric_fact_rows=sum(r['numeric_fact_rows'] for r in reports),archives_verified=sum(len(r['archives']) for r in reports),quarantined=quarantine,universe_tickers=8727,resolved_ticker_identities=4040,unresolved_ticker_identities=4687,base_tag=reports[0]['base_tag'],selected_sources={str(r['shard']):r['selected_tag'] for r in reports},proof_source_commit=os.environ['GITHUB_SHA'],run_url='https://github.com/'+os.environ['GITHUB_REPOSITORY']+'/actions/runs/'+os.environ['GITHUB_RUN_ID'],world_gate='FAIL',scope='Every selected raw archive and member hash checked; every numeric Parquet reparsed exactly from raw companyfacts. CIK1790169 remains quarantined pending James review. Unmapped universe identities remain unresolved. Not Phase 1/world approval.',proof_files=[dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    (root/'SEC_FULL_SOURCE_PROOF_SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print('SEC_FULL_SOURCE_PROOF_SUMMARY',json.dumps(summary),flush=True)
if __name__=='__main__':main()

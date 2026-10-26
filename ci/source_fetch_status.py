"""Validate source outcomes and publish explicitly provisional coverage evidence."""
import argparse,csv,hashlib,json,os
from pathlib import Path
from ci.world_source_evidence import collect,verified_blocker,blocked_reports


def assess(directory):
    reports=[json.loads(p.read_text()) for p in Path(directory).glob('xbrl_shard_*.progress.json')]
    if not reports:raise ValueError('SEC source produced no progress report')
    errors=[r for report in reports for r in report.get('errors',{}).values()]
    rows=sum(r.get('rows',0) for r in reports)
    if rows and not errors and all(len(r.get('done',{}))==r.get('requested') for r in reports):return dict(status='PASS',rows=rows,reports=reports)
    if blocked_reports(reports):
        return dict(status='BLOCKED',rows=0,reports=reports)
    raise ValueError('SEC source is incomplete or its failure lacks fair-access evidence')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',required=True)
    parser.add_argument('--measurements',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    status=assess(args.source_root)
    from ci.world_v2_coverage import build
    measured_path=Path(args.measurements);measured=json.loads(measured_path.read_text())
    evidence=collect(args.source_root);rows,failures=build(measured,source_evidence=evidence)
    affected=[r for r in rows if r['namespace']=='dictionary' and r['item_id'] in ('I192','I193','I194')]
    if status['status']=='BLOCKED':
        if not affected or any(r['status']!='BLOCKED' for r in affected):
            raise ValueError('verified SEC failure not reflected in every coverage timeframe')
        if any(c.startswith('xb_') and r['non_null_rows'] for c,r in measured['columns'].items()):
            raise ValueError('blocked-source evidence conflicts with supplied XBRL measurements')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    for row in rows:row['universe_scope']='SIX_STOCK_PROVISIONAL_NOT_FULL_UNIVERSE'
    with open(out/'WORLD_COVERAGE.csv','w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    status.update(source_commit=os.environ.get('GITHUB_SHA'),
        run_url='https://github.com/'+os.environ.get('GITHUB_REPOSITORY','SRoyaltyy/checklist-engine')+'/actions/runs/'+os.environ.get('GITHUB_RUN_ID','local'),
        measured_world_gate='FAIL' if failures else 'PASS',coverage_failures=len(failures),
        measurements_sha256=hashlib.sha256(measured_path.read_bytes()).hexdigest(),
        scope='Source handling proof only; six-stock released measurements, not full-universe coverage.')
    (out/'SEC_SOURCE_STATUS.json').write_text(json.dumps(status,indent=2))
    print(json.dumps({k:v for k,v in status.items() if k!='reports'}),flush=True)


if __name__=='__main__':main()

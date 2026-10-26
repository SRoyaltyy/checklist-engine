"""Publish immutable, hashed source archives only after their explicit source gate."""
import argparse,hashlib,json,os,subprocess,tarfile
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--kind',choices=['sec','fred'],required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
    root=Path(a.source)
    if a.kind=='sec':
        from ci.source_fetch_status import assess
        status=assess(root)
        if status['status']!='PASS':raise ValueError('Real numeric companyfacts required; BLOCKED does not pass this source gate')
        if any(any(v!='OK' for v in r['done'].values()) for r in status['reports']):raise ValueError('Probe company has no structured facts')
    else:
        status=json.loads((root/'fred.source.json').read_text())
        from fetch.fetch_fred import SERIES
        if status['status']!='PASS' or set(status['series'])!=set(SERIES):raise ValueError('Missing registered macro series')
        if any(r['rows']<=0 for r in status['series'].values()):raise ValueError('Empty macro series')
    files=sorted(p for p in root.rglob('*') if p.is_file())
    if not files:raise ValueError('No source assets')
    archive=root.parent/(a.kind+'_structured_source.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        for p in files:tar.add(p,arcname=p.relative_to(root),recursive=False)
    manifest=dict(kind=a.kind,source_commit=os.environ['GITHUB_SHA'],run_url='https://github.com/'+os.environ['GITHUB_REPOSITORY']+'/actions/runs/'+os.environ['GITHUB_RUN_ID'],scope='Source-only evidence; no complete world-state approval',status=status,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    target=root.parent/(a.kind+'_structured_source.json');target.write_text(json.dumps(manifest,indent=2))
    subprocess.run(['gh','release','create',a.tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title',a.tag,'--notes',manifest['scope'],str(archive),str(target)],check=True)
    result=subprocess.run(['gh','release','view',a.tag,'--json','assets'],check=True,capture_output=True,text=True)
    assets=json.loads(result.stdout)['assets']
    expected={p.name:p.stat().st_size for p in (archive,target)}
    if {a['name']:a['size'] for a in assets}!=expected:raise ValueError('Published source assets missing or wrong sizes')
    subprocess.run(['gh','release','edit',a.tag,'--draft=false'],check=True)
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':main()

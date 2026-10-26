"""Replace obsolete source-block evidence only after checking real archived SEC facts."""
import csv,gzip,hashlib,json,os,subprocess,tarfile
from pathlib import Path

def main():
    manifest=json.loads(Path('sec_structured_source.json').read_text())
    archive=Path('sec_structured_source.tar.gz')
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['archive_sha256']:raise ValueError('SEC source archive mismatch')
    if manifest['status']['status']!='PASS' or manifest['status']['rows']<=0:raise ValueError('No numeric source proof')
    raw_count=0
    with tarfile.open(archive) as tar:
        actual={m.name:m for m in tar if m.isfile()}
        for record in manifest['files']:
            data=tar.extractfile(actual[record['path']]).read()
            if hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('SEC source member mismatch')
            if record['path'].endswith('.json.gz'):
                payload=json.loads(gzip.decompress(data))
                if not payload.get('facts'):raise ValueError('Empty raw companyfacts')
                raw_count+=1
    if raw_count!=3:raise ValueError('Expected all three probe companies')
    subprocess.run(['git','fetch','origin','main'],check=True)
    subprocess.run(['git','checkout','-B','sec-source-unblocked-publication','origin/main'],check=True)
    target=Path('docs/WORLD_COVERAGE.csv')
    with target.open(newline='',encoding='utf8') as stream:reader=csv.DictReader(stream);rows=list(reader);fields=reader.fieldnames
    changed=0
    for row in rows:
        if row['namespace']=='dictionary' and row['item_id'] in ('I192','I193','I194') and row['status']=='BLOCKED':
            row['status']='PENDING'
            row['reason']='SEC relay access proved with real numeric companyfacts; full-universe numeric snapshot join and measurement still pending.'
            row['source_evidence']=json.dumps(dict(status='PASS',run_url=manifest['run_url'],source_commit=manifest['source_commit'],rows=manifest['status']['rows'],archive_sha256=manifest['archive_sha256']))
            changed+=1
    if changed not in (0,66):raise ValueError('Unexpected affected SEC coverage row count '+str(changed))
    with target.open('w',newline='',encoding='utf8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    status=dict(manifest['status'],run_url=manifest['run_url'],source_commit=manifest['source_commit'],source_archive_sha256=manifest['archive_sha256'],raw_companyfacts=raw_count,scope='Three-company source-access proof only. Full-universe world gate remains FAIL; these source rows are PENDING until rebuilt and measured.')
    Path('docs/SEC_SOURCE_STATUS.json').write_text(json.dumps(status,indent=2))
    subprocess.run(['git','config','user.name','github-actions[bot]'],check=True)
    subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
    subprocess.run(['git','add','docs/WORLD_COVERAGE.csv','docs/SEC_SOURCE_STATUS.json'],check=True)
    if subprocess.run(['git','diff','--cached','--quiet']).returncode==0:return
    subprocess.run(['git','commit','-m','Clear obsolete SEC access blocks with verified real relay data; snapshot remains pending'],check=True)
    for attempt in range(5):
        if subprocess.run(['git','push','origin','HEAD:main']).returncode==0:
            print('SEC_SOURCE_ACCESS_UNBLOCKED',changed,flush=True);return
        subprocess.run(['git','fetch','origin','main'],check=True)
        subprocess.run(['git','rebase','origin/main'],check=True)
    raise RuntimeError('Main proof publication failed')
if __name__=='__main__':main()

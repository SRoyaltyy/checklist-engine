"""Validate and fingerprint the real source artifacts before archival."""
import hashlib,json,os
from pathlib import Path


def main():
    root=Path('source-inputs')
    fred=json.loads((root/'fred/fred_wide_2020_26.source.json').read_text())
    prices=json.loads((root/'prices/PRICE_FETCH_REPORT.json').read_text())
    xbrl=json.loads((root/'companyfacts/xbrl_shard_000.progress.json').read_text())
    if fred['status']!='PASS' or fred['rows']!=38038 or len(fred['series'])!=5:
        raise ValueError('ALFRED artifact does not match the verified source run')
    if prices['errors'] or len(prices['completed'])!=20:
        raise ValueError('daily-price source artifact is incomplete')
    files=[]
    for file in sorted(root.rglob('*')):
        if file.is_file():
            files.append(dict(path=str(file.relative_to(root)),bytes=file.stat().st_size,
                sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    manifest=dict(status='PROVISIONAL_SOURCE_ARCHIVE',source_run=int(os.environ['SOURCE_RUN']),
        source_commit=os.environ['SOURCE_SHA'],archive_commit=os.environ['GITHUB_SHA'],
        fred=dict(status=fred['status'],rows=fred['rows'],series=fred['series']),
        daily_prices=dict(completed=prices['completed'],nominal_price_basis_verified=False),
        companyfacts=dict(status='FAIL' if xbrl['errors'] else 'PASS',errors=xbrl['errors'],rows=xbrl['rows']),
        files=files,scope='5 macro series and 6 pilot stocks plus 14 ETFs; not full world coverage')
    Path('WORLD_INPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','daily_prices','fred')}),flush=True)


if __name__=='__main__':main()

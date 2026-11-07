"""Bounded public OI source observations, executed only on GitHub Actions."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path

from ci import release_assets as releases
from scripts.nai import common

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/'ci/OI_SOURCE_PROFILE_REQUEST.json'
SOURCES={
 'occ_series_AAPL':'https://marketdata.theocc.com/series-search?symbolType=U&symbol=AAPL',
 'occ_directory':'https://marketdata.theocc.com/delo-download?prodType=ALL&downloadFields=OS;US;SN&format=txt',
 'cboe_chain_AAPL':'https://cdn.cboe.com/api/global/delayed_quotes/options/AAPL.json',
 'occ_series_documentation':'https://www.theocc.com/market-data/market-data-reports/other-market-data-info/batch-processing/series-search-batch-processing',
}
LEGACY=dict(release='nai-occ-oi-daily-v1',asset='occ_oi_20261102.parquet',bytes=2315105,
            sha256='326a7d7794ec3f294b4c21f3cc29afcb07cb5669dfa43638bb8c10395faaa146')
UA='Mozilla/5.0 (checklist-engine public market-data research)'


def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return releases._digest(path).removeprefix('sha256:')


def validate_request(value):
    if (set(value)!= {'version','execute','scope'} or value['version']!=1 or type(value['execute']) is not bool
            or value['scope']!='OI_CURRENT_SOURCES_AND_FROZEN_LEGACY_OBSERVATION'):
        raise ValueError('OI source profile request differs')
    return value


def inspect_bytes(name,raw):
    if name=='cboe_chain_AAPL':
        value=json.loads(raw);rows=value['data']['options']
        if not isinstance(rows,list) or not rows:raise ValueError('empty options chain')
        return dict(timestamp_raw=value.get('timestamp'),symbol_raw=value['data'].get('symbol'),rows=len(rows),
            fields=sorted({k for row in rows for k in row}),sample=rows[:3],
            open_interest_null=sum(r.get('open_interest') is None for r in rows))
    text=raw.decode('latin1')
    return dict(lines=len(text.splitlines()),head='\n'.join(text.splitlines()[:18])[:6000])


def legacy_profile(path):
    import pyarrow.parquet as pq
    with pq.ParquetFile(path) as file:
        fields=file.schema_arrow.names
        if fields!=['ticker','product','expiry','strike','call_oi','put_oi','snapshot_utc']:
            raise ValueError('frozen legacy schema differs')
        tickers=set();days=set();invalid=0;rows=0;sample=[]
        for batch in file.iter_batches(batch_size=50000):
            for row in batch.to_pylist():
                rows+=1;tickers.add(row['ticker']);days.add(row['snapshot_utc'])
                invalid+=any(row[k] is None or row[k]<0 for k in ('call_oi','put_oi'))
                if len(sample)<3:sample.append(row)
        return dict(rows=rows,tickers=len(tickers),snapshot_labels=sorted(days),invalid_oi_rows=invalid,
            schema=str(file.schema_arrow),sample=sample,
            provenance_status='LEGACY_UNVERIFIED_SOURCE_RAW_AND_OI_ASOF_NOT_RETAINED',
            historical_oi_session='UNKNOWN',acquisition_time='UNKNOWN',backfill_proof=False)


def run(root):
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('GITHUB_REPOSITORY')!='SRoyaltyy/checklist-engine':
        raise ValueError('OI observations run only on the authorized GitHub runner')
    request=validate_request(json.loads(REQUEST.read_bytes()))
    if not request['execute']:raise ValueError('OI source observations disabled')
    root.mkdir(parents=True,exist_ok=True)
    tag=f"oi-source-profile-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    report=dict(format='OI_SOURCE_PROFILE_V1',status='FAIL',actual_run_id=os.environ['GITHUB_RUN_ID'],
        actual_attempt=os.environ['GITHUB_RUN_ATTEMPT'],source_commit=os.environ['GITHUB_SHA'],started_at=now(),
        sources=[],assets=[],scoring_gate='CLOSED',scope='SOURCE_OBSERVATIONS_NOT_DAILY_COLLECTION_OR_HISTORICAL_BACKFILL')
    releases.gh_retry('release','create',tag,'--draft','--target',os.environ['GITHUB_SHA'],'--title',tag,
        '--notes','Bounded OI source observations. No complete panel or historical backfill claim.')
    def publish(path):
        binding=dict(name=path.name,bytes=path.stat().st_size,sha256=sha(path))
        releases.publish_assets(tag,path);report['assets'].append(binding)
    try:
        for name,url in SOURCES.items():
            entry=dict(name=name,url=url,started_at=now(),status='FAIL');report['sources'].append(entry)
            path=root/(name+'.raw')
            try:
                common.get(url,str(path),ua=UA,pace=1.0,tries=2,timeout=90,max_bytes=20000000)
                entry.update(bytes=path.stat().st_size,sha256=sha(path),inspection=inspect_bytes(name,path.read_bytes()),status='OBSERVED')
                publish(path)
            except Exception as exc:
                entry['error']=getattr(exc,'evidence',dict(type=type(exc).__name__,message=common.redact(exc)))
                if path.exists():publish(path)
            entry['finished_at']=now()
        path=releases.download_asset(LEGACY['release'],LEGACY['asset'],root)
        if path.stat().st_size!=LEGACY['bytes'] or sha(path)!=LEGACY['sha256']:
            raise ValueError('legacy OI source fingerprint differs')
        report['legacy']=dict(LEGACY,profile=legacy_profile(path));publish(path)
        report['status']='MEASURED_BOUNDED_SOURCE_OBSERVATIONS_ONLY'
    except Exception as exc:
        report['error']=dict(type=type(exc).__name__,message=common.redact(exc));raise
    finally:
        report['finished_at']=now();path=root/'OI_SOURCE_PROFILE_V1.json'
        path.write_text(json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
        releases.publish_assets(tag,path);releases.gh_retry('release','edit',tag,'--draft=false','--notes',report['status'])
        print('OI_SOURCE_PROFILE_FINAL',tag,report['status'],flush=True)


if __name__=='__main__':run(Path('oi-source-profile-output'))

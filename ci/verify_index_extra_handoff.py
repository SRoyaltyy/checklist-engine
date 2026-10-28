"""Verify unclaimed index/extra-ETF evidence handed to Cursor Bot."""
import json
from pathlib import Path
from ci.verify_etf_daily_source import verify

INDEX={'SPY','QQQ','IWM','DIA'}
EXTRA={'TLT','HYG','LQD','UUP','GLD','CPER','USO','RSP','VXX','IBIT','DIA'}


def run():
    expected=json.loads(Path('docs/ETF_BASELINE_SOURCE_FETCHED_V1.json').read_text(encoding='utf-8'))
    actual=verify(expected['release'],expected['source_head'])
    if actual!=expected:raise ValueError('released ETF byte proof differs from committed self-verification')
    records={row['ticker']:row for row in actual['records']}
    macro=json.loads(Path('docs/MACRO_SOURCE_STATUS_V3.json').read_text(encoding='utf-8'))
    for file in sorted(Path('docs').glob('INDEX_EXTRA_SOURCE_HANDOFF_*.json')):
        claim=json.loads(file.read_text(encoding='utf-8'));ident=claim['checklist_id']
        if claim['contributor_status']!='EVIDENCE_ONLY_CHECKBOX_UNCLAIMED' or claim['handoff_owner']!='Cursor Bot':
            raise ValueError('handoff ownership/status differs')
        selected=INDEX if ident in ('1.136','1.137') else EXTRA if ident in ('1.146','1.147') else None
        if selected is None or set(claim['symbols'])!=selected:raise ValueError('source-claim symbol grid differs')
        if claim['release']!=actual['release'] or claim['stock_cutoff']!=actual['stock_cutoff']:
            raise ValueError('source-claim release/cutoff differs')
        for row in claim['assets']:
            original=records[row['ticker']]
            if any(row[key]!=original[key] for key in ('ticker','file','sha256','rows','first','last')):
                raise ValueError('source-claim asset binding differs')
            if original['last']!=actual['stock_cutoff']:raise ValueError('ETF does not reach approved stock cutoff')
        if {r['ticker'] for r in claim['assets']}!=selected:raise ValueError('source-claim asset membership differs')
        if ident=='1.136':
            if ('VIXCLS' not in macro['registered_I178'] or macro['status']['series']['VIXCLS']['status']!='PASS'
                or claim['vix_source']['series']!='VIXCLS'
                or claim['vix_source']['archive_sha256']!=macro['archive_sha256']):
                raise ValueError('market VIX source must be the verified ALFRED vintage series')
        print('INDEX_EXTRA_SOURCE_HANDOFF_VERIFIED',ident,len(selected),actual['stock_cutoff'])


if __name__=='__main__':run()

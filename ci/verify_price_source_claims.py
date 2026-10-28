"""Recheck source-only claims against the exact released full-universe stitch."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import urllib.request


def verify(directory):
    directory=Path(directory)
    files=sorted(directory.glob('PRICE_SOURCE_CLAIM_*.json'))
    if not files:raise ValueError('no source claim evidence')
    claims=[json.loads(p.read_text(encoding='utf-8')) for p in files]
    source=claims[0]['stitch']
    raw=urllib.request.urlopen(source['url'],timeout=180).read()
    if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('published stitch bytes changed')
    status=json.loads(raw)
    if (status['original_universe']!=8727 or status['accepted_tickers']!=8316
        or len(status['records'])!=8316 or status['excluded_tickers']!=411
        or 100*status['accepted_tickers']/status['original_universe']<95):
        raise ValueError('claim universe differs from owner-approved source')
    record_names=[r['ticker'] for r in status['records']]
    part_names=[t for p in status['parts'] for t in p['tickers']]
    if len(set(record_names))!=len(record_names) or sorted(record_names)!=sorted(part_names):
        raise ValueError('published source part membership differs')
    with Path('dictionary/DATA_SOURCES.csv').open(encoding='utf-8-sig',newline='') as stream:
        sources={r['id']:r for r in csv.DictReader(stream)}
    with (directory/'PRICE_DERIVED_SOURCE_COVERAGE.csv').open(encoding='utf-8',newline='') as stream:
        coverage=list(csv.DictReader(stream))
    for claim in claims:
        if claim['stitch']!=source or claim['scope']!='SOURCE_LOCATED_ONLY':raise ValueError('claim source/scope differs')
        own=[r for r in coverage if r['checklist_id']==claim['checklist_id']]
        if sorted(r['item_id'] for r in own)!=sorted(claim['item_ids']):raise ValueError('source coverage item grid differs')
        for row in own:
            if ('Yahoo' not in sources[row['item_id']]['source'] or row['status']!='SOURCE_LOCATED_ONLY'
                or row['bar_asset']!='<ticker UTF-8 hex>.bars.parquet'
                or row['source_stitch_sha256']!=source['sha256']):
                raise ValueError('source coverage row differs')
        print('PRICE_SOURCE_CLAIM_VERIFIED',claim['checklist_id'],len(own),8316,8727)
    return claims


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',default='docs')
    args=parser.parse_args();verify(args.directory)

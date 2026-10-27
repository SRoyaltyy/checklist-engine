"""Archive pinned org numeric/categorical captures without backdating them."""
import argparse
import hashlib
import io
import json
import math
import os
import re
import tarfile
import urllib.request
from pathlib import Path

import pandas as pd

from ci.native_price_blocks import sha, write_json
from ci.release_assets import gh_retry, publish_assets

THEME_IDS = ['Ticker', 'Industry', 'Sector', 'Country', 'Exchange', 'Index', 'scrape_ts']
THEME_NUMERIC = ['Market Cap', 'Price', 'Average Volume', 'Short Float', 'Short Ratio',
    'Institutional Transactions', 'Institutional Ownership', 'Insider Transactions',
    'Insider Ownership', 'Analyst Recom', 'Target Price', 'Forward P/E', 'EV/Sales', 'PEG',
    'Performance (Week)', 'Performance (Month)', 'Performance (Quarter)', 'Performance (Half Year)',
    'Performance (YTD)', 'Performance (Year)', 'Relative Volume', 'Relative Strength Index (14)',
    'Sales Year Over Year TTM', 'Sales Growth Quarter Over Quarter', 'EPS Surprise', 'Revenue Surprise',
    'Gross Margin', 'Operating Margin', 'Profit Margin', '20-Day Simple Moving Average',
    '50-Day Simple Moving Average', '200-Day Simple Moving Average', 'EPS Growth This Year',
    'EPS Growth Next Year', 'Beta', 'Volume', 'Average True Range', 'Volatility (Week)',
    'Volatility (Month)', 'Total Debt/Equity', 'Current Ratio', 'Open']
PEER_NUMERIC = ['n_peers', 'n_peers_present', 'perf_week', 'perf_month', 'perf_quarter',
                'change', 'peer_med_week', 'peer_med_month', 'rs_week', 'rs_month',
                'rs_quarter', 'beat_week_pct']


def verify_blob(raw, meta):
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if len(raw) != meta['size'] or blob != meta['git_blob_sha1']:
        raise ValueError('pinned org source size/blob differs: ' + meta['path'])


def fetch_blob(repo, commit, meta):
    if not re.fullmatch('[0-9a-f]{40}', commit) or not meta['path'].startswith('data/'):
        raise ValueError('org source must be a pinned data path')
    if meta['size'] <= 0 or meta['size'] > 32000000:
        raise ValueError('org source exceeds bounded file size')
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{meta['path']}"
    with urllib.request.urlopen(url, timeout=90) as response:
        raw = response.read(meta['size'] + 1)
    verify_blob(raw, meta)
    return raw, url


def numeric(value):
    text = str(value).strip().replace(',', '')
    if text.lower() in ('', '-', '--', 'nan', 'n/a', 'none'):
        return float('nan'), False
    scale = 1.
    if text.endswith('%'):
        scale = .01
        text = text[:-1]
    elif text[-1:].upper() in ('K', 'M', 'B', 'T'):
        scale = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}[text[-1].upper()]
        text = text[:-1]
    try:
        value = float(text) * scale
        if not math.isfinite(value):
            raise ValueError('nonfinite')
        return value, False
    except ValueError:
        return float('nan'), True


def project(raw, kind):
    source = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    if kind == 'correlations':
        expected = ['ticker', *['peer_' + str(i) for i in range(1, 11)]]
        if not set(expected) <= set(source):
            raise ValueError('peer membership source schema differs')
        frame = source[expected].copy()
        return frame, dict(rows=len(frame), numeric_columns=[], unparsed_numeric={},
                           scope='captured static membership; rolling PIT peers NOT_PROVEN')
    ids, numbers = (THEME_IDS, THEME_NUMERIC) if kind == 'theme' else (['Ticker', 'peers', 'peers_used'], PEER_NUMERIC)
    if not {'Ticker', 'Price' if kind == 'theme' else 'rs_week'} <= set(source):
        raise ValueError('numeric org source schema differs')
    frame = source[[c for c in ids if c in source]].copy()
    invalid = {}
    for column in numbers:
        if column in source:
            values = [numeric(value) for value in source[column]]
            frame[column] = [value for value, _ in values]
            invalid[column] = sum(bad for _, bad in values)
    return frame, dict(rows=len(frame), numeric_columns=[c for c in numbers if c in frame],
                       missing_numeric_columns=sorted(set(numbers) - set(frame)), unparsed_numeric=invalid,
                       excluded_columns=sorted(set(source) - set(frame)),
                       units='literal numeric units; percent signs divided by 100, K/M/B/T expanded; bare numbers unchanged',
                       scope='captured numeric source only; historical availability NOT_PROVEN')


def acquire(root, request):
    root.mkdir(parents=True, exist_ok=True)
    stage = root / 'current'
    stage.mkdir(exist_ok=True)
    tag = f"org-context-sources-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    report = dict(status='INCOMPLETE_SOURCE_ONLY', source_commit=os.environ['GITHUB_SHA'], request=request,
                  receipts=[], parts=[], first_capture='2026-08-06', historical_2020_coverage='ABSENT',
                  pit_membership_gate='NOT_PROVEN', world_gate='NOT_RUN', scoring_gate='CLOSED')
    known = {}
    created = False
    pending = []

    def flush():
        nonlocal pending, created
        if not pending:
            return
        stem = f"org_context_{len(report['parts']):04d}"
        archive = root / (stem + '.tar')
        members = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(stage.iterdir())]
        with tarfile.open(archive, 'w') as tar:
            for member in members:
                tar.add(stage / member['name'], arcname=member['name'], recursive=False)
        manifest = root / (stem + '.json')
        meta = dict(archive_sha256=sha(archive), members=members, receipts=pending, status='ORG_CAPTURE_SOURCE_ONLY')
        write_json(manifest, meta)
        if not created:
            gh_retry('release', 'create', tag, '--draft', '--target', os.environ['GITHUB_SHA'], '--title', tag,
                     '--notes', 'Numeric/fixed-category captures from August 2026 onward only; no historical PIT membership, 2020 coverage or world approval.')
            created = True
        publish_assets(tag, archive, manifest)
        gh_retry('release', 'edit', tag, '--draft=false')
        report['parts'].append(dict(file=archive.name, sha256=meta['archive_sha256'], members=members))
        for member in members:
            (stage / member['name']).unlink()
        archive.unlink()
        manifest.unlink()
        pending = []
        print('ORG_SOURCE_PART_DURABLE', tag, stem, len(members), flush=True)

    try:
        for source in request['sources']:
            for meta in source['files']:
                identity = (source['repo'], meta['git_blob_sha1'])
                receipt = dict(repo=source['repo'], commit=source['commit'], **meta)
                if identity in known:
                    receipt['identical_capture_alias_of'] = known[identity]
                    report['receipts'].append(receipt)
                    continue
                raw, url = fetch_blob(source['repo'], source['commit'], meta)
                name = source['repo'].split('/')[1] + '_' + Path(meta['path']).name
                receipt.update(url=url, raw_sha256=hashlib.sha256(raw).hexdigest())
                if name.endswith('.csv'):
                    kind = 'theme' if source['repo'].endswith('/theme-radar') else ('correlations' if name.endswith('correlations.csv') else 'peer_rs')
                    frame, profile = project(raw, kind)
                    if frame.empty:
                        raise ValueError('empty numeric org capture')
                    file = stage / (name[:-4] + '.parquet')
                    frame.to_parquet(file, index=False, compression='zstd')
                    receipt.update(projected_file=file.name, projected_sha256=sha(file), profile=profile)
                else:
                    file = stage / name
                    file.write_bytes(raw)
                    receipt['metadata_only_not_features'] = True
                known[identity] = dict(repo=source['repo'], path=meta['path'])
                pending.append(receipt)
                report['receipts'].append(receipt)
                if len(pending) >= 5:
                    flush()
        flush()
        report['status'] = 'PINNED_ORG_CAPTURES_ACQUIRED_SOURCE_ONLY'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        file = root / 'ORG_SOURCE_STATUS.json'
        report['release'] = tag if created else None
        write_json(file, report)
        if created:
            publish_assets(tag, file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    acquire(Path(args.directory), json.loads(Path('ci/ORG_CONTEXT_SOURCE_REQUEST.json').read_text()))


if __name__ == '__main__':
    main()

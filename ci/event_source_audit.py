"""Audit every released event row and attempt without issuing provider requests."""
import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from ci.native_price_blocks import sha, write_json
from ci.release_assets import download_asset, publish_assets, gh_retry
from fetch.fetch_event_history import SCHEMAS


def validate_status(report, kind, expected, source_head):
    if report['kind'] != kind or report['source_commit'] != source_head:
        raise ValueError('event source identity differs')
    if report['status'] != 'REQUESTED_TICKERS_ATTEMPTED_SOURCE_ONLY':
        raise ValueError('event source shard did not complete its request')
    if report['requested_tickers'] != expected or [a['ticker'] for a in report['attempts']] != expected:
        raise ValueError('event requested/attempted universe differs')
    parts = report['parts']
    if len({p['file'] for p in parts}) != len(parts):
        raise ValueError('duplicate event part')
    rows = sum(a.get('rows', 0) for a in report['attempts'])
    if rows != report['source_rows'] or rows != sum(p['rows'] for p in parts):
        raise ValueError('event row ledger differs')
    return Counter(a['status'] for a in report['attempts'])


def validate_part(frame, kind, receipt, expected):
    if set(frame) != set(SCHEMAS[kind]) or frame.empty or len(frame) != receipt['rows']:
        raise ValueError('event row schema/count differs')
    if not set(frame.ticker) <= set(expected):
        raise ValueError('event part contains an unrequested ticker')
    if frame.duplicated().any():
        raise ValueError('duplicate event rows')
    attempts = {a['ticker']: a for a in receipt['attempts']}
    if len(attempts) != len(receipt['attempts']):
        raise ValueError('duplicate event receipt ticker')
    actual = frame.groupby('ticker').size().to_dict()
    positive = {ticker: a['rows'] for ticker, a in attempts.items() if a.get('rows', 0) > 0}
    if actual != positive:
        raise ValueError('event part per-ticker row ledger differs')
    for row in frame[['event_timestamp', 'event_date', 'source_timezone']].itertuples(index=False):
        stamp = pd.Timestamp(row.event_timestamp)
        date = stamp.tz_convert('America/New_York').date() if stamp.tz is not None else stamp.date()
        if str(date) != row.event_date or not ('2018-01-01' <= row.event_date <= '2026-10-27'):
            raise ValueError('event timestamp/date scope differs')
        if stamp.tz is None and row.source_timezone != 'PROVIDER_NAIVE_TIMEZONE_UNPROVEN':
            raise ValueError('naive event time mislabeled as proven timezone')


def audit(root, request):
    root.mkdir(parents=True, exist_ok=True)
    file = download_asset(request['inputs_tag'], 'BUILD_INPUTS.json', root)
    if sha(file) != request['inputs_sha256']:
        raise ValueError('event audit universe manifest differs')
    inputs = json.loads(file.read_text())
    names = sorted(r['ticker'] for r in inputs['records'])
    report = dict(status='INCOMPLETE_EVENT_SOURCE_AUDIT', request=request,
                  source_commit=os.environ['GITHUB_SHA'], canonical_tickers=len(names), sources={},
                  historical_completeness='NOT_PROVEN; no rows returned is not proof of zero events',
                  point_in_time_gate='NOT_PROVEN; provider event timestamps do not establish original availability/revisions',
                  world_gate='NOT_RUN', scoring_gate='CLOSED')
    try:
        for kind in SCHEMAS:
            statuses = Counter()
            fields = Counter()
            years = Counter()
            year_tickers = defaultdict(set)
            shards = []
            total = 0
            for shard in range(request['shards']):
                tag = f"event-history-{kind}-v1-{request['source_run_id']}-{request['source_run_attempt']}-{shard:03d}"
                directory = root / kind / str(shard)
                file = download_asset(tag, 'EVENT_SOURCE_STATUS.json', directory)
                own = json.loads(file.read_text())
                expected = names[shard::request['shards']]
                statuses.update(validate_status(own, kind, expected, request['source_head_sha']))
                hashes = []
                actual_ticker_rows = Counter()
                for part in own['parts']:
                    file = download_asset(tag, part['file'], directory)
                    if sha(file) != part['sha256']:
                        raise ValueError('event parquet differs from status')
                    meta = download_asset(tag, Path(part['file']).stem + '.json', directory)
                    receipt = json.loads(meta.read_text())
                    if receipt['sha256'] != part['sha256']:
                        raise ValueError('event receipt fingerprint differs')
                    frame = pd.read_parquet(file)
                    validate_part(frame, kind, receipt, expected)
                    actual_ticker_rows.update(frame.groupby('ticker').size().to_dict())
                    total += len(frame)
                    fields.update({c: int(frame[c].notna().sum()) for c in frame})
                    for year, group in frame.groupby(frame.event_date.str[:4]):
                        years[year] += len(group)
                        year_tickers[year].update(group.ticker)
                    hashes.append(dict(file=file.name, sha256=sha(file), rows=len(frame),
                                       receipt_sha256=sha(meta), first=frame.event_date.min(), last=frame.event_date.max()))
                    file.unlink()
                expected_ticker_rows = {a['ticker']: a['rows'] for a in own['attempts'] if a.get('rows', 0) > 0}
                if dict(actual_ticker_rows) != expected_ticker_rows:
                    raise ValueError('all-parts event per-ticker row ledger differs')
                shards.append(dict(release=tag, status_sha256=sha(directory / 'EVENT_SOURCE_STATUS.json'),
                                   requested=len(expected), rows=own['source_rows'], parts=hashes))
                print('EVENT_AUDIT_SHARD', kind, shard, len(expected), own['source_rows'], flush=True)
            report['sources'][kind] = dict(attempt_status_counts=dict(statuses), source_rows=total,
                                          field_nonnull_rows=dict(fields), rows_by_year=dict(sorted(years.items())),
                                          tickers_by_year={y: len(v) for y, v in sorted(year_tickers.items())}, shards=shards)
        report['status'] = 'ALL_RELEASED_EVENT_BYTES_AND_ATTEMPTS_AUDITED_SOURCE_ONLY'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        write_json(root / 'EVENT_SOURCE_AUDIT.json', report)
    tag = f"event-source-audit-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release', 'create', tag, '--draft', '--target', os.environ['GITHUB_SHA'], '--title', tag,
             '--notes', 'Audit of all released event rows/attempts. Historical completeness, PIT availability and world acceptance remain unproven.')
    publish_assets(tag, root / 'EVENT_SOURCE_AUDIT.json')
    gh_retry('release', 'edit', tag, '--draft=false')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    audit(Path(args.directory), json.loads(Path('ci/EVENT_SOURCE_AUDIT_REQUEST.json').read_text()))


if __name__ == '__main__':
    main()

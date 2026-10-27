"""Stitch immutable raw-price checkpoints with explicit owner-approved exclusions."""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path

from ci import native_price_base as base
from ci import native_price_blocks as blocks
from ci.release_assets import download_asset, gh_retry, publish_assets

REQUEST = Path('ci/ACCEPTED_PRICE_STITCH_REQUEST.json')


def membership(inputs, records, minimum_percent):
    expected = {r['ticker'] for r in inputs['records']}
    actual = [r['ticker'] for r in records]
    if len(actual) != len(set(actual)) or not set(actual) <= expected:
        raise ValueError('duplicate or foreign accepted ticker')
    if not 95 <= minimum_percent <= 100:
        raise ValueError('minimum accepted coverage must be 95 to 100 percent')
    missing = sorted(expected - set(actual))
    percent = 100 * len(actual) / len(expected)
    if percent < minimum_percent:
        raise ValueError(f'accepted coverage {percent:.6f}% below {minimum_percent}%')
    return missing, percent


def run(root, request):
    root.mkdir(parents=True, exist_ok=True)
    file = download_asset(request['inputs_tag'], 'BUILD_INPUTS.json', root)
    if blocks.sha(file) != request['inputs_sha256']:
        raise ValueError('frozen input manifest changed')
    inputs = json.loads(file.read_text()); inputs['inputs_tag'] = request['inputs_tag']
    records = []; parts = []; exclusions = []; shard_proofs = []
    original = base.download
    base.download = download_asset
    try:
        for shard in range(16):
            selected = {r['ticker'] for r in inputs['records'] if r['ordinal'] % 16 == shard}
            tag = request['source_prefix'] + f'-{shard:03d}'
            own_parts, own_records = base.recover_base_parts(tag, inputs, selected, root / str(shard))
            # Even an unfinished job's fully published parts are immutable and verified.
            records.extend(own_records); parts.extend(own_parts)
            missing = sorted(selected - {r['ticker'] for r in own_records})
            exclusions.extend(dict(ticker=t, compact_shard=shard, source_release=tag,
                reason='NO_COMPLETE_HASH_VERIFIED_COMPACT_CHECKPOINT_AT_STITCH') for t in missing)
            shard_proofs.append(dict(shard=shard, release=tag, accepted=len(own_records), excluded=len(missing)))
    finally:
        base.download = original
    excluded, percent = membership(inputs, records, request['minimum_coverage_percent'])
    if excluded != sorted(r['ticker'] for r in exclusions):
        raise ValueError('exclusion ledger does not match original universe')
    metrics = {}; dates = Counter()
    for part in parts:
        directory = root / 'verified' / part['release'] / part['part']
        coverage = download_asset(part['release'], part['part'] + '.coverage.csv', directory)
        stock_days = download_asset(part['release'], part['part'] + '.stock_days.csv', directory)
        if blocks.sha(coverage) != part['coverage_sha256'] or blocks.sha(stock_days) != part['stock_days_sha256']:
            raise ValueError('compact coverage/date weights changed')
        with coverage.open(newline='') as stream:
            for row in csv.DictReader(stream):
                for key in ('query_rows', 'non_null_rows', 'tickers_with_values'): row[key] = int(row[key])
                blocks.add_metrics(metrics, row['timeframe'], [row])
        with stock_days.open(newline='') as stream:
            for row in csv.DictReader(stream): dates[row['date']] += int(row['stock_days'])
    count = sum(r['query_rows'] for r in records)
    if sum(dates.values()) != count: raise ValueError('accepted stock-day denominator differs')
    rows = sorted(metrics.values(), key=lambda r: (r['timeframe'], r['column']))
    for row in rows:
        if row['query_rows'] != count or not 0 < row['non_null_rows'] <= count:
            raise ValueError('accepted OHLCV coverage inconsistent')
        row['non_null_pct'] = 100 * row['non_null_rows'] / count
    coverage = root / 'ACCEPTED_PRICE_COVERAGE.csv'
    with coverage.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    ledger = root / 'ACCEPTED_PRICE_EXCLUSIONS.json'
    blocks.write_json(ledger, exclusions)
    weights = root / 'ACCEPTED_PRICE_STOCK_DAYS.csv'
    with weights.open('w', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['date', 'stock_days']); writer.writerows(sorted(dates.items()))
    result = dict(status='ACCEPTED_PRICE_BASE_WITH_LOGGED_EXCLUSIONS_NOT_WORLD',
        inputs_tag=request['inputs_tag'], inputs_sha256=request['inputs_sha256'],
        recipe_fingerprint=inputs['recipe_fingerprint'], source_commit=os.environ['GITHUB_SHA'],
        original_universe=len(inputs['records']), accepted_tickers=len(records), excluded_tickers=len(exclusions),
        accepted_percent=percent, minimum_coverage_percent=request['minimum_coverage_percent'],
        query_rows=count, timeframes=list(base.TIMEFRAMES), parts=parts, records=records, shards=shard_proofs,
        coverage_sha256=blocks.sha(coverage), exclusions_sha256=blocks.sha(ledger), stock_days_sha256=blocks.sha(weights),
        authority=request['authority'], historical_tradeability_gate='NOT_PROVEN',
        price_basis='frozen reference units; nominal historical price not proven',
        world_gate='READY_FOR_OWNER_AUTHORIZED_BUILD_NOT_WORLD_ACCEPTANCE', scoring_gate='CLOSED')
    status = root / 'ACCEPTED_PRICE_STITCH.json'; blocks.write_json(status, result)
    tag = f"accepted-price-stitch-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release', 'create', tag, '--draft', '--title', tag, '--target', os.environ['GITHUB_SHA'],
        '--notes', 'Hash-verified raw prices with explicit exclusions under James 19:00 directive. Not full-world or PIT approval.')
    publish_assets(tag, status, ledger, coverage, weights)
    gh_retry('release', 'edit', tag, '--draft=false')
    print('ACCEPTED_PRICE_STITCH', tag, len(records), len(exclusions), percent, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', required=True)
    args = parser.parse_args(); run(Path(args.directory), json.loads(REQUEST.read_text()))

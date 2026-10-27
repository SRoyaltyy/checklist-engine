"""Reuse verified compact ETF bars; publish native contexts, never world approval."""
import argparse
import csv
import io
import json
import os
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ci import native_price_base as base
from ci.native_price_blocks import read_member, sha, write_json, measure_availability
from ci.release_assets import download_asset, gh_retry, publish_assets
from world_context_native import KEYS, combine_contexts, price_native
from world_timeframes import TIMEFRAMES, PRICE_COLS


def target_parts(inputs, symbols, root, prefix):
    """Inventory complete parts, including partial shards, without archive reads."""
    groups = defaultdict(set)
    records = {r['ticker']: r for r in inputs['records']}
    absent = sorted(set(symbols) - set(records))
    for symbol in symbols:
        if symbol in records:
            groups[int(records[symbol]['ordinal']) % 16].add(symbol)
    located = []
    original = base.download
    base.download = download_asset
    try:
        for shard, wanted in sorted(groups.items()):
            selected = {r['ticker'] for r in inputs['records'] if int(r['ordinal']) % 16 == shard}
            directory = root / str(shard)
            parts, _ = base.recover_base_parts(prefix + f'-{shard:03d}', inputs, selected, directory)
            found = set()
            for part in parts:
                targets = wanted & set(part['tickers'])
                if targets:
                    manifest = json.loads((directory / (part['part'] + '.json')).read_text())
                    located.append((part, manifest, sorted(targets)))
                    found.update(targets)
            absent.extend(sorted(wanted - found))
    finally:
        base.download = original
    return located, sorted(absent)


def validated_bars(raw, symbol, calendar):
    frame = pd.read_parquet(io.BytesIO(raw))
    if not {'ticker', 'date', *PRICE_COLS} <= set(frame):
        raise ValueError('ETF source schema differs: ' + symbol)
    if set(frame.ticker) != {symbol}:
        raise ValueError('ETF source ticker differs: ' + symbol)
    frame['date'] = pd.to_datetime(frame.date).astype('datetime64[ns]')
    if frame.empty or frame.date.duplicated().any() or not frame.date.is_monotonic_increasing:
        raise ValueError('ETF source dates differ: ' + symbol)
    if not pd.DatetimeIndex(frame.date).isin(calendar).all():
        raise ValueError('ETF source dates outside frozen calendar: ' + symbol)
    return frame


def contexts(bars, calendar):
    return {tf: combine_contexts([price_native(frame, calendar, tf, 'etf_' + symbol.lower())
                                for symbol, frame in sorted(bars.items())]) for tf in TIMEFRAMES}


def prefix_checks(full, bars, calendar, cuts=('2023-01-03', '2025-01-02')):
    checks = []
    for value in cuts:
        cut = pd.Timestamp(value)
        earlier = {symbol: frame[frame.date < cut] for symbol, frame in bars.items()}
        rebuilt = contexts(earlier, calendar[calendar <= cut])
        for tf in TIMEFRAMES:
            expected = full[tf][full[tf].available_from <= cut].reset_index(drop=True)
            pd.testing.assert_frame_equal(expected, rebuilt[tf], check_dtype=False, rtol=0, atol=0)
            checks.append(dict(cut=value, timeframe=tf, rows=len(expected),
                               columns=len(expected.columns) - len(KEYS), mismatches=0))
    return checks


def build(root, request):
    root.mkdir(parents=True, exist_ok=True)
    file = download_asset(request['inputs_tag'], 'BUILD_INPUTS.json', root)
    if sha(file) != request['inputs_sha256']:
        raise ValueError('ETF frozen input manifest differs')
    inputs = json.loads(file.read_text())
    inputs['inputs_tag'] = request['inputs_tag']
    file = download_asset(request['inputs_tag'], 'market_sessions.parquet', root)
    if sha(file) != inputs['calendar_sha256']:
        raise ValueError('ETF calendar differs')
    calendar = pd.DatetimeIndex(pd.read_parquet(file).date)
    symbols = request['symbols']
    if not symbols or len(set(symbols)) != len(symbols):
        raise ValueError('ETF request must contain unique symbols')
    parts, missing = target_parts(inputs, symbols, root / 'manifests', request['compact_prefix'])
    bars = {}
    receipts = []
    for part, manifest, names in parts:
        archive = download_asset(part['release'], part['part'] + '.tar', root / 'archives')
        if sha(archive) != part['archive_sha256']:
            raise ValueError('ETF compact archive differs')
        for symbol in names:
            member = symbol.encode().hex() + '.bars.parquet'
            raw = read_member(archive, manifest, member)
            bars[symbol] = validated_bars(raw, symbol, calendar)
            meta = next(m for m in manifest['members'] if m['name'] == member)
            receipts.append(dict(ticker=symbol, release=part['release'], archive=archive.name,
                                 archive_sha256=part['archive_sha256'], member=meta,
                                 first=str(bars[symbol].date.min())[:10],
                                 last=str(bars[symbol].date.max())[:10], rows=len(bars[symbol])))
        archive.unlink()
    if not bars:
        raise ValueError('No verified ETF bars; do not publish a request-only release')
    full = contexts(bars, calendar)
    checks = prefix_checks(full, bars, calendar)
    coverage = []
    files = []
    parts = []
    query = calendar[calendar >= pd.Timestamp('2020-01-01')]
    for tf, frame in full.items():
        file = root / ('etf_context_' + tf + '.parquet')
        frame.to_parquet(file, index=False, compression='zstd')
        files.append(file)
        selected = [c for c in frame if c not in KEYS]
        for row in measure_availability(frame[['available_from', *selected]], query):
            coverage.append(dict(row, timeframe=tf, denominator='shared_market_sessions_not_stock_days'))
        parts.append(dict(file=file.name, sha256=sha(file), native_rows=len(frame),
                          timeframe=tf, feature_columns=len(selected)))
    file = root / 'ETF_CONTEXT_COVERAGE.csv'
    with file.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(coverage[0]))
        writer.writeheader()
        writer.writerows(coverage)
    files.append(file)
    status = dict(status='ETF_NATIVE_SOURCE_CONTEXT_ONLY', source_commit=os.environ['GITHUB_SHA'],
                  request=request, requested_symbols=symbols, available_symbols=sorted(bars),
                  missing_symbols=missing, source_receipts=receipts, parts=parts,
                  calendar_sha256=inputs['calendar_sha256'], recipe_fingerprint=inputs['recipe_fingerprint'],
                  coverage_sha256=sha(file), prefix_checks=checks, timeframes=list(TIMEFRAMES),
                  price_basis='frozen reference units; not nominal PIT prices or market-cap eligibility',
                  macro_cboe_reference='shared-context-v1-40363757188-1; separate source, no ETF prices there',
                  source_complete=not missing, stock_day_attachment_gate='NOT_RUN',
                  full_indicator_grid_gate='NOT_RUN; OHLCV and native return/trend baselines only',
                  historical_tradeability_gate='NOT_RUN', full_world_gate='NOT_RUN', scoring_gate='CLOSED',
                  code_sha256={name: sha(name) for name in
                               ('ci/etf_context_source.py', 'world_context_native.py', 'world_timeframes.py')})
    file = root / 'ETF_CONTEXT_STATUS.json'
    write_json(file, status)
    tag = f"etf-native-context-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release', 'create', tag, '--draft', '--target', os.environ['GITHUB_SHA'], '--title', tag,
             '--notes', 'Verified ETF native baselines. Shared-session coverage only; stock joins, full indicator grid and world acceptance remain open.')
    publish_assets(tag, *files, file)
    gh_retry('release', 'edit', tag, '--draft=false')
    print('ETF_NATIVE_SOURCE_COMPLETE', tag, len(bars), 'MISSING', missing, flush=True)
    if missing:
        raise ValueError('Missing requested ETF checkpoints; partial source evidence published explicitly')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--request', default='ci/ETF_CONTEXT_SOURCE_REQUEST.json')
    args = parser.parse_args()
    build(Path(args.directory), json.loads(Path(args.request).read_text()))


if __name__ == '__main__':
    main()

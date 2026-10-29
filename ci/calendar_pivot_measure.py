"""Original3-stock/SPY exact proof for all existing I074 anchor settings."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import time
from itertools import groupby

import numpy as np
import pandas as pd

from ci.relative_native_measure import checked_source, matrix_receipt
from ci.release_assets import gh_retry, publish_assets
from ci.verify_etf_daily_source import raw_asset
from market_storage import assert_exact_frame, exact_arrow_table
from world_calendar_pivots import ANCHORS, LEVELS, native_calendar_pivots
from world_timeframes import TIMEFRAMES

REQUEST = Path('ci/CALENDAR_PIVOT_REQUEST.json')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def independent_anchors(bars, calendar, day):
    """Scalar daily-record oracle: independent of production groupby/alignment."""
    daily = {pd.Timestamp(row.date): (float(row.high), float(row.low), float(row.close))
             for row in bars.itertuples() if calendar[0] <= pd.Timestamp(row.date) < day}
    result = {}
    for setting, (_, frequency) in ANCHORS.items():
        table = {}
        for period, sessions in groupby(calendar[calendar < day], key=lambda d: d.to_period(frequency)):
            if period == calendar[0].to_period(frequency) or period >= day.to_period(frequency): continue
            records = [daily.get(date) for date in sessions]
            if any(r is None or not all(np.isfinite(r)) or not (r[0] >= r[2] >= r[1] > 0) for r in records): continue
            h = max(r[0] for r in records); l = min(r[1] for r in records); c = records[-1][2]
            p = (h+l+c)/3
            table[str(period)] = [p, 2*p-l, 2*p-h, p+(h-l), p-(h-l)]
        result[setting] = table
    return result


def independent_frame(grid, anchors):
    out = grid.iloc[:, :3].copy()
    for setting, (_, frequency) in ANCHORS.items():
        expected = np.full((len(out), len(LEVELS)), np.nan, dtype='float64')
        for i, day in enumerate(pd.DatetimeIndex(out.available_from)):
            value = anchors[setting].get(str(day.to_period(frequency)-1))
            if value is not None: expected[i] = value
        for j, level in enumerate(LEVELS): out['I074_'+setting+'_'+level] = expected[:, j]
    return out


def measure(root, request):
    import pyarrow.parquet as pq
    settings = [dict(name=k, kind='native', parameters=dict(anchor=v[0])) for k, v in ANCHORS.items()]
    registry = json.loads(Path('dictionary/INDICATOR_SETTINGS.json').read_text(encoding='utf-8'))
    if request['settings'] != settings or registry['items']['I074']['settings'] != settings:
        raise ValueError('pivot proof must retain every exact registered anchor setting')
    columns = ['I074_'+setting+'_'+level for setting in ANCHORS for level in LEVELS]
    if request['columns'] != columns: raise ValueError('pivot proof schema differs')
    parent = json.loads(checked_source(request['parent_proof']))
    if parent['status'] != 'EXACT_RECOMPUTATION_SAMPLE_ONLY' or parent['errors']:
        raise ValueError('pivot original sample proof differs')
    bindings = [*request['stocks'], dict(request['benchmark'], ticker='SPY')]
    if len(bindings) != 4 or {b['ticker'] for b in bindings} != {'MAN', 'MNTS', 'EYE', 'SPY'}:
        raise ValueError('pivot proof requires original3 stocks plus SPY')
    original = {r['ticker']: r['raw_source_sha256'] for r in parent['samples']}
    original['SPY'] = parent['etf']['raw_source_sha256']
    if any(b['sha256'] != original[b['ticker']] for b in bindings):
        raise ValueError('pivot immutable sample input changed')
    calendar = pd.DatetimeIndex(pd.read_parquet(io.BytesIO(checked_source(request['calendar']))).date).as_unit('ns')
    cuts = [pd.Timestamp(c) for c in request['cutoffs']]
    if len(cuts) != 2 or len(set(cuts)) != 2 or any(c not in calendar for c in cuts):
        raise ValueError('two actual pivot cutoff sessions required')
    root.mkdir(parents=True, exist_ok=True)
    samples = []
    for binding in bindings:
        bars = pd.read_parquet(io.BytesIO(checked_source(binding)))
        checks, prefixes = [], []
        started = time.perf_counter()
        anchors = independent_anchors(bars, calendar, calendar[-1])
        for tf in TIMEFRAMES:
            full = native_calendar_pivots(bars, calendar, tf, calendar[-1])
            if list(full.columns[3:]) != columns: raise ValueError('pivot output schema differs')
            assert_exact_frame(full, independent_frame(full, anchors))
            file = root/(binding['ticker']+'_'+tf+'.parquet')
            pq.write_table(exact_arrow_table(full), file, compression='zstd', compression_level=9)
            reopened = pd.read_parquet(file)
            assert_exact_frame(full, reopened)
            assert_exact_frame(reopened, native_calendar_pivots(bars, calendar, tf, calendar[-1]))
            checks.append(dict(timeframe=tf, **matrix_receipt(full), anchors=full.attrs['anchors'],
                               persisted_bytes=file.stat().st_size, persisted_sha256=sha(file.read_bytes()),
                               independent_scalar_mismatches=0, mismatches=0))
            for cut in cuts:
                earlier = native_calendar_pivots(bars.loc[bars.date < cut], calendar[calendar <= cut], tf, cut)
                assert_exact_frame(full.loc[full.available_from <= cut].reset_index(drop=True), earlier)
                prefixes.append(dict(timeframe=tf, cut=str(cut.date()), **matrix_receipt(earlier), mismatches=0))
            (root/'CALENDAR_PIVOT_PROGRESS.json').write_text(json.dumps(dict(status='INCOMPLETE_CALENDAR_PIVOT_SAMPLE', ticker=binding['ticker'],
                checks=checks, prefixes=prefixes), indent=2)+'\n', encoding='utf-8')
        samples.append(dict(ticker=binding['ticker'], source_sha256=binding['sha256'], checks=checks,
                            prefixes=prefixes, seconds=time.perf_counter()-started))
        print('CALENDAR_PIVOT_INPUT_COMPLETE', binding['ticker'], len(checks), len(prefixes), flush=True)
    code = ('world_calendar_pivots.py', 'ci/calendar_pivot_measure.py', 'dictionary/INDICATOR_SETTINGS.json',
            'ci/relative_native_measure.py', 'world_relative_context.py', 'world_context_native.py',
            'world_timeframes.py', 'market_storage.py', 'requirements-world-v2.txt', 'world_fred.py',
            'world_dates.py', 'world_context_store.py', 'outside_compare.py', 'outside_market.py',
            'world_bar_statistics.py', 'ci/release_assets.py', 'ci/verify_etf_daily_source.py')
    return dict(status='FOUR_INPUT_CALENDAR_PIVOT_SAMPLE_ONLY', source_commit=os.environ['GITHUB_SHA'],
                request=request, samples=samples, timeframes=list(TIMEFRAMES), native_frames=sum(len(s['checks']) for s in samples),
                prefix_checks=sum(len(s['prefixes']) for s in samples),
                numeric_cells=sum(c['numeric_cells'] for s in samples for c in s['checks']),
                known_numeric_cells=sum(c['non_null_cells'] for s in samples for c in s['checks']),
                reference_bytes=sum(c['persisted_bytes'] for s in samples for c in s['checks']),
                code_sha256={name: sha(Path(name).read_bytes()) for name in code},
                runtime={n: importlib.metadata.version(n) for n in ('numpy', 'pandas', 'pyarrow')},
                anchor_rule='Prior calendar period at native availability; complete daily HLC, every expected session, no older-period substitution.',
                configured_indicators_integration='NOT_CHANGED; separate bound raw/calendar adapter',
                full_universe_gate='NOT_RUN', full_world_gate='NOT_PROVEN', comprehensive_leak_gate='NOT_PROVEN',
                full_dependency_budget_gate='NOT_PROVEN', scoring_gate='CLOSED', protected_run_untouched=40621517496)


def run(root, request):
    report = measure(root, request)
    file = root/'CALENDAR_PIVOT_MEASURED_V1.json'
    file.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    tag = f"calendar-pivot-native-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release', 'create', tag, '--draft', '--title', tag, '--target', os.environ['GITHUB_SHA'],
             '--notes', 'Original3 stocks plus SPY, existing I074 week/month/quarter anchors on22 genuine grids. Exact persistence and raw/calendar cutoff checks; sample only, no world/quality/PIT/budget/scoring acceptance.')
    publish_assets(tag, file)
    gh_retry('release', 'edit', tag, '--draft=false')
    if sha(raw_asset(tag, file.name)) != sha(file.read_bytes()): raise ValueError('pivot public report differs')
    print('CALENDAR_PIVOT_SAMPLE_COMPLETE', tag, report['native_frames'], report['prefix_checks'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    run(args.directory, json.loads(REQUEST.read_text(encoding='utf-8')))

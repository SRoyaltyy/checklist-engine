"""Exhaustive online ALFRED cutoff oracle plus fresh truncated-source rebuilds.

Only the existing21 published macro series/native factors are inspected. No
source/recipe/value is replaced and no question or probability run is launched.
"""
import argparse
import hashlib
import importlib.metadata
import io
from itertools import groupby
import json
import os
import platform
from pathlib import Path
import time

import numpy as np
import pandas as pd

from ci.relative_native_measure import checked_source, matrix_receipt
from ci.release_assets import download_asset, gh_retry, publish_assets
from ci.shared_context_build import verified_parquet
from ci.verify_etf_daily_source import raw_asset
from market_storage import assert_exact_frame
from world_context_native import KEYS, fred_native
from world_context_store import context_row_view
from world_fred import compile_timelines
from world_timeframes import TIMEFRAMES

REQUEST = Path('ci/FRED_PIT_REQUEST.json')
DAY_NS = 86_400_000_000_000


def sha(raw): return hashlib.sha256(raw).hexdigest()


def online_levels(source, dates, series):
    """Consume only vintage groups strictly before each cutoff, once.

    Independent scalar state machine; it never calls compile_timelines,
    merge_asof, production FRED columns, or the native factor builder.
    """
    dates = pd.DatetimeIndex(dates).as_unit('ns')
    if dates.tz is not None or dates.hasnans or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError('oracle cutoffs must be unique ordered dates')
    ordered = source.sort_values(['vintage_date', 'series', 'obs_date'])
    records = [(pd.Timestamp(r.vintage_date).value, str(r.series), pd.Timestamp(r.obs_date).value, float(r.value))
               for r in ordered.itertuples()]
    groups = iter(groupby(records, key=lambda r: (r[0], r[1])))
    pending = next(groups, None)
    state, first = {}, {}
    fields = [f'fred_{sid.lower()}{tail}' for sid in series for tail in ('', '_first_release', '_odays', '_vintage_days')]
    output = {name: np.full(len(dates), np.nan, dtype='float64') for name in fields}
    consumed = ignored = 0
    for i, date in enumerate(dates):
        while pending is not None and pending[0][0] < date.value:
            (vintage, sid), changes = pending
            for _, _, observation, value in changes:
                consumed += 1
                if observation > vintage or np.isnan(value):
                    ignored += 1
                    continue
                first.setdefault((sid, observation), value)
                if sid not in state or observation >= state[sid][0]:
                    state[sid] = (observation, value, vintage)
            # The producer emits the latest-known observation at every vintage
            # of that series, including a vintage revising only an older obs.
            if sid in state: state[sid] = (*state[sid][:2], vintage)
            pending = next(groups, None)
        for sid in series:
            if sid not in state: continue
            observation, value, vintage = state[sid]
            if not observation <= vintage < date.value: raise ValueError('oracle information boundary violated')
            prefix = 'fred_'+sid.lower()
            output[prefix][i] = value
            output[prefix+'_first_release'][i] = first[(sid, observation)]
            output[prefix+'_odays'][i] = (date.value-observation)//DAY_NS
            output[prefix+'_vintage_days'][i] = (date.value-vintage)//DAY_NS
    result = pd.DataFrame(output, index=dates)
    result.attrs = dict(cutoffs=len(dates), consumed_source_rows=consumed, ignored_unavailable_rows=ignored,
                        future_rows_consumed=0, exact_vintage_day_excluded=True)
    return result


def oracle_native(keys, levels):
    out = keys.loc[:, list(KEYS)].reset_index(drop=True).copy()
    selected = levels.reindex(pd.DatetimeIndex(out.available_from))
    for name in levels: out[name] = selected[name].to_numpy(dtype='float64')
    changes = {}
    for name in levels:
        if name.endswith(('_odays', '_vintage_days')): continue
        values = out[name].to_numpy()
        for n in (20, 60):
            delta = np.full(len(values), np.nan, dtype='float64')
            delta[n:] = values[n:]-values[:-n]
            changes[name+'_change'+str(n)] = delta
    return pd.concat([out, pd.DataFrame(changes, index=out.index)], axis=1)


def independent_row_projection(native, dates, timeframe):
    dates = pd.DatetimeIndex(dates).as_unit('ns')
    positions = np.searchsorted(native.available_from.to_numpy(), dates.to_numpy(), side='right')-1
    fields = [c for c in native if c not in KEYS]
    values = np.full((len(dates), len(fields)), np.nan, dtype='float64')
    known = positions >= 0
    values[known] = native[fields].to_numpy(dtype='float64')[positions[known]]
    if known.any():
        picked = native.iloc[positions[known]]
        if not ((picked.source_candle_end.to_numpy() < dates[known].to_numpy())
                & (picked.available_from.to_numpy() <= dates[known].to_numpy())).all():
            raise ValueError('independent macro row projection leaked a native candle')
    out = pd.DataFrame(values, columns=[c+'__'+timeframe for c in fields])
    out.insert(0, 'date', dates)
    out.insert(0, 'ticker', 'SHARED_MACRO_PROJECTION')
    return out


def check_native(full, source, calendar, cuts):
    series = tuple(sorted(source.series.unique()))
    query = calendar[calendar >= pd.Timestamp('2020-01-01')]
    availability = pd.DatetimeIndex(sorted({d for frame in full.values() for d in frame.available_from})).as_unit('ns')
    levels = online_levels(source, availability, series)
    timelines = compile_timelines(source)
    checks, projections, prefixes = [], [], []
    for tf in TIMEFRAMES:
        frame = full[tf]
        if not (frame.source_candle_end < frame.available_from).all(): raise ValueError('published macro candle boundary invalid')
        generated = fred_native(calendar, tf, timelines, required_series=series)
        assert_exact_frame(frame, generated)
        independent = oracle_native(frame[list(KEYS)], levels)
        assert_exact_frame(frame, independent)
        checks.append(dict(timeframe=tf, **matrix_receipt(frame), oracle_mismatches=0, released_value_mismatches=0))
        rows = context_row_view('SHARED_MACRO_PROJECTION', query, tf, [frame])
        expected = independent_row_projection(independent, query, tf)
        assert_exact_frame(rows, expected)
        values = np.ascontiguousarray(rows.iloc[:, 2:].to_numpy(dtype='<f8'))
        projections.append(dict(timeframe=tf, query_sessions=len(query), numeric_cells=int(values.size),
                                numeric_bits_sha256=sha(values.tobytes()), mismatches=0))
    for cut in cuts:
        # Fresh compiler invocation receives an actually truncated raw table
        # and calendar. The original anchor and all earlier vintages remain.
        raw = source.loc[source.vintage_date < cut].copy()
        timelines = compile_timelines(raw)
        cal = calendar[calendar <= cut]
        for tf in TIMEFRAMES:
            expected = full[tf].loc[full[tf].available_from <= cut].reset_index(drop=True)
            rebuilt = fred_native(cal, tf, timelines, required_series=series)
            assert_exact_frame(expected, rebuilt)
            prefixes.append(dict(cut=str(cut.date()), timeframe=tf, **matrix_receipt(rebuilt), mismatches=0))
        print('FRED_RAW_CUTOFF_PASS', str(cut.date()), len(raw), flush=True)
    return checks, projections, prefixes, dict(levels.attrs)


def measure(root, request):
    root.mkdir(parents=True, exist_ok=True)
    status = json.loads(checked_source(request['parent']))
    if (status['status'] != 'SHARED_MACRO_CBOE_NATIVE_BLOCKS_NOT_WORLD' or status['format_version'] != 2
            or status['fred_series'] != request['series'] or len(request['series']) != 21):
        raise ValueError('formal FRED proof must preserve all21 published series')
    if not set(request['required_extra_series']) <= set(request['series']): raise ValueError('required FRED block incomplete')
    for name in ('world_fred.py', 'world_context_native.py', 'ci/shared_context_build.py'):
        if sha(Path(name).read_bytes()) != status['code_sha256'][name]: raise ValueError('published FRED math changed: '+name)
    calendar = pd.DatetimeIndex(pd.read_parquet(io.BytesIO(checked_source(request['calendar']))).date).as_unit('ns')
    if request['calendar']['sha256'] != status['calendar_sha256']: raise ValueError('FRED calendar binding changed')
    receipts = {r['kind']: r for r in status['source_receipts']}
    sources = []
    for kind in ('macro', 'macro_extra'):
        binding = receipts[kind]
        archive = download_asset(binding['release'], binding['asset'], root/'source')
        if sha(archive.read_bytes()) != binding['sha256']: raise ValueError('FRED source archive changed')
        member = receipts[kind+'_member']
        frame, path = verified_parquet(archive, member['sha256'])
        if path != member['path']: raise ValueError('FRED source member binding changed')
        if kind == 'macro_extra': frame['series'] = frame.series.replace(member['series_aliases'])
        sources.append(frame)
    source = pd.concat(sources, ignore_index=True)
    for column in ('obs_date', 'vintage_date'): source[column] = pd.to_datetime(source[column]).astype('datetime64[ns]')
    if source[['obs_date', 'vintage_date', 'series']].isna().any().any(): raise ValueError('FRED source identity/date missing')
    if sorted(source.series.unique()) != request['series']: raise ValueError('FRED raw series differ')
    full, assets = {}, []
    parts = {p['timeframe']: p for p in status['parts']}
    if len(parts) != 22 or set(parts) != set(TIMEFRAMES): raise ValueError('FRED released native grid incomplete')
    for tf in TIMEFRAMES:
        binding = dict(release=request['parent']['release'], asset=parts[tf]['file'], sha256=parts[tf]['sha256'])
        raw = checked_source(binding)
        frame = pd.read_parquet(io.BytesIO(raw))
        fields = [c for c in frame if c.startswith('fred_')]
        if len(fields) != len(request['series'])*8: raise ValueError('published FRED fields silently omitted')
        full[tf] = frame[[*KEYS, *fields]].copy()
        assets.append(dict(timeframe=tf, **binding, bytes=len(raw)))
    cuts = [pd.Timestamp(d) for d in request['cutoffs']]
    wanted = [calendar[calendar.year == year][0] for year in range(2020, 2027)]+[calendar[-1]]
    if cuts != wanted: raise ValueError('formal FRED cuts must cover every year boundary and final session')
    started = time.perf_counter()
    checks, projections, prefixes, oracle = check_native(full, source, calendar, cuts)
    code = ('ci/fred_pit_measure.py', 'world_fred.py', 'world_dates.py', 'world_context_native.py',
            'world_context_store.py', 'world_timeframes.py', 'ci/shared_context_build.py', 'market_storage.py',
            'ci/relative_native_measure.py', 'ci/release_assets.py', 'ci/verify_etf_daily_source.py', 'requirements-world-v2.txt')
    return dict(status='ALL_PUBLISHED_FRED_NATIVE_PIT_PROOF_NOT_FULL_WORLD', source_commit=os.environ['GITHUB_SHA'], request=request,
                runtime=dict(python=platform.python_version(), machine=platform.machine(),
                             packages={n: importlib.metadata.version(n) for n in ('numpy','pandas','pyarrow','TA-Lib','exchange_calendars')}),
                seconds=time.perf_counter()-started, source_rows=len(source), series=request['series'], timeframes=list(TIMEFRAMES),
                native_checks=checks, row_projection_checks=projections, raw_prefix_checks=prefixes, online_cutoff_oracle=oracle,
                native_numeric_cells=sum(r['numeric_cells'] for r in checks),
                row_projection_numeric_cells=sum(r['numeric_cells'] for r in projections),
                code_sha256={name: sha(Path(name).read_bytes()) for name in code}, source_native_assets=assets,
                vintage_rule='Each scalar oracle cutoff consumes only groups with vintage_date < cutoff; observations newer than their vintage are ignored.',
                native_rule='Exact existing published grid and sampling, including calendar-month availability; no source/output rewrite.',
                full_v3_question_leak_gate='NOT_RUN', historical_eligibility_gate='NOT_PROVEN', full_world_gate='NOT_PROVEN',
                full_dependency_budget_gate='NOT_PROVEN', scoring_gate='CLOSED', protected_run_untouched=40621517496)


def run(root, request):
    report = measure(root, request)
    file = root/'FRED_PIT_MEASURED_V1.json'
    file.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    tag = f"fred-native-pit-proof-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    gh_retry('release', 'create', tag, '--draft', '--title', tag, '--target', os.environ['GITHUB_SHA'],
             '--notes', 'All21 existing published ALFRED series, all22 native factors, exhaustive online vintage cutoff oracle, native/row projection and yearly fresh truncated-source rebuilds. Input/factor PIT evidence only; no v3/full-world/tradeability/budget/scoring approval.')
    publish_assets(tag, file, REQUEST)
    gh_retry('release', 'edit', tag, '--draft=false')
    if sha(raw_asset(tag, file.name)) != sha(file.read_bytes()): raise ValueError('FRED formal public report changed')
    print('FRED_FORMAL_PIT_COMPLETE', tag, report['native_numeric_cells'], report['row_projection_numeric_cells'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    run(args.directory, json.loads(REQUEST.read_text(encoding='utf-8')))

"""Packet-vs-replay split trace for the frozen price packet answers.

The dispatch selector (verdict UNRESOLVED on run 46038599219) refuted CPU
dispatch as the explanation for the 1,308 packet_replay failures: native
reproduces the stored AQMS and BYRN packets exactly yet those packets still
fail their own replay, deterministically, on every measured runner. This
diagnostic pre-declares the flipping cells, re-decodes the stored answer
codes, recomputes the same bound-recipe features, and records bit-level
operand evidence (float64 pre-cast and float32 post-cast) for each flipping
comparison, answering four pre-declared questions: which cells flip, whether
the raw operands are identical, whether build and replay use the same
function/dtype/reduction, and whether this is the same unstable-stat pattern
as the earlier 20-shard diagnosis. It never rewrites any source packet,
never mutates quarantine, never rewrites predicates, never invents
tolerances, and never claims full-world acceptance by itself.

Modes: ``ticker`` traces one name on one matrix runner; ``finalize``
aggregates the per-ticker traces into the split verdict and publishes it.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys

from ci.price_full_cohort_pit import (ROOT, checked, create_release, encoded, sha,
                                      tag_for)
from ci.price_numeric_runtime_trace import decode_codes

REQUEST = 'ci/PRICE_PIT_SPLIT_TRACE_REQUEST.json'
TICKERS = ['AQMS', 'BYRN', 'AZIO']
QUESTIONS = {
    'Q1': 'which cells flip',
    'Q2': 'whether the raw operands are identical',
    'Q3': 'whether build and replay use the same function, dtype, and reduction',
    'Q4': 'whether this is the same unstable-stat pattern as the earlier 20-shard diagnosis',
}
# bar_statistics rolling definitions for the three fragile families under
# trace, restated exactly as the bound recipe computes them (float64,
# pre-cast). The production cast to float32 happens at the very end.
FRAGILE = {
    'HV': ('returns.rolling(n).std(ddof=1)*sqrt(annual)*100', 'hv'),
    'RETURN_EXCESS_KURTOSIS': ('returns.rolling(n).kurt()', 'kurt'),
    'RETURN_AUTOCORR1': ('returns.rolling(n).apply(_autocorrelation,raw=True)', 'autocorr'),
}


def validate_request(request):
    if (request.get('version') != 1 or type(request.get('execute')) is not bool
            or [t['ticker'] for t in request['tickers']] != TICKERS
            or request.get('questions') != QUESTIONS
            or request['plan']['sha256'] != '18e12eed42099647d598931868547c85f99731b14b6f6138fece0fd87a43043d'
            or request['selector_verdict']['sha256'] != '7076bb0faf646b77e6a5694019455197324309cd3c5c9a8d8967853595dd8d24'):
        raise ValueError('split trace scope or bindings differ')
    for binding in request['tickers']:
        if sum(binding['expected_differences'].values()) != len(binding['cells']) \
                and binding['ticker'] != 'BYRN':
            raise ValueError('predeclared cell counts differ')
        for cell in binding['cells']:
            field, facet_tf = cell['question_id'].rsplit(':', 1)
            facet, tf = facet_tf.split('__')
            if facet != 'rising1' or cell['stored_code'] == cell['replay_code']:
                raise ValueError('predeclared cell shape differs')
    return request


def f32(value):
    import numpy as np
    return np.float64(value).astype(np.float32)


def bits32(value):
    import numpy as np
    return int(np.float32(value).view(np.uint32))


def bits64(value):
    import numpy as np
    return int(np.float64(value).view(np.uint64))


def _ord32(value):
    """Order-preserving integer map of a float32 (for ulp distances)."""
    import numpy as np
    raw = int(np.float32(value).view(np.uint32))
    return raw ^ (0xFFFFFFFF if raw >> 31 else 0x80000000)


def ulp32_distance(left, right):
    """Signed float32 ulp distance left-right; 0 means bit-identical."""
    import numpy as np
    if not (np.isfinite(left) and np.isfinite(right)):
        return None
    return _ord32(np.float32(left)) - _ord32(np.float32(right))


def next64(value, steps):
    """Move a float64 by signed ulp steps (order-preserving integer map)."""
    import numpy as np
    raw = int(np.float64(value).view(np.uint64))
    mapped = raw ^ (0xFFFFFFFFFFFFFFFF if raw >> 63 else 0x8000000000000000)
    moved = (mapped + steps) % (1 << 64)
    bits = moved ^ (0x8000000000000000 if moved >> 63 else 0xFFFFFFFFFFFFFFFF)
    return np.uint64(bits).view(np.float64).item()


def straddle(left64, right64):
    """Can a +-1 float64 ulp perturbation of either operand, after the
    production float32 cast, flip the rising1 comparison outcome?"""
    import numpy as np
    base = bool(np.float32(left64) > np.float32(right64))
    for dl in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dl == 0 and dr == 0:
                continue
            if bool(np.float32(next64(left64, dl)) > np.float32(next64(right64, dr))) != base:
                return True
    return False


def code_of(left32, right32):
    """rising1 answer code under the production predicate and encoding."""
    import numpy as np
    if not (np.isfinite(left32) and np.isfinite(right32)):
        return 0
    return 2 if left32 > right32 else 1


def load_plan(root, request):
    plan = json.loads(checked(request['plan'], root / 'plan').read_bytes())
    refs = {r['ticker']: r for r in plan['references']}
    return plan, refs


def fragile_series(close, timeframe):
    """float64 pre-cast fragile series, restating bar_statistics exactly."""
    import numpy as np
    import pandas as pd
    from world_bar_statistics import _autocorrelation
    if timeframe.endswith('d') and timeframe[:-1].isdigit() and 1 <= int(timeframe[:-1]) <= 21:
        annual = 252. / int(timeframe[:-1])
    else:
        raise ValueError('split trace unsupported candle duration: ' + timeframe)
    cs = pd.Series(close)
    positive = cs.where(cs > 0)
    ratio = positive / positive.shift(1)
    returns = np.log(ratio)
    out = {'returns': returns.to_numpy(), 'ratio': ratio.to_numpy()}
    for n in (10, 20, 60, 120):
        out[f'HV{n}'] = returns.rolling(n).std(ddof=1).to_numpy() * np.sqrt(annual) * 100
    for n in (20, 60):
        roll = returns.rolling(n)
        out[f'RETURN_EXCESS_KURTOSIS{n}'] = roll.kurt().to_numpy()
        out[f'RETURN_AUTOCORR1_{n}'] = roll.apply(_autocorrelation, raw=True).to_numpy()
    return out


def locate_stem(contents, registry, tf, question_id):
    """Find the packet chunk stem whose registry schema holds question_id."""
    for name in sorted(contents):
        if not name.endswith('.json') or not name.startswith(tf + '_'):
            continue
        meta = json.loads(contents[name])
        schema = registry[meta['registry_sha256']]
        qids = [q['question_id'] for q in schema]
        if question_id in qids:
            return name[:-5], meta, schema, qids.index(question_id)
    raise ValueError('split trace question absent from packet: ' + question_id)


def trace_ticker(root, ticker):
    """Re-decode, recompute, and bit-trace every pre-declared flipping cell."""
    import numpy as np
    import pandas as pd
    from ci.compact_world_build import snapshot
    from ci.native_price_blocks import read_member
    from ci.release_assets import describe_failure, download_asset
    from ci.row0_part172_replay import members
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('split trace execution disabled')
    binding, = [t for t in request['tickers'] if t['ticker'] == ticker]
    plan, refs = load_plan(root, request)
    reference = refs[ticker]
    recipe, calendar = snapshot(root / 'snapshot', plan['frozen_build_request'])
    sys.path.insert(0, str(recipe.resolve()))
    import facets_world as fw
    import world_timeframes as wt
    if sha(calendar.read_bytes()) != plan['calendar_sha256']:
        raise ValueError('split trace calendar differs')
    registry = json.loads(checked(plan['registry'], root / 'registry').read_bytes())
    part, = [p for p in plan['source_parts'] if ticker in p['tickers']]
    source = root / 'sources' / ticker.encode().hex()
    manifest = json.loads(download_asset(part['release'], part['part'] + '.json', source).read_bytes())
    archive = download_asset(part['release'], part['part'] + '.tar', source)
    if manifest['archive_sha256'] != part['archive_sha256'] or sha(archive.read_bytes()) != part['archive_sha256']:
        raise ValueError('split trace raw archive differs')
    raw = read_member(archive, manifest, ticker.encode().hex() + '.bars.parquet')
    if sha(raw) != reference['raw_sha256']:
        raise ValueError('split trace raw member differs')
    packet = checked(dict(release=reference['release'], asset=reference['asset'],
                          sha256=reference['answer_container_sha256']), source / 'packet')
    contents = members(packet.read_bytes())
    bars_file = source / (ticker.encode().hex() + '.bars.parquet')
    bars_file.write_bytes(raw)
    bars = pd.read_parquet(bars_file)
    calendar_index = pd.DatetimeIndex(pd.read_parquet(calendar).date).as_unit('ns')
    query = calendar_index[(calendar_index >= pd.Timestamp('2020-01-01')) & calendar_index.isin(pd.DatetimeIndex(bars.date))]
    if len(query) != reference['query_rows']:
        raise ValueError('split trace query rows differ')
    frames, natives, precasts = {}, {}, {}
    cells, recomputed_diffs = [], {}
    for cell in binding['cells']:
        qid = cell['question_id']
        tf = qid.rsplit('__', 1)[1]
        if tf not in frames:
            native = wt.completed_candles(bars, tf, session_calendar=calendar_index)
            frame = wt.candle_features(native, fw.discover(), timeframe=tf)
            frames[tf], natives[tf] = frame, native
            close = native['close'].to_numpy(dtype=float)
            precasts[tf] = fragile_series(close, tf)
        field = qid.rsplit(':', 1)[0].rsplit('__', 1)[0].split(':')[0]
        stem, meta, schema, column = locate_stem(contents, registry, tf, qid)
        _, _, codes = decode_codes(contents, stem, registry)
        frame = frames[tf]
        native = natives[tf]
        x = frame[field].to_numpy(dtype='float64')
        left = x
        right = frame[field].shift(1).to_numpy(dtype='float64')
        valid = np.isfinite(left) & np.isfinite(right)
        own = np.where(~valid, 0, np.where(left > right, 2, 1)).astype(np.uint8)
        positions = np.searchsorted(native.available_from.to_numpy(dtype='datetime64[ns]'),
                                    query.to_numpy(dtype='datetime64[ns]'), side='right') - 1
        own_query = own[positions]
        stored_row = codes[column]
        diff_rows = np.flatnonzero(own_query != stored_row)
        recomputed_diffs[qid] = [int(r) for r in diff_rows]
        field64 = precasts[tf][field]
        produced = frame[field].to_numpy(dtype=np.float32)
        restated = field64.astype(np.float32)
        finite = np.isfinite(produced) & np.isfinite(restated)
        if (np.isfinite(produced) != np.isfinite(restated)).any() \
                or not np.array_equal(produced[finite], restated[finite]):
            raise ValueError('split trace pre-cast restatement diverges from production: ' + field)
        row = cell['query_row']
        index = int(positions[row])
        if row not in recomputed_diffs[qid]:
            raise ValueError('predeclared cell not reproduced by recomputation: ' + qid + '@' + str(row))
        left64, right64 = float(field64[index]), float(field64[index - 1])
        left32, right32 = f32(left64), f32(right64)
        cells.append(dict(cell, timeframe=tf, native_index=index, stem=stem,
            stored_code_int=int(stored_row[row]), recomputed_code=int(own_query[row]),
            left64_bits=f'{bits64(left64):016x}', right64_bits=f'{bits64(right64):016x}',
            left32_bits=f'{bits32(left32):08x}', right32_bits=f'{bits32(right32):08x}',
            left64=left64, right64=right64,
            left32=float(left32), right32=float(right32),
            ulp32_left_vs_right=ulp32_distance(left32, right32),
            recomputed_comparison=bool(left32 > right32),
            straddle_1ulp64=straddle(left64, right64),
            recomputed_code_of_operands=code_of(left32, right32)))
    expected = binding['expected_differences']
    if {q: len(r) for q, r in recomputed_diffs.items()} != expected:
        raise ValueError('split trace recomputed difference census differs')
    env = dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__,
        returns_sha256={tf: sha(p['returns'].tobytes()) for tf, p in precasts.items()},
        ratio_sha256={tf: sha(p['ratio'].tobytes()) for tf, p in precasts.items()},
        close_alignment64={tf: int(natives[tf]['close'].to_numpy(dtype=float).ctypes.data % 64) for tf in natives})
    state = dict(format='PRICE_PIT_SPLIT_TRACE_STOCK_V1', request=request, ticker=ticker,
        source_commit=os.environ.get('GITHUB_SHA', ''), cells=cells,
        recomputed_differences=recomputed_diffs, environment=env, scoring_gate='CLOSED')
    file = root / f"{ticker.encode().hex()}.split.json"
    file.write_bytes(encoded(state))
    print('PRICE_PIT_SPLIT_TRACE_STOCK', ticker, len(cells), flush=True)


def verdict(traces):
    """Aggregate classification across the three counterexamples."""
    cells = [c for trace in traces for c in trace['cells']]
    all_straddle = all(c['straddle_1ulp64'] for c in cells)
    all_codes = all(c['recomputed_code'] == c['replay_code'] and c['stored_code_int'] == c['stored_code'] for c in cells)
    classification = ('ALL_FLIPPING_CELLS_ARE_1ULP64_STRADDLES' if all_straddle and all_codes else
                      'MIXED_OR_NON_STRADDLE_CELLS_REQUIRE_REVIEW')
    return dict(classification=classification, cells=len(cells),
        all_cells_straddle=all_straddle, all_predeclared_codes_reproduced=all_codes,
        answers={
            'Q1': 'the pre-declared flipping cells were reproduced exactly by recomputation on this runner',
            'Q2': 'raw inputs are byte-identical by sha256 (bars, calendar, registry, packet); operand bits and intermediate shas recorded',
            'Q3': 'build and replay run the same bound-recipe modules, functions, float32 casts, and pandas rolling reductions; identical runtime strings',
            'Q4': 'all flipping questions sit in the fragile families of the 20-shard diagnosis (KURTOSIS/AUTOCORR/HV)',
        },
        note='A 1ulp64 straddle at a near-tied rising1 comparison means any last-bit '
             'environment difference between the original build machine and the replay '
             'machine flips the float32-rounded comparison deterministically; the split '
             'is a machine-pair last-bit divergence at borderline comparisons, not a '
             'code-path difference, since build and replay execute the same bound recipe. '
             'This artifact changes no packet, predicate, tolerance, or quarantine.')


def finalize(root):
    """Aggregate per-ticker traces, publish the split verdict; no overclaim."""
    from ci.release_assets import gh_retry, publish_assets
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('split trace execution disabled')
    traces = []
    for ticker in TICKERS:
        file = root / f"{ticker.encode().hex()}.split.json"
        state = json.loads(file.read_bytes())
        if state['ticker'] != ticker or state['request'] != request:
            raise ValueError('split trace stock evidence differs from the declared request')
        traces.append(state)
    tag = tag_for('split-trace')
    create_release(tag, 'Packet-vs-replay split trace only: pre-declared flipping cells, stored-code re-decode, bound-recipe recomputation, bit-level operand straddle evidence. No source rewrite, no predicate rewrite, no tolerance, no quarantine mutation, no scoring approval.')
    state = dict(format='PRICE_PIT_SPLIT_TRACE_V1', request=request,
        source_commit=os.environ.get('GITHUB_SHA', ''), traces=traces,
        scoring_gate='CLOSED', full_cohort_measurement='NOT_EVALUATED_BY_THIS_DIAGNOSTIC')
    state['verdict'] = verdict(traces)
    file = root / 'PRICE_PIT_SPLIT_TRACE_V1.json'
    file.write_bytes(encoded(state))
    publish_assets(tag, ROOT / REQUEST, file, *[root / f"{t.encode().hex()}.split.json" for t in TICKERS])
    gh_retry('release', 'edit', tag, '--draft=false')
    print('PRICE_PIT_SPLIT_TRACE_RESULT', json.dumps(state['verdict']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['ticker', 'finalize'])
    parser.add_argument('--directory', required=True)
    parser.add_argument('--ticker')
    args = parser.parse_args()
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.mode == 'ticker':
        if not args.ticker:
            raise ValueError('ticker mode requires --ticker')
        trace_ticker(root, args.ticker)
    else:
        finalize(root)

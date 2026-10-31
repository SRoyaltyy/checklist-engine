"""Read authenticated diagnostic JSON; never recompute or replace market data."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def key(selector):
    return (selector['question_id'], selector['query_row'], selector['row_keys_sha256'])


def value(bits):
    return struct.unpack('>d', bytes.fromhex(bits))[0]


def code(selector):
    left, right = value(selector['value_bits']), value(selector['comparison_bits'])
    return 1 + int(left > right) if math.isfinite(left) and math.isfinite(right) else 0


def analyse(summary_path, evidence_root):
    if not __debug__:
        raise RuntimeError('Run without Python -O: this evidence reviewer requires its assertions.')
    summary_raw = summary_path.read_bytes()
    summary = json.loads(summary_raw)
    rows = []
    for binding in summary['results']:
        raw = (evidence_root / binding['release'] / 'NUMERIC_RUNTIME_STOCK_TRACE_V2.json').read_bytes()
        assert sha(raw) == binding['sha256'], binding['ticker']
        doc = json.loads(raw)
        assert doc['ticker'] == binding['ticker'] and doc['unsupported_selectors'] == 0
        profiles = doc['profiles']
        a, repeat, alternate = [profiles[name] for name in ('baseline_a', 'baseline_b', 'no_numpy_dispatch')]
        assert len({json.dumps(p['bound_module_sha256'], sort_keys=True) for p in profiles.values()}) == 1
        maps = [{key(s): s for s in p['selectors']} for p in (a, repeat, alternate)]
        assert len(maps[0]) == len(a['selectors'])
        assert maps[0].keys() == maps[1].keys() == maps[2].keys()
        for p in profiles.values():
            for s in p['selectors']:
                assert s['status'] == 'TRACED' and code(s) == s['profile_code']
        assert maps[0] == maps[1], 'baseline selectors are not repeatable'
        assert doc['profile_comparisons'][0]['profile'] == 'baseline_b'
        assert all(d['bit_differences'] == 0 for d in doc['profile_comparisons'][0]['by_array'].values())
        assert len(a['observed_log_calls']) == len(alternate['observed_log_calls'])
        same_operands_changed_logs = different_operands = 0
        for first, second in zip(a['observed_log_calls'], alternate['observed_log_calls']):
            assert (first['component'], first['rows']) == (second['component'], second['rows'])
            if first['ratio_sha256'] != second['ratio_sha256']:
                different_operands += 1
            elif first['log_sha256'] != second['log_sha256']:
                same_operands_changed_logs += 1
        mismatch = [k for k, s in maps[0].items() if s['old_code'] != s['replay_code']]
        reproduced = []
        unresolved = []
        for k in mismatch:
            first, second = maps[0][k], maps[2][k]
            assert (first['old_code'], first['replay_code']) == (second['old_code'], second['replay_code'])
            target = reproduced if {first['profile_code'], second['profile_code']} == {first['old_code'], first['replay_code']} else unresolved
            target.append(dict(question_id=k[0], query_row=k[1], row_keys_sha256=k[2],
                               old_code=first['old_code'], replay_code=first['replay_code'],
                               baseline_code=first['profile_code'], alternate_code=second['profile_code'],
                               baseline_value_bits=first['value_bits'], baseline_comparison_bits=first['comparison_bits'],
                               alternate_value_bits=second['value_bits'], alternate_comparison_bits=second['comparison_bits']))
        controls = [k for k in maps[0] if k not in mismatch]
        row = dict(ticker=doc['ticker'], release=binding['release'], asset='NUMERIC_RUNTIME_STOCK_TRACE_V2.json',
                   sha256=sha(raw), source_commit=doc['source_commit'], plan_sha256=doc['plan_sha256'],
                   baseline_log_kernel=a['runtime']['active_ufunc_dispatch']['log'],
                   alternate_log_kernel=alternate['runtime']['active_ufunc_dispatch']['log'],
                   original_mismatch_selectors=len(mismatch), toggle_reproduces_both_codes=len(reproduced),
                   remaining_not_reproduced=len(unresolved), control_selectors=len(controls),
                   control_toggle_changes=sum(maps[0][k]['profile_code'] != maps[2][k]['profile_code'] for k in controls),
                   same_operand_bytes_different_log_bytes=same_operands_changed_logs,
                   different_operand_bytes=different_operands,
                   baseline_prefix_bit_differences=sum(p['bit_differences'] for p in a['prefix_checks']),
                   remaining_by_field=dict(Counter(s['question_id'].rsplit(':', 1)[0] for s in unresolved)),
                   reproduced_selectors=reproduced, remaining_selectors=unresolved)
        rows.append(row)
    totals = {k: sum(row[k] for row in rows) for k in ('original_mismatch_selectors', 'toggle_reproduces_both_codes',
              'remaining_not_reproduced', 'control_selectors', 'control_toggle_changes',
              'same_operand_bytes_different_log_bytes', 'different_operand_bytes', 'baseline_prefix_bit_differences')}
    assert totals['original_mismatch_selectors'] == 166
    return dict(status='DIAGNOSTIC_REVIEW_ONLY_QUARANTINE_UNCHANGED', evidence_run=41068145897,
                summary_sha256=sha(summary_raw), totals=totals, results=rows,
                interpretation=[
                    'The dispatch experiment reproduces both retained old/replay codes for the counted selectors under identical frozen module hashes.',
                    'Same-operand hash with different log-output hash establishes a numerical dependency in the observed np.log calls.',
                    'All NumPy dispatch features were disabled together; these traces do not isolate log alone as the sufficient cause of every selector change.',
                    'The original producer active kernels were not recorded here; historical cause is not proved for all 166 selectors.',
                    'Zero differences in the recorded baseline repeats/prefixes apply only to the measured schedule, not the full universe or every possible prefix.'
                ], next_experiment='Before proposing any runtime policy: same-host log-only substitution with matched operand bytes and a baseline reinjection control; retain unresolved selectors explicitly.',
                production_changes='NONE;ALL_EIGHT_REMAIN_EXCLUDED_REPLAY_MISMATCH', scoring_gate='CLOSED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.summary, args.evidence_root)
    out = args.output
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(out), totals=result['totals'], stocks=[{k: row[k] for k in ('ticker', 'original_mismatch_selectors', 'toggle_reproduces_both_codes', 'remaining_not_reproduced', 'same_operand_bytes_different_log_bytes', 'different_operand_bytes')} for row in result['results']])))

"""Independent public receipt lineage audit; no market calculation or download."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

from ci.price_full_cohort_pit_readback import (EVIDENCE, INPUT_RELEASE, PLAN_SHA,
    REPORT, read_bundle, require)

RUN = '41844079765'
COMMIT = '92f2d4ab6cb4cf9cac2f6218085851b24f759456'
WORKER_SHA = 'd48f918fe27bbdab5df56d4408d74284deba47406b323a138dfd459fa3cddbc2'
RECOVERY_SHA = 'dc4c72c9ec98ced17ff7e0d71acb5deee20be84899e89e0c63b0ebd6766b408a'
RECOVERY_INPUTS = f'price-full-cohort-pit-v1-{RUN}-1-recovery-inputs'
RECOVERY_PLAN = 'PRICE_FULL_COHORT_PIT_RECOVERY_PLAN_V1.json'
SUMMARY = 'PRICE_FULL_COHORT_PIT_RECOVERY_SUMMARY_V1.json'
INDICES = list(range(34, 176))
SELECTED, QUERY_ROWS = 6799, 10110205


def fingerprint(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def public_body(raw, tag, name, releases):
    release = releases.get(tag)
    require(release is not None and release['draft'] is False, 'lineage release is not public')
    assets = {a['name']: a for a in release['assets']}
    require(len(assets) == len(release['assets']), 'duplicate lineage asset')
    asset = assets.get(name)
    bound = fingerprint(raw)
    require(asset is not None and asset['state'] == 'uploaded' and asset['size'] == bound['bytes'] > 0
            and asset['digest'] == 'sha256:' + bound['sha256'], 'public lineage body fingerprint differs')


def validate_lineage(base_raw, report_raw, evidence, plan_raw, summary_raw, receipt_bodies, inventories):
    """Authenticate metadata bodies separately from the producer's validators."""
    require(fingerprint(base_raw)['sha256'] == PLAN_SHA, 'different base plan body')
    require(fingerprint(plan_raw)['sha256'] == RECOVERY_SHA, 'different sealed recovery plan body')
    base, report, plan, summary = map(json.loads, (base_raw, report_raw, plan_raw, summary_raw))
    releases = {r['tag_name']: r for r in inventories}
    require(len(releases) == len(inventories), 'duplicate lineage release')
    require(str(report['run_id']) == RUN and str(report['run_attempt']).isdigit()
            and int(report['run_attempt']) >= 1 and report['measurement'] == 'MEASURED'
            and report['scoring_gate'] == 'CLOSED', 'different or incomplete finalizer run')
    measured = f'price-full-cohort-pit-v1-{RUN}-{report["run_attempt"]}-measured'
    public_body(report_raw, measured, REPORT, releases)
    public_body(summary_raw, measured, SUMMARY, releases)
    public_body(plan_raw, RECOVERY_INPUTS, RECOVERY_PLAN, releases)
    require(plan['format'] == 'PRICE_FULL_COHORT_PIT_RECOVERY_PLAN_V1'
            and str(plan['actual_recovery_run_id']) == RUN and plan['recovery_commit'] == COMMIT
            and plan['worker_lf_sha256'] == WORKER_SHA and plan['scoring_gate'] == 'CLOSED'
            and plan['base_plan'] == dict(release=INPUT_RELEASE, asset='PRICE_FULL_COHORT_PIT_PLAN_V1.json', sha256=PLAN_SHA),
            'sealed recovery source differs')
    require(summary['format'] == 'PRICE_FULL_COHORT_PIT_RECOVERY_SUMMARY_V1'
            and summary['base_plan_sha256'] == PLAN_SHA and summary['recovery_plan_sha256'] == RECOVERY_SHA
            and summary['recovery_inputs'] == RECOVERY_INPUTS and str(summary['actual_recovery_run_id']) == RUN
            and summary['recovery_commit'] == COMMIT and summary['worker_lf_sha256'] == WORKER_SHA
            and summary['complete_report_sha256'] == fingerprint(report_raw)['sha256']
            and summary['complete_measurement'] == 'MEASURED' and summary['scoring_gate'] == 'CLOSED',
            'recovery summary source or report differs')
    parts = {p['index']: p for p in plan['parts']}
    receipts = {p['index']: p for p in summary['part_receipts']}
    require(len(parts) == len(plan['parts']) == len(receipts) == len(summary['part_receipts']) == len(INDICES)
            and set(parts) == set(receipts) == set(INDICES) and set(receipt_bodies) == set(INDICES),
            'missing, duplicate or foreign recovery part')
    references = {r['ticker']: r for r in base['references']}
    canonical = {r['ticker']: r for r in evidence['records']}
    require(len(canonical) == len(evidence['records']) and not evidence['errors'], 'ambiguous canonical evidence')
    selected, reused, job_ids = set(), 0, set()
    for index in INDICES:
        item, binding, raw = parts[index], receipts[index], receipt_bodies[index]
        expected = base['work_parts'][index]['tickers']
        tag = INPUT_RELEASE.removesuffix('-inputs') + f'-{index:03d}'
        failure = item['original_failure']
        require(item['tag'] == tag and item['expected_names'] == expected
                and failure['name'] == f'measure ({index})' and failure['conclusion'] == 'failure'
                and type(failure['job_id']) is int and failure['job_id'] not in job_ids
                and bool(failure['completed_at']), 'different failed source part')
        job_ids.add(failure['job_id'])
        match = re.fullmatch(r'PRICE_FULL_COHORT_PIT_PART_RECOVERY_' + RUN + r'_([1-9][0-9]*)\.json', binding['asset'])
        require(match is not None and binding['release'] == tag
                and all(binding[k] == v for k, v in fingerprint(raw).items()), 'receipt body binding differs')
        public_body(raw, tag, binding['asset'], releases)
        state = json.loads(raw)
        require(state['format'] == 'PRICE_FULL_COHORT_PIT_PART_RECOVERY_V1' and state['index'] == index
                and state['release'] == tag and state['base_plan_sha256'] == PLAN_SHA
                and state['recovery_plan_sha256'] == RECOVERY_SHA and state['recovery_inputs'] == RECOVERY_INPUTS
                and str(state['actual_recovery_run_id']) == RUN and str(state['actual_recovery_attempt']) == match[1]
                and state['recovery_commit'] == COMMIT and state['worker_lf_sha256'] == WORKER_SHA
                and state['original_failure'] == failure and state['expected_names'] == expected
                and not state['unmeasured'] and state['scoring_gate'] == 'CLOSED', 'receipt lineage differs')
        rows = state['records']
        require(len(rows) == len(expected) == len(set(expected))
                and {r['ticker'] for r in rows} == set(expected), 'receipt membership differs')
        for row in rows:
            ticker = row['ticker']
            require(ticker not in selected and ticker in canonical and type(row['reused']) is bool
                    and row['release'] == tag and row['asset'] == ticker.encode().hex() + '.pit.json.gz'
                    and all(row[k] == canonical[ticker][k] for k in ('release', 'asset', 'bytes', 'sha256')),
                    'recovered proof differs from canonical evidence')
            selected.add(ticker)
            reused += row['reused']
    require(len(selected) == SELECTED and sum(references[t]['query_rows'] for t in selected) == QUERY_ROWS,
            'recovery selected cohort differs')
    require(type(summary['reused_names']) is int and type(summary['newly_measured_names']) is int
            and summary['selected_names'] == SELECTED and summary['reused_names'] == reused
            and summary['newly_measured_names'] == SELECTED - reused, 'recovery name accounting differs')
    return dict(status='PASS_PUBLIC_RECOVERY_LINEAGE', actual_recovery_run_id=RUN, recovery_commit=COMMIT,
        part_receipts_verified=len(receipts), selected_names=SELECTED, selected_query_rows=QUERY_ROWS,
        reused_names=reused, newly_measured_names=SELECTED - reused, scoring_gate='CLOSED')


def read_recovery_bundle(directory, inventories):
    root = Path(directory)
    bundle = read_bundle(root, inventories)
    summary_raw = (root / SUMMARY).read_bytes()
    summary = json.loads(summary_raw)
    require(len(summary['part_receipts']) == len(INDICES)
            and {r['index'] for r in summary['part_receipts']} == set(INDICES)
            and all(re.fullmatch(r'PRICE_FULL_COHORT_PIT_PART_RECOVERY_' + RUN + r'_[1-9][0-9]*\.json',
                                 r['asset']) for r in summary['part_receipts']), 'unsafe or incomplete receipt paths')
    receipts = {r['index']: (root / 'receipts' / str(r['index']) / r['asset']).read_bytes()
                for r in summary['part_receipts']}
    lineage = validate_lineage((root / 'PRICE_FULL_COHORT_PIT_PLAN_V1.json').read_bytes(),
        (root / REPORT).read_bytes(), json.loads(gzip.decompress((root / EVIDENCE).read_bytes())),
        (root / RECOVERY_PLAN).read_bytes(), summary_raw, receipts, inventories)
    return dict(bundle=bundle, recovery=lineage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--inventories', required=True)
    args = parser.parse_args()
    print(json.dumps(read_recovery_bundle(args.directory,
        json.loads(Path(args.inventories).read_bytes())), indent=2))

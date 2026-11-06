"""Append-only recovery of missing PIT proofs; original worker/math unchanged."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from ci.price_full_cohort_pit import (ROOT, checked, create_release, encoded, finalize as full_finalize,
    sha, tag_for, validate_stock)
from ci.price_full_cohort_pit_readback import INPUT_RELEASE, PLAN_SHA
from ci import release_assets as io

REQUEST = 'ci/PRICE_PIT_MISSING_RECOVERY_REQUEST.json'
WORKER = '8003fb7906c3bf86d88612495664e597de1c65ae'
WORKER_SHA = 'd48f918fe27bbdab5df56d4408d74284deba47406b323a138dfd459fa3cddbc2'
PLAN_FILE = 'PRICE_FULL_COHORT_PIT_RECOVERY_PLAN_V1.json'
RESUME_REPORT = dict(release='price-full-cohort-pit-v1-41655284751-2-measured',
    asset='PRICE_FULL_COHORT_PIT_MEASURED_V1.json',
    sha256='d4cce0a3134227dfff8374debda3276fdce9b6fcb784a1bcabbd1291a33fb30b')


def validate_request(request):
    if (request.get('version') != 1 or type(request.get('execute')) is not bool
            or request['base_plan'] != dict(release=INPUT_RELEASE, asset='PRICE_FULL_COHORT_PIT_PLAN_V1.json', sha256=PLAN_SHA)
            or request['original_run_id'] != 41578885310 or request['worker_commit'] != WORKER
            or request['worker_lf_sha256'] != WORKER_SHA or request['failed_indices'] != list(range(34, 176))
            or request['expected_selected_names'] != 6799 or request['expected_selected_query_rows'] != 10110205
            or request['reserved_release_ids'] != {'34': 432338603}):
        raise ValueError('recovery scope differs from the observed missing-only cohort')
    if request.get('resume_report') is not None:
        if request['resume_report'] != RESUME_REPORT or request.get('allowed_new_names') != ['KGRN']:
            raise ValueError('resume scope differs from the authenticated one-name gap')
    elif 'allowed_new_names' in request:
        raise ValueError('new-measurement restriction requires its authenticated resume report')
    return request


def worker_unchanged():
    if sha((ROOT / 'ci/price_full_cohort_pit.py').read_bytes().replace(b'\r\n', b'\n')) != WORKER_SHA:
        raise ValueError('recovery must execute the unchanged original measurement worker')


def selected_failures(jobs, wanted):
    result = {}
    for job in jobs:
        match = re.fullmatch(r'measure \((\d+)\)', job['name'])
        if match and int(match[1]) in wanted:
            index = int(match[1])
            if index in result or job['status'] != 'completed' or job['conclusion'] != 'failure':
                raise ValueError('recovery cannot select duplicate, live or successful original parts')
            result[index] = dict(job_id=job['id'], name=job['name'], conclusion=job['conclusion'],
                                 completed_at=job['completed_at'])
    if set(result) != set(wanted):
        raise ValueError('original failed-part snapshot is incomplete')
    return result


def original_tag(index):
    if type(index) is not int or index not in range(34, 176):
        raise ValueError('recovery cannot write outside the failed original PIT namespace')
    return INPUT_RELEASE.removesuffix('-inputs') + f'-{index:03d}'


def receipt_name():
    return f"PRICE_FULL_COHORT_PIT_PART_RECOVERY_{os.environ['GITHUB_RUN_ID']}_{os.environ['GITHUB_RUN_ATTEMPT']}.json"


def latest_receipt(inventory, run_id):
    pattern = re.compile(r'PRICE_FULL_COHORT_PIT_PART_RECOVERY_' + re.escape(str(run_id)) + r'_(\d+)\.json')
    matches = [(int(match[1]), name) for name in inventory if (match := pattern.fullmatch(name))]
    if not matches:
        raise ValueError('recovery part has no actual-run receipt')
    return max(matches)[1]


def validate_resume_report(report, base, allowed):
    names = set(base['expected_names'])
    retained = names - set(allowed)
    expected_rows = sum(r['query_rows'] for r in base['references'] if r['ticker'] in retained)
    if (report['measurement'] != 'PARTIAL_NOT_MEASURED_FULL_COHORT'
            or report['plan_sha256'] != PLAN_SHA or report['inputs_release'] != INPUT_RELEASE
            or str(report['run_id']) != '41655284751' or str(report['run_attempt']) != '2'
            or report['expected_names'] != len(names) or report['measured_names'] != len(retained)
            or report['expected_query_rows'] != base['expected_query_rows']
            or report['measured_query_rows'] != expected_rows or report['unmeasured_names'] != allowed
            or report['source_commit'] != base['source_commit'] or report['composition'] != base['composition']
            or report['frozen_recipe'] != base['frozen_build_request']['corrected_recipe_fingerprint']
            or report['scoring_gate'] != 'CLOSED'):
        raise ValueError('resume report changes the frozen measurement or exact missing set')


def ensure_recovery_release(item):
    """A sealed absence is a creation-time observation, never a resume command."""
    tag = original_tag(item['index'])
    if item['tag'] != tag:
        raise ValueError('recovery release namespace differs')
    hint = item['existing_release_id']
    if hint is not None:
        io._RELEASE_IDS[(os.environ['GITHUB_REPOSITORY'], tag)] = hint
    try:
        release = io.release_info(tag)
    except subprocess.CalledProcessError as exc:
        if not re.search(r'\bHTTP\s+404\b', str(exc.stderr or '')):
            raise
        if hint is not None:
            raise ValueError('sealed existing recovery release disappeared') from exc
        io.gh_retry('release', 'create', tag, '--draft', '--target', WORKER, '--title', tag,
            '--notes', f"Append-only missing PIT recovery; original part {item['index']}, actual recovery run {os.environ['GITHUB_RUN_ID']}. Source commit/worker/math unchanged; not scoring approval.")
        release = io.release_info(tag)
    if release['tag_name'] != tag or release['target_commitish'] != WORKER:
        raise ValueError('recovery release identity differs')
    return release


def allow_new_measurement(request, ticker):
    allowed = request.get('allowed_new_names')
    if allowed is not None and ticker not in allowed:
        raise ValueError('retained proof disappeared; refusing to remeasure a completed name')


def publish_checkpoint(root, tag, state, paths, reused):
    # Reused proof bytes are already durable. The final part receipt records
    # their new validation without publishing thousands of redundant checkpoints.
    if reused:
        if paths:
            raise ValueError('a reused proof cannot be republished')
        return
    checkpoint = root / f"recovery_{os.environ['GITHUB_RUN_ID']}_{os.environ['GITHUB_RUN_ATTEMPT']}_{len(state['records']) + len(state['unmeasured']):04d}.json"
    checkpoint.write_bytes(encoded(state))
    io.publish_assets(tag, *paths, checkpoint)


def prepare(root):
    worker_unchanged()
    request = validate_request(json.loads((ROOT / REQUEST).read_bytes()))
    if request['execute'] is not True:
        raise ValueError('missing-only recovery is disabled')
    repository = os.environ['GITHUB_REPOSITORY']
    if repository != 'SRoyaltyy/checklist-engine':
        raise ValueError('wrong recovery repository')
    base = json.loads(checked(request['base_plan'], root / 'base').read_bytes())
    if request.get('resume_report') is not None:
        report = json.loads(checked(request['resume_report'], root / 'resume-report').read_bytes())
        validate_resume_report(report, base, request['allowed_new_names'])
    run = json.loads(io.gh_retry('api', f'repos/{repository}/actions/runs/{request["original_run_id"]}'))
    if run['head_sha'] != WORKER or run['run_attempt'] != 1:
        raise ValueError('original run changed; audit its actual attempt before recovery')
    jobs, page = [], 1
    while True:
        batch = json.loads(io.gh_retry('api', f'repos/{repository}/actions/runs/{run["id"]}/jobs?per_page=100&page={page}'))['jobs']
        jobs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    failed = selected_failures(jobs, request['failed_indices'])
    refs = {r['ticker']: r for r in base['references']}
    selected = [t for i in failed for t in base['work_parts'][i]['tickers']]
    if (len(selected) != len(set(selected)) or len(selected) != request['expected_selected_names']
            or sum(refs[t]['query_rows'] for t in selected) != request['expected_selected_query_rows']):
        raise ValueError('missing-only recovery changes the retained source scope')
    for index, release_id in request['reserved_release_ids'].items():
        io._RELEASE_IDS[(repository, original_tag(int(index)))] = release_id
    parts = []
    for index in sorted(failed):
        tag = original_tag(index)
        try:
            release = io.release_info(tag)
            if release['tag_name'] != tag or release['target_commitish'] != WORKER:
                raise ValueError('existing recovery namespace differs')
            release_id = release['id']
        except Exception as exc:
            if not isinstance(exc, subprocess.CalledProcessError) or not re.search(r'\bHTTP\s+404\b', str(exc.stderr or '')):
                raise
            release_id = None
        parts.append(dict(index=index, tag=tag, expected_names=base['work_parts'][index]['tickers'],
                          existing_release_id=release_id, original_failure=failed[index]))
        print('PIT_RECOVERY_PREPARED_PART', index, release_id, flush=True)
    plan = dict(format='PRICE_FULL_COHORT_PIT_RECOVERY_PLAN_V1', request=request, parts=parts,
        actual_recovery_run_id=os.environ['GITHUB_RUN_ID'], recovery_commit=os.environ['GITHUB_SHA'],
        worker_lf_sha256=WORKER_SHA, base_plan=request['base_plan'], scoring_gate='CLOSED')
    file = root / PLAN_FILE
    file.write_bytes(encoded(plan))
    tag = tag_for('recovery-inputs')
    create_release(tag, 'Sealed missing-only PIT recovery plan. Original cohort/math/worker unchanged; actual recovery lineage explicit.')
    io.publish_assets(tag, file, ROOT / REQUEST)
    io.gh_retry('release', 'edit', tag, '--draft=false')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('inputs_release=' + tag + '\nplan_sha256=' + sha(file.read_bytes()) +
                     '\nmatrix=' + json.dumps([p['index'] for p in parts if p['index'] != 34]) + '\n')


def recovery_plan(inputs, pin, root):
    plan = json.loads(checked(dict(release=inputs, asset=PLAN_FILE, sha256=pin), root).read_bytes())
    validate_request(plan['request'])
    if plan['worker_lf_sha256'] != WORKER_SHA or plan['base_plan']['sha256'] != PLAN_SHA:
        raise ValueError('recovery source binding differs')
    return plan


def validate_state(state, expected):
    done = [r['ticker'] for r in state['records']]
    missing = [r['ticker'] for r in state['unmeasured']]
    if len(done + missing) != len(set(done + missing)) or set(done + missing) != set(expected):
        raise ValueError('recovery lost, duplicated or excluded a planned name')


def recover(root, inputs, pin, index):
    from ci.compact_world_build import snapshot, limited_process
    from ci.native_price_blocks import read_member
    worker_unchanged()
    recovery = recovery_plan(inputs, pin, root / 'recovery-plan')
    item, = [p for p in recovery['parts'] if p['index'] == index]
    base = json.loads(checked(recovery['base_plan'], root / 'base').read_bytes())
    part = base['work_parts'][index]
    if item['expected_names'] != part['tickers'] or item['tag'] != original_tag(index):
        raise ValueError('recovery source part membership differs')
    refs = {r['ticker']: r for r in base['references']}
    tag = item['tag']
    release = ensure_recovery_release(item)
    inventory = io.asset_index(tag)
    io._DOWNLOAD_INVENTORIES[(os.environ['GITHUB_REPOSITORY'], tag)] = inventory
    state = dict(format='PRICE_FULL_COHORT_PIT_PART_RECOVERY_V1', index=index, release=tag,
        base_plan_sha256=PLAN_SHA, recovery_plan_sha256=pin, recovery_inputs=inputs,
        actual_recovery_run_id=os.environ['GITHUB_RUN_ID'], actual_recovery_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
        recovery_commit=os.environ['GITHUB_SHA'], original_failure=item['original_failure'],
        worker_lf_sha256=WORKER_SHA, expected_names=part['tickers'], records=[], unmeasured=[], scoring_gate='CLOSED')
    recipe = calendar = registry = manifest = archive = None
    started = time.monotonic()
    for ticker in part['tickers']:
        reference = refs[ticker]
        name = ticker.encode().hex() + '.pit.json.gz'
        publish = []
        reused = False
        try:
            existing = inventory.get(name)
            if existing and existing['state'] == 'uploaded':
                file = io.download_asset(tag, name, root / 'existing')
                reused = True
            else:
                allow_new_measurement(recovery['request'], ticker)
                if existing and not (existing['state'] == 'starter' and existing['size'] == 0):
                    raise ValueError('existing immutable proof cannot be replaced')
                if time.monotonic() - started > 16800 - 1200:
                    raise TimeoutError('RECOVERY_SHARD_BUDGET_RESUME_ONLY_REMAINING_NAMES')
                if recipe is None:
                    candidate_recipe, candidate_calendar = snapshot(root / 'snapshot', base['frozen_build_request'])
                    if sha(candidate_calendar.read_bytes()) != base['calendar_sha256']:
                        raise ValueError('recovery calendar differs')
                    candidate_registry = checked(base['registry'], root / 'registry')
                    candidate_manifest = json.loads(io.download_asset(part['release'], part['part'] + '.json', root / 'raw').read_bytes())
                    candidate_archive = io.download_asset(part['release'], part['part'] + '.tar', root / 'raw')
                    if candidate_manifest['archive_sha256'] != part['archive_sha256'] or sha(candidate_archive.read_bytes()) != part['archive_sha256']:
                        raise ValueError('recovery raw archive differs')
                    recipe, calendar, registry, manifest, archive = (candidate_recipe, candidate_calendar,
                        candidate_registry, candidate_manifest, candidate_archive)
                raw = read_member(archive, manifest, ticker.encode().hex() + '.bars.parquet')
                if sha(raw) != reference['raw_sha256']:
                    raise ValueError('recovery raw member differs')
                own = root / 'stocks' / ticker.encode().hex()
                own.mkdir(parents=True, exist_ok=True)
                (own / 'bars.parquet').write_bytes(raw)
                shutil.copyfile(calendar, own / 'market_sessions.parquet')
                packet = checked(dict(release=reference['release'], asset=reference['asset'],
                    sha256=reference['answer_container_sha256']), own / 'source-packet')
                shutil.copyfile(packet, own / 'reference.packet')
                config = dict(ticker=ticker, bars_sha256=reference['raw_sha256'], calendar_sha256=base['calendar_sha256'],
                    packet_sha256=reference['answer_container_sha256'], expected_query_rows=reference['query_rows'],
                    registry_path=str(registry.resolve()), registry_sha256=base['registry']['sha256'],
                    price_fields=base['price_fields'], prefix_cuts=base['prefix_cuts'],
                    recipe_fingerprint=base['frozen_build_request']['corrected_recipe_fingerprint'],
                    input_manifest_sha256=base['frozen_build_request']['inputs_sha256'])
                (own / 'WORKER.json').write_bytes(encoded(config))
                outcome = limited_process([sys.executable, '-m', 'ci.price_full_cohort_pit', 'worker',
                    '--directory', str(own.resolve()), '--recipe', str(recipe.resolve())], own, 1200)
                if outcome['returncode']:
                    raise RuntimeError(str(outcome['reason']) + ':' + outcome['log_tail'])
                file = root / name
                shutil.copyfile(own / 'STOCK_PRICE_PIT_V1.json.gz', file)
                reused = False
                publish.append(file)
            with gzip.open(file, 'rt', encoding='utf-8') as stream:
                stock = json.load(stream)
            validate_stock(stock, base, reference)
            state['records'].append(dict(ticker=ticker, release=tag, asset=name, bytes=file.stat().st_size,
                sha256=sha(file.read_bytes()), reused=reused, **{k: stock[k] for k in
                    ('prefix_gate', 'alignment_gate', 'packet_replay_gate')}))
            print('PIT_MISSING_RECOVERY_STOCK', index, ticker, 'REUSED' if reused else 'MEASURED', stock['packet_replay_gate'], flush=True)
        except Exception as exc:
            state['unmeasured'].append(dict(ticker=ticker, reason=io.describe_failure(exc)[-4000:]))
            print('PIT_MISSING_RECOVERY_UNMEASURED', index, ticker, io.describe_failure(exc)[-4000:], flush=True)
            publish = []
            reused = False
        # Publication failures stop this part; uploaded stock bytes remain
        # durable and are validated/reused on any later missing-only recovery.
        publish_checkpoint(root, tag, state, publish, reused)
    validate_state(state, part['tickers'])
    file = root / receipt_name()
    file.write_bytes(encoded(state))
    io.publish_assets(tag, file)
    if release['draft']:
        io.gh_retry('release', 'edit', tag, '--draft=false')
    if state['unmeasured']:
        raise ValueError('recovery retains explicit unmeasured names; no exclusions')


def finalize(root, inputs, pin):
    worker_unchanged()
    recovery = recovery_plan(inputs, pin, root / 'recovery-plan')
    full_finalize(root, INPUT_RELEASE, PLAN_SHA)
    report_file = root / 'PRICE_FULL_COHORT_PIT_MEASURED_V1.json'
    report = json.loads(report_file.read_bytes())
    with gzip.open(root / 'PRICE_FULL_COHORT_PIT_EVIDENCE_V1.json.gz', 'rt', encoding='utf-8') as stream:
        full_records = {r['ticker']: r for r in json.load(stream)['records']}
    receipts, names, reused = [], set(), 0
    for item in recovery['parts']:
        inventory = io.asset_index(item['tag'])
        io._DOWNLOAD_INVENTORIES[(os.environ['GITHUB_REPOSITORY'], item['tag'])] = inventory
        name = latest_receipt(inventory, os.environ['GITHUB_RUN_ID'])
        file = io.download_asset(item['tag'], name, root / 'receipts' / str(item['index']))
        state = json.loads(file.read_bytes())
        validate_state(state, item['expected_names'])
        if (state['unmeasured'] or state['actual_recovery_run_id'] != os.environ['GITHUB_RUN_ID']
                or state['recovery_plan_sha256'] != pin or state['worker_lf_sha256'] != WORKER_SHA
                or state['original_failure'] != item['original_failure']):
            raise ValueError('recovery lineage is incomplete or differs')
        for row in state['records']:
            if row['ticker'] in names or any(full_records[row['ticker']][k] != row[k] for k in ('release', 'asset', 'sha256', 'bytes')):
                raise ValueError('recovery proof binding differs from the complete report')
            names.add(row['ticker'])
            reused += row['reused']
        receipts.append(dict(index=item['index'], release=item['tag'], asset=file.name, sha256=sha(file.read_bytes()), bytes=file.stat().st_size))
    if len(names) != 6799:
        raise ValueError('recovery summary lost a selected name')
    summary = dict(format='PRICE_FULL_COHORT_PIT_RECOVERY_SUMMARY_V1', base_plan_sha256=PLAN_SHA,
        recovery_inputs=inputs, recovery_plan_sha256=pin, actual_recovery_run_id=os.environ['GITHUB_RUN_ID'],
        recovery_commit=os.environ['GITHUB_SHA'], worker_lf_sha256=WORKER_SHA, selected_names=len(names),
        reused_names=reused, newly_measured_names=len(names) - reused, part_receipts=receipts,
        complete_report_sha256=sha(report_file.read_bytes()), complete_measurement=report['measurement'], scoring_gate='CLOSED')
    file = root / 'PRICE_FULL_COHORT_PIT_RECOVERY_SUMMARY_V1.json'
    file.write_bytes(encoded(summary))
    io.publish_assets(tag_for('measured'), file)
    print('PIT_MISSING_RECOVERY_COMPLETE', len(names), reused, report['measurement'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'recover', 'finalize'))
    parser.add_argument('--directory', required=True)
    parser.add_argument('--inputs-release')
    parser.add_argument('--plan-sha256')
    parser.add_argument('--index', type=int)
    args = parser.parse_args()
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.action == 'prepare':
        prepare(root)
    elif args.action == 'recover':
        recover(root, args.inputs_release, args.plan_sha256, args.index)
    else:
        finalize(root, args.inputs_release, args.plan_sha256)

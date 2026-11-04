"""Retire only the obsolete recovery controller; never touch data or its successor."""
import json
import os
from pathlib import Path
import subprocess
import time

from ci import release_assets as io

REPOSITORY = 'SRoyaltyy/checklist-engine'
OLD = 41655284751
NEW = 41844079765
OLD_SHA = '22ce4aaf1d039e2b7593f390e967ca2d54fa9384'
NEW_SHA = '92f2d4ab6cb4cf9cac2f6218085851b24f759456'
REQUEST = Path(__file__).with_name('PRICE_PIT_SUPERSEDE_REQUEST.json')


def validate(run, run_id, source, attempt):
    if (run['id'] != run_id or run['head_sha'] != source
            or run['run_attempt'] != attempt or run['event'] != 'push'
            or run['head_branch'] != 'codex/price-full-cohort-pit'
            or run['path'] != '.github/workflows/price_pit_missing_recovery.yml'
            or run['repository']['full_name'] != REPOSITORY):
        raise ValueError('controller identity differs; refusing cancellation')
    return run


def read(run_id):
    return json.loads(io.gh_retry('api', f'repos/{REPOSITORY}/actions/runs/{run_id}'))


def retire_old():
    if os.environ['GITHUB_REPOSITORY'] != REPOSITORY:
        raise ValueError('wrong repository')
    request = json.loads(REQUEST.read_bytes())
    if request != dict(version=1, execute=True, obsolete_run_id=OLD, corrected_run_id=NEW):
        raise ValueError('one-time supersession is disabled or differs')
    successor = validate(read(NEW), NEW, NEW_SHA, 1)
    if successor['status'] == 'completed' and successor['conclusion'] != 'success':
        raise ValueError('corrected successor failed; inspect before retiring anything')
    observations = []
    def observe():
        run = validate(read(OLD), OLD, OLD_SHA, 3)
        observations.append({key: run.get(key) for key in
                             ('id', 'head_sha', 'run_attempt', 'status', 'conclusion', 'updated_at')})
        return run
    def save():
        Path('PRICE_PIT_SUPERSEDE_READBACK_V1.json').write_text(json.dumps(dict(
            version=1, obsolete_run_id=OLD, corrected_run_id=NEW, observations=observations), indent=2)+'\n')
    try:
        if observe()['status'] == 'completed':
            return
        # Ordinary cancellation first. Force-cancel is bounded to the same exact
        # old controller if GitHub keeps its always() finalizer alive.
        for endpoint in ('cancel', 'force-cancel'):
            if observe()['status'] == 'completed':
                return  # revalidate identity immediately before each mutation
            try:
                io.gh_retry('api', f'repos/{REPOSITORY}/actions/runs/{OLD}/{endpoint}', '--method', 'POST')
            except subprocess.CalledProcessError as exc:
                if observe()['status'] == 'completed':
                    return
                raise exc
            for _ in range(6):
                time.sleep(10)
                if observe()['status'] == 'completed':
                    return
        raise RuntimeError('old controller did not reach a terminal state; inspect readback')
    finally:
        save()


if __name__ == '__main__':
    retire_old()

"""One-shot capture of a failed PIT namespace publication response.

No market work, existing asset upload, deletion, or whole-run restart. A
successful POST only reserves the otherwise failed original part034 namespace.
"""
import argparse
import json
import os
from pathlib import Path

from ci import release_assets as io

REQUEST = Path('ci/PRICE_PIT_PUBLICATION_PROBE_REQUEST.json')
TAG = 'price-full-cohort-pit-v1-41578885310-1-034'
WORKER = '8003fb7906c3bf86d88612495664e597de1c65ae'


def failure(exc):
    value = dict(kind=type(exc).__name__, description=io.describe_failure(exc)[-4000:])
    headers = getattr(exc, 'response_headers', {})
    value['response_headers'] = {k: headers[k] for k in
        ('x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset', 'x-ratelimit-resource', 'retry-after') if k in headers}
    return value


def run(root):
    request = json.loads(REQUEST.read_bytes())
    if request['execute'] is not True:
        print('PUBLICATION_PROBE_DISABLED', flush=True)
        return
    repository = os.environ['GITHUB_REPOSITORY']
    if (repository != 'SRoyaltyy/checklist-engine' or request['target_tag'] != TAG
            or request['target_commit'] != WORKER or request['failed_job_id'] != 125730370756):
        raise ValueError('wrong repository or bounded publication probe scope')
    report = dict(format='PRICE_PIT_PUBLICATION_PROBE_V1', request=request,
        diagnostic_run_id=os.environ['GITHUB_RUN_ID'], source_commit=os.environ['GITHUB_SHA'],
        scope='ONE_PUBLICATION_REQUEST_NO_MARKET_COMPUTE_OR_RESTART', scoring_gate='CLOSED')
    try:
        core = json.loads(io._run('api', 'rate_limit'))['resources']['core']
        report['core_before'] = {k: core[k] for k in ('limit', 'remaining', 'reset')}
    except Exception as exc:
        report['core_read_error'] = failure(exc)
    try:
        # Check recent releases before the single request. Never replace or
        # upload into a pre-existing namespace in this diagnostic.
        releases = json.loads(io._run('api', f'repos/{repository}/releases?per_page=100&page=1'))
        matches = [r for r in releases if r['tag_name'] == TAG]
        if matches:
            report['publication_result'] = 'EXISTING_NO_MUTATION'
            report['existing'] = [dict(id=r['id'], draft=r['draft'], assets=len(r['assets'])) for r in matches]
        else:
            payload = root / 'creation-request.json'
            payload.write_text(json.dumps(dict(tag_name=TAG, name=TAG, target_commitish=WORKER,
                draft=True, body='Recovery reservation only; no completed measurement yet. Original part034 failed before measuring. '
                'Publication probe run ' + os.environ['GITHUB_RUN_ID'] + ' records the actual response; no source or protected artifact changed.')))
            try:
                value = json.loads(io._run('api', f'repos/{repository}/releases', '--method', 'POST', '--input', payload))
                if value['tag_name'] != TAG or not value['draft']:
                    raise ValueError('publication response identity differs')
                report['publication_result'] = 'CREATED_EMPTY_RECOVERY_RESERVATION'
                report['created_release_id'] = value['id']
            except Exception as exc:
                report['publication_result'] = 'REJECTED_RESPONSE_CAPTURED'
                report['publication_error'] = failure(exc)
    except Exception as exc:
        report['publication_result'] = 'PRECHECK_FAILED_NO_POST'
        report['precheck_error'] = failure(exc)
    file = root / 'PRICE_PIT_PUBLICATION_PROBE_V1.json'
    file.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    root = Path(args.directory).resolve()
    root.mkdir(parents=True, exist_ok=True)
    run(root)

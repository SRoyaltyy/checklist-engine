#!/usr/bin/env python3
"""Checkpoint loop for Step A on a GitHub runner.

Watches the chunks dir; whenever scores_NNN.parquet appears (a finished piece), pushes
scores_NNN.parquet + errors_NNN.json to the results branch and uploads answers_NNN.npz as a
release asset (idempotent: skips pieces already on the remote). Stops the engine when the
deadline approaches so the job exits cleanly inside its cap.

Usage:
  python3 ci/push_loop.py --engine-pid PID --chunks DIR --deadline-min 320        # loop mode
  python3 ci/push_loop.py --chunks DIR --once                                     # single sweep
"""
import argparse, glob, json, os, subprocess, sys, time, urllib.request

def api(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{os.environ['GH_REPO']}{path}",
                                 headers={'Authorization': f"token {os.environ['GITHUB_TOKEN']}",
                                          'Accept': 'application/vnd.github+json'})
    return json.load(urllib.request.urlopen(req))

def sh(*args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)

def remote_state():
    """pieces already pushed: {NNN: {'scores': bool, 'answers': bool}}"""
    state = {}
    sh('git', 'fetch', '-q', 'origin', os.environ.get('RESULTS_BRANCH', 'results/step-a-2020-22'))
    ref = f"origin/{os.environ.get('RESULTS_BRANCH', 'results/step-a-2020-22')}"
    out = sh('git', 'ls-tree', '--name-only', ref, 'step_a/').stdout
    for line in out.splitlines():
        b = os.path.basename(line)
        for pre, kind in (('scores_', 'scores'), ('errors_', 'errors')):
            if b.startswith(pre) and b.endswith('.parquet'):
                state.setdefault(b[len(pre):-len('.parquet')], {})[kind] = True
    rel = api(f"/releases/tags/{os.environ.get('RELEASE', 'data-2020-24-v1')}")
    for a in rel['assets']:
        if a['name'].startswith('answers_') and a['name'].endswith('.npz'):
            state.setdefault(a['name'][len('answers_'):-len('.npz')], {})['answers'] = True
    return state

def push_piece(nnn, ch):
    """commit scores+errors to results branch; upload answers npz. Idempotent per piece."""
    rb = os.environ.get('RESULTS_BRANCH', 'results/step-a-2020-22')
    clone = os.path.join(os.environ.get('RUNNER_TEMP', '/tmp'), 'results-clone')
    tok = os.environ['GITHUB_TOKEN']; repo = os.environ['GH_REPO']
    if not os.path.exists(clone):
        sh('git', 'clone', '-q', f'https://x-access-token:{tok}@github.com/{repo}.git', clone)
    sh('git', '-C', clone, 'fetch', '-q', 'origin', rb)
    sh('git', '-C', clone, 'checkout', '-q', '-B', 'results-push', f'origin/{rb}')
    import shutil
    for pre in ('scores', 'errors'):
        src = os.path.join(ch, f'{pre}_{nnn}.parquet' if pre == 'scores' else f'{pre}_{nnn}.json')
        if os.path.exists(src):
            os.makedirs(os.path.join(clone, 'step_a'), exist_ok=True)
            shutil.copy(src, os.path.join(clone, 'step_a'))
    sh('git', '-C', clone, 'add', '-f', 'step_a/')
    if sh('git', '-C', clone, 'status', '--porcelain', 'step_a/').stdout.strip():
        sh('git', '-C', clone, '-c', 'user.name=step-a-bot', '-c', 'user.email=step-a-bot@users.noreply.github.com',
           'commit', '-q', '-m', f'Step A piece {int(nnn) + 1}/34 checkpoint')
        for attempt in range(6):   # matrix jobs push concurrently; rebase over each other and retry
            r = sh('git', '-C', clone, 'push', '-q', 'origin', 'results-push:' + rb, check=False)
            if r.returncode == 0:
                break
            sh('git', '-C', clone, 'fetch', '-q', 'origin', rb, check=False)
            sh('git', '-C', clone, 'rebase', '-q', f'origin/{rb}', check=False)
            time.sleep(5 + attempt * 10)
        else:
            raise RuntimeError(f'push failed after retries: {r.stderr[-300:]}')
    ans = os.path.join(ch, f'answers_{nnn}.npz')
    if os.path.exists(ans):
        rel = api(f"/releases/tags/{os.environ.get('RELEASE', 'data-2020-24-v1')}")
        names = {a['name'] for a in rel['assets']}
        if os.path.basename(ans) not in names:
            up = rel['upload_url'].split('{')[0] + f'?name={os.path.basename(ans)}'
            req = urllib.request.Request(up, data=open(ans, 'rb').read(),
                                         headers={'Authorization': f'token {tok}',
                                                  'Content-Type': 'application/octet-stream',
                                                  'Content-Length': str(os.path.getsize(ans))})
            urllib.request.urlopen(req)
    print(f'checkpointed piece {int(nnn) + 1}', flush=True)

def sweep(ch, state):
    for f in sorted(glob.glob(os.path.join(ch, 'scores_*.parquet'))):
        nnn = os.path.basename(f)[len('scores_'):-len('.parquet')]
        have = state.get(nnn, {})
        if have.get('scores') and have.get('answers'):
            continue
        if not os.path.exists(os.path.join(ch, f'answers_{nnn}.npz')):
            continue   # answers save happens before scoring; scores present => answers should exist
        try:
            push_piece(nnn, ch)
            state.setdefault(nnn, {})['scores'] = state.setdefault(nnn, {})['answers'] = True
        except Exception as e:
            print('push failed for', nnn, repr(e)[:200], flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine-pid', type=int, default=None)
    ap.add_argument('--chunks', required=True)
    ap.add_argument('--deadline-min', type=float, default=320)
    ap.add_argument('--once', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    state = remote_state()
    while True:
        sweep(a.chunks, state)
        if a.once:
            return
        if a.engine_pid and sh('kill', '-0', str(a.engine_pid), check=False).returncode != 0:
            print('engine exited', flush=True)
            return
        if (time.time() - t0) / 60 > a.deadline_min:
            print('deadline reached, stopping engine for a clean resume', flush=True)
            sh('kill', '-TERM', str(a.engine_pid), check=False)
            time.sleep(15); sweep(a.chunks, state)
            return
        time.sleep(60)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Release asset helper for the exit-grid jobs.
  have <tag> <name>...     exit 0 if every named asset exists on the release, else 1
  get <tag> <dest>          download every asset of the release into dest
  getmatch <tag> <dest> <pat>...  download only assets whose name matches a glob pattern
  upload <tag> <file>...    upload each file as an asset if its name is not already taken (release created if missing)
  rm <tag> <name>...         delete named assets (for forced reruns)
Env note: FORCE_UPLOAD=1 makes upload replace same-named assets (delete+upload), for dictionary-fix reruns.
Env: GITHUB_TOKEN, GH_REPO."""
import json, os, sys, urllib.request

API = f"https://api.github.com/repos/{os.environ['GH_REPO']}"
TOK = os.environ['GITHUB_TOKEN']
H = {'Authorization': f'token {TOK}', 'Accept': 'application/vnd.github+json'}


def req(path, data=None, method=None, raw_headers=None):
    r = urllib.request.Request(API + path, data=data, method=method,
                               headers=raw_headers or H)
    return urllib.request.urlopen(r)


def release(tag):
    try:
        return json.load(req(f'/releases/tags/{tag}'))
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        body = json.dumps({'tag_name': tag, 'name': tag,
                           'body': 'Exit-grid 2020-22 intermediate + final outputs (see kimi/exit-grid).'}).encode()
        return json.load(req('/releases', data=body, method='POST',
                             raw_headers={**H, 'Content-Type': 'application/json'}))


def _download(a, dest):
    out = os.path.join(dest, a['name'])
    if os.path.exists(out) and os.path.getsize(out) == a['size']:
        print('cached', a['name'])
        return
    r = urllib.request.Request(a['url'], headers={'Authorization': f'token {TOK}',
                                                  'Accept': 'application/octet-stream'})
    with urllib.request.urlopen(r) as resp, open(out, 'wb') as f:
        while True:
            b = resp.read(1 << 20)
            if not b:
                break
            f.write(b)
    print('downloaded', a['name'], a['size'])


def main():
    cmd, tag = sys.argv[1], sys.argv[2]
    rel = release(tag)
    names = {a['name'] for a in rel['assets']}
    if cmd == 'have':
        missing = [n for n in sys.argv[3:] if n not in names]
        if missing:
            print('missing:', *missing)
            sys.exit(1)
        print('all present')
    elif cmd == 'get':
        dest = sys.argv[3]
        os.makedirs(dest, exist_ok=True)
        for a in rel['assets']:
            _download(a, dest)
    elif cmd == 'getmatch':
        import fnmatch
        dest = sys.argv[3]
        pats = sys.argv[4:]
        os.makedirs(dest, exist_ok=True)
        matched = False
        for a in rel['assets']:
            if any(fnmatch.fnmatch(a['name'], p) for p in pats):
                matched = True
                _download(a, dest)
        if not matched:
            print('getmatch: no assets matched', pats)
    elif cmd == 'upload':
        up_base = rel['upload_url'].split('{')[0]
        force = os.environ.get('FORCE_UPLOAD') == '1'
        ids = {a['name']: a['id'] for a in rel['assets']}
        for path in sys.argv[3:]:
            name = os.path.basename(path)
            if name in names and not force:
                print('exists', name)
                continue
            if name in names and force:
                req(f'/releases/assets/{ids[name]}', method='DELETE')
                print('replaced (deleted old)', name)
            data = open(path, 'rb').read()
            r = urllib.request.Request(up_base + f'?name={name}', data=data,
                                       headers={'Authorization': f'token {TOK}',
                                                'Content-Type': 'application/octet-stream',
                                                'Content-Length': str(len(data))})
            urllib.request.urlopen(r)
            print('uploaded', name, len(data))
    elif cmd == 'rm':
        ids = {a['name']: a['id'] for a in rel['assets']}
        for name in sys.argv[3:]:
            if name in ids:
                req(f'/releases/assets/{ids[name]}', method='DELETE')
                print('deleted', name)
            else:
                print('not found', name)
    else:
        sys.exit(f'unknown cmd {cmd}')


if __name__ == '__main__':
    main()

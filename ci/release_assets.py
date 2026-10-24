#!/usr/bin/env python3
"""Release asset helper for the exit-grid jobs.
  have <tag> <name>...     exit 0 if every named asset exists on the release, else 1
  get <tag> <dest>          download every asset of the release into dest
  upload <tag> <file>...    upload each file as an asset if its name is not already taken (release created if missing)
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
            out = os.path.join(dest, a['name'])
            if os.path.exists(out) and os.path.getsize(out) == a['size']:
                print('cached', a['name'])
                continue
            r = urllib.request.Request(a['url'], headers={'Authorization': f'token {TOK}',
                                                          'Accept': 'application/octet-stream'})
            with urllib.request.urlopen(r) as resp, open(out, 'wb') as f:
                while True:
                    b = resp.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            print('downloaded', a['name'], a['size'])
    elif cmd == 'upload':
        up_base = rel['upload_url'].split('{')[0]
        for path in sys.argv[3:]:
            name = os.path.basename(path)
            if name in names:
                print('exists', name)
                continue
            data = open(path, 'rb').read()
            r = urllib.request.Request(up_base + f'?name={name}', data=data,
                                       headers={'Authorization': f'token {TOK}',
                                                'Content-Type': 'application/octet-stream',
                                                'Content-Length': str(len(data))})
            urllib.request.urlopen(r)
            print('uploaded', name, len(data))
    else:
        sys.exit(f'unknown cmd {cmd}')


if __name__ == '__main__':
    main()

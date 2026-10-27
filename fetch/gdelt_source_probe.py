"""Measure actual numeric DOC API history access before a universe fetch."""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from ci.native_price_blocks import sha, write_json
from ci.release_assets import gh_retry, publish_assets

MODES = ('TimelineVolRaw', 'TimelineTone')


def parse_payload(payload, mode, start, end):
    if mode not in MODES:
        raise ValueError('only numeric timeline modes are authorized')
    timeline = payload.get('timeline')
    if not isinstance(timeline, list) or len(timeline) != 1:
        raise ValueError('expected one numeric timeline series')
    values = timeline[0].get('data')
    if not isinstance(values, list) or not values:
        raise ValueError('no numeric timeline rows; not a zero event count')
    frame = pd.DataFrame(values)
    if not {'date', 'value'} <= set(frame):
        raise ValueError('numeric timeline schema differs')
    dates = pd.to_datetime(frame.date, format='%Y%m%dT%H%M%SZ', utc=True, errors='raise')
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError('numeric timeline dates must be unique and ordered')
    first = pd.to_datetime(start, format='%Y%m%d%H%M%S', utc=True)
    last = pd.to_datetime(end, format='%Y%m%d%H%M%S', utc=True)
    if not ((dates >= first) & (dates <= last)).all():
        raise ValueError('provider returned dates outside requested history window')
    value = pd.to_numeric(frame.value, errors='raise').astype(float)
    if not np.isfinite(value).all():
        raise ValueError('numeric timeline contains nonfinite values')
    out = pd.DataFrame(dict(timestamp=dates, value=value))
    if mode == 'TimelineVolRaw':
        if 'norm' not in frame:
            raise ValueError('raw article counts require their source norm')
        norm = pd.to_numeric(frame.norm, errors='raise').astype(float)
        if not np.isfinite(norm).all() or (value < 0).any() or (norm < value).any():
            raise ValueError('raw article count/norm outside range')
        if (value % 1 != 0).any() or (norm % 1 != 0).any():
            raise ValueError('raw article counts must be integers; never truncate percentages')
        out['value'] = value.astype('int64')
        out['norm'] = norm.astype('int64')
    return out


def probe(root, request):
    root.mkdir(parents=True, exist_ok=True)
    report = dict(status='INCOMPLETE_NUMERIC_SOURCE_PROBE', request=request,
                  source_commit=os.environ['GITHUB_SHA'], attempts=[], parts=[],
                  history_2020_2026_gate='NOT_PROVEN', ticker_identity_gate='NOT_PROVEN; test query only',
                  point_in_time_gate='NOT_PROVEN; query time is not historical first observation',
                  full_universe_gate='NOT_RUN', world_gate='NOT_RUN', scoring_gate='CLOSED')
    files = []
    blocked = False
    for window in request['windows']:
        for mode in MODES:
            receipt = dict(window=window, mode=mode, observed_at=datetime.now(timezone.utc).isoformat())
            if blocked:
                receipt.update(status='NOT_ATTEMPTED_AFTER_ACCESS_OR_RATE_LIMIT')
                report['attempts'].append(receipt)
                continue
            params = dict(query=request['query'], mode=mode, format='json',
                          startdatetime=window['start'], enddatetime=window['end'], timelinesmooth=1)
            url = 'https://api.gdeltproject.org/api/v2/doc/doc?' + urllib.parse.urlencode(params)
            receipt['url'] = url
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'checklist-engine numeric-source-probe'})
                with urllib.request.urlopen(req, timeout=90) as response:
                    receipt['http_status'] = response.status
                    raw = response.read(4000001)
                if len(raw) > 4000000:
                    raise ValueError('numeric probe payload exceeds bound')
                receipt['response_sha256'] = hashlib.sha256(raw).hexdigest()
                try:
                    payload = json.loads(raw)
                except ValueError:
                    receipt['provider_message'] = raw.decode('utf-8', errors='replace')[:500]
                    raise ValueError('provider returned non-JSON response')
                frame = parse_payload(payload, mode, window['start'], window['end'])
                file = root / (window['name'] + '_' + mode + '.parquet')
                frame.to_parquet(file, index=False)
                files.append(file)
                receipt.update(status='NUMERIC_ROWS_RETURNED', file=file.name, sha256=sha(file), rows=len(frame),
                               first=frame.timestamp.min().isoformat(), last=frame.timestamp.max().isoformat(),
                               value_kind='distinct_article_count' if mode == 'TimelineVolRaw' else 'mean_tone_float')
                report['parts'].append(dict(file=file.name, sha256=sha(file), rows=len(frame)))
            except urllib.error.HTTPError as exc:
                receipt.update(status='SOURCE_ERROR', http_status=exc.code, error=str(exc))
                blocked = exc.code in (401, 403, 429)
            except Exception as exc:
                receipt.update(status='SOURCE_ERROR', error=str(exc))
            report['attempts'].append(receipt)
            write_json(root / 'GDELT_SOURCE_PROBE.json', report)
            print('GDELT_NUMERIC_PROBE', window['name'], mode, receipt['status'], receipt.get('rows'), flush=True)
            time.sleep(6)
    errors = any(a['status'] != 'NUMERIC_ROWS_RETURNED' for a in report['attempts'])
    report['status'] = 'PARTIAL_NUMERIC_PROBE_HISTORY_UNPROVEN' if errors else 'NUMERIC_PROBE_WINDOWS_RETURNED_NOT_FULL_HISTORY'
    file = root / 'GDELT_SOURCE_PROBE.json'
    write_json(file, report)
    if files:
        tag = f"gdelt-numeric-probe-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
        gh_retry('release', 'create', tag, '--draft', '--target', os.environ['GITHUB_SHA'], '--title', tag,
                 '--notes', 'Bounded numeric source probes only; not full historical or full-universe GDELT coverage. See explicit failed windows.')
        publish_assets(tag, *files, file)
        gh_retry('release', 'edit', tag, '--draft=false')
    if errors:
        raise RuntimeError('One or more requested numeric source windows unavailable; evidence retained, no zero filling')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    probe(Path(args.directory), json.loads(Path('ci/GDELT_SOURCE_PROBE_REQUEST.json').read_text()))


if __name__ == '__main__':
    main()

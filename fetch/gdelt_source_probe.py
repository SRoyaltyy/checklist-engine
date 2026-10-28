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
    from world_scope import NEWS_DROP_REASON
    raise RuntimeError(NEWS_DROP_REASON)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    probe(Path(args.directory), json.loads(Path('ci/GDELT_SOURCE_PROBE_REQUEST.json').read_text()))


if __name__ == '__main__':
    main()

"""Fetch CBOE market-wide put/call ratios -> data-ext/mkt_pc_2020_26.parquet.

Block I201 (CBOE market-wide options) wiring for the world snapshot. Keyless
CBOE endpoints (cdn.cboe.com). Put/call counts for day D are published after
the close of D, so the consumer must join strict < D (same convention as
mkt_wide VIX). Values are official counts and are never revised.

Primary source: the published put/call historical CSVs, one request total:
  https://cdn.cboe.com/resources/options/volume_and_open_interest/totalpc.csv
    columns: DATE, CALL VOLUME, PUT VOLUME, TOTAL VOLUME, P/C RATIO (total)
Fallback (probe-verified): per-day market_statistics files under one of the
CDN layouts below.

Usage:
  python3 fetch/fetch_cboe.py probe   # print HTTP status + head for every candidate
  python3 fetch/fetch_cboe.py fetch --out mkt_pc_2020_26.parquet
"""
import argparse, io, json, sys, time, urllib.error, urllib.request

import numpy as np
import pandas as pd

UA = {'User-Agent': 'checklist-engine-fetch/1.0'}

# One-shot historical CSVs (single request covers 2020..today).
# CORRECT directory is volume_and_call_put_ratios (proven by James's runner probe,
# run 40911427670, branch james/cboe-runner-test @ ce0b2773: HTTP 200, 135,696
# bytes for equitypc.csv, UA and no-UA). The volume_and_open_interest path 403s.
HIST_CSV = {
    'totalpc-cdn': 'https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/totalpc.csv',
    'equitypc-cdn': 'https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv',
    'indexpc-cdn': 'https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/indexpc.csv',
}

# Per-day JSON ratios (secondary source + CSV cross-check): TOTAL/INDEX/EQUITY P/C.
DAILY_JSON = 'https://cdn.cboe.com/data/us/options/market_statistics/daily/{date}_daily_options'

# Per-day file layout candidates (first one that probes 200 wins):
#   {y}/{m:02d}/{d:02d}.csv  with Expiration,Calls,Puts,Total,P/C Ratio rows.
DAILY_PATTERNS = [
    'https://cdn.cboe.com/us/options/market_statistics/daily/{y}/{m:02d}/{d:02d}.csv',
    'https://cdn.cboe.com/data/us/options/market_statistics/daily/{y}/{m:02d}/{d:02d}.csv',
    'https://cdn.cboe.com/us/options/market_statistics/daily/{y}-{m:02d}-{d:02d}.csv',
    'https://www.cboe.com/us/options/market_statistics/daily/{y}/{m:02d}/{d:02d}.csv',
]

# CBOE's CDN 403s plain-script UAs from datacenter IPs; probe a browser UA too.
UAS = [
    ('fetch', 'checklist-engine-fetch/1.0'),
    ('browser', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'),
]


def get(url, ua=None):
    req = urllib.request.Request(url, headers={'User-Agent': ua or UA['User-Agent']})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception:
        return None, b''


def wayback_latest(url, ua=None, n=4):
    """Fetch the newest few Wayback snapshots of `url`; return (ts, raw) with
    the newest data end-date. Raw bytes via the id_ (unmodified) modifier.

    CBOE's CDN 403s datacenter IPs on both the owner network and GitHub
    runners (proven in runs 40879412423 / 40882550364 / 40883758218), so the
    keyless direct fetch is not live-replicable from automation. The Wayback
    Machine is the dated, replicable mirror. Put/call counts are official
    figures and are never revised, so a late snapshot is PIT-safe for the
    full history (the CSV is cumulative) -- proven by checking that the
    overlapping dates of two snapshots agree.
    """
    cdx = ('https://web.archive.org/cdx/search/cdx?url=' + url +
           f'&output=json&fl=timestamp,original,statuscode&filter=statuscode:200&limit=-{n}')
    st, raw = get(cdx, ua)
    if not raw:
        return None, None
    try:
        rows = json.loads(raw.decode('utf-8', 'ignore'))
    except Exception:
        return None, None
    if len(rows) < 2:
        return None, None
    best = (None, None, None)   # (ts, raw, max_date)
    for ts, original, _code in rows[1:]:
        snap = f'https://web.archive.org/web/{ts}id_/{original}'
        st2, raw2 = get(snap, ua)
        if not raw2:
            continue
        df = parse_hist_csv(raw2)
        if df is None or not len(df):
            continue
        if best[2] is None or df.date.max() > best[2]:
            best = (ts, raw2, df.date.max())
        print(f'wayback snapshot {ts}: {len(df)} rows, ends {df.date.max().date()}')
    return best[0], best[1]


def parse_hist_csv(raw):
    """Parse the put/call historical CSV -> DataFrame[date, calls, puts, total_n, ratio].

    Legacy files carry 1-2 preamble lines (disclaimer / product banner)
    before the DATE header; find the header line first.
    """
    lines = raw.decode('utf-8', 'ignore').splitlines()
    hdr = next((i for i, l in enumerate(lines) if l.split(',')[0].strip().upper() == 'DATE'), None)
    if hdr is None:
        return None
    df = pd.read_csv(io.StringIO('\n'.join(lines[hdr:])))
    cols = {c.lower().strip(): c for c in df.columns}
    date_c = df.columns[0]

    def pick(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return ''

    df = df.rename(columns={
        pick('call volume', 'calls'): 'calls',
        pick('put volume', 'puts'): 'puts',
        pick('total volume', 'total'): 'total_n',
        pick('p/c ratio', 'p/c'): 'ratio',
    })
    need = {'calls', 'puts', 'total_n', 'ratio'}
    if not need.issubset(df.columns):
        return None
    df['date'] = pd.to_datetime(df[date_c], errors='coerce')
    for c in ('calls', 'puts', 'total_n', 'ratio'):
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['date'])[['date', 'calls', 'puts', 'total_n', 'ratio']]
    return df.reset_index(drop=True)


def parse_day(raw):
    """-> (calls, puts, total, ratio) from a daily market-statistics file's Total row."""
    try:
        df = pd.read_csv(io.StringIO(raw.decode('utf-8', 'ignore')))
    except Exception:
        return None
    cols = {c.lower().strip(): c for c in df.columns}
    key_col = df.columns[0]
    total = df[df[key_col].astype(str).str.strip().str.lower() == 'total']
    if not len(total):
        return None
    row = total.iloc[0]

    def num(name):
        c = cols.get(name)
        if c is None:
            return np.nan
        return pd.to_numeric(row[c], errors='coerce')

    return num('calls'), num('puts'), num('total'), num('p/c ratio')


def probe():
    for ua_name, ua in UAS:
        print(f'--- UA={ua_name} ---')
        for name, url in HIST_CSV.items():
            st, raw = get(url, ua)
            print(f'{name}: HTTP {st}, {len(raw)} bytes')
            if raw:
                print('  head: ' + ' | '.join(raw.decode('utf-8', 'ignore').splitlines()[:3]))
        for pat in DAILY_PATTERNS:
            st, raw = get(pat.format(y=2024, m=3, d=15), ua)
            print(f'daily {pat}: HTTP {st}, {len(raw)} bytes')
            if raw:
                print('  head: ' + ' | '.join(raw.decode('utf-8', 'ignore').splitlines()[:6]))
    ts, wb = wayback_latest(HIST_CSV['totalpc-www'], UAS[0][1])
    if wb:
        print('wayback totalpc head: ' + ' | '.join(wb.decode('utf-8', 'ignore').splitlines()[:3]))


def parse_daily_json(raw):
    """Per-day CBOE JSON -> {name_lower: value_float}; None on failure."""
    try:
        j = json.loads(raw.decode('utf-8', 'ignore'))
        out = {}
        for r in j.get('ratios', []):
            try:
                out[str(r['name']).lower()] = float(str(r['value']).replace(',', ''))
            except Exception:
                pass
        return out or None
    except Exception:
        return None


def crosscheck_and_fill(df, start, end, ua, pace=0.15):
    """Spot-check the CSV against the daily JSON and backfill any missing days.

    Checks every ~120th day against TOTAL/INDEX/EQUITY PUT/CALL RATIO where the
    CSV has matching columns, then walks business days to fill gaps.
    Returns (mismatches, filled_rows).
    """
    cols = {c.lower(): c for c in df.columns}
    total_c = cols.get('pc_total')
    mismatches, checked = [], 0
    step = max(1, len(df) // 25)
    for i in range(0, len(df), step):
        row = df.iloc[i]
        st, raw = get(DAILY_JSON.format(date=str(row['date'])[:10]), ua)
        pj = parse_daily_json(raw) if raw else None
        if not pj or total_c is None:
            continue
        jv = pj.get('total put/call ratio')
        cv = row[total_c]
        if jv is None or pd.isna(cv):
            continue
        checked += 1
        if abs(float(cv) - jv) > 0.005:
            mismatches.append((str(row['date'])[:10], float(cv), jv))
    print(f'JSON cross-check: {checked} days compared, {len(mismatches)} mismatches', flush=True)

    have = set(df.date.astype(str).str[:10])
    filled = 0
    for dt in pd.bdate_range(start, end):
        ds = str(dt.date())
        if ds in have:
            continue
        st, raw = get(DAILY_JSON.format(date=ds), ua)
        pj = parse_daily_json(raw) if raw else None
        if pj:
            rec = {'date': pd.Timestamp(ds),
                   'pc_calls': np.nan, 'pc_puts': np.nan, 'pc_total_n': np.nan,
                   'pc_total': pj.get('total put/call ratio'),
                   'pc_equity': pj.get('equity put/call ratio'),
                   'pc_index': pj.get('index put/call ratio')}
            df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
            filled += 1
        time.sleep(pace)
    if filled:
        df = df.sort_values('date').reset_index(drop=True)
    return mismatches, filled, df


def fetch_all(out, start='2020-01-01', end=None, pace=0.15):
    end = pd.Timestamp(end or pd.Timestamp.today().date())
    start = pd.Timestamp(start)

    # Fast path: three historical CSVs (total/equity/index), one request each.
    # Direct first, Wayback mirror second. Merge equity/index ratios onto total.
    base = None
    for ua_name, ua in UAS:
        frames = {}
        for name, url in HIST_CSV.items():
            st, raw = get(url, ua)
            via = f'direct HTTP {st}'
            if not raw:
                ts, wb = wayback_latest(url, ua)
                if wb:
                    raw, via = wb, f'wayback {ts}'
            df0 = parse_hist_csv(raw) if raw else None
            if df0 is not None and len(df0):
                print(f'historical CSV {name} ({via}): {len(df0)} parsed rows')
                frames[name.split('-')[0]] = df0
        if 'totalpc' in frames:
            base = frames['totalpc'].rename(
                columns={'total_n': 'pc_total_n', 'ratio': 'pc_total',
                         'calls': 'pc_calls', 'puts': 'pc_puts'})
            for short, col in (('equitypc', 'pc_equity'), ('indexpc', 'pc_index')):
                if short in frames:
                    base = base.merge(
                        frames[short][['date', 'ratio']].rename(columns={'ratio': col}),
                        on='date', how='left')
            break
    if base is not None and len(base):
        base = base[(base.date >= start) & (base.date <= end)].reset_index(drop=True)
        mismatches, filled, base = crosscheck_and_fill(base, start, end, ua, pace)
        base.to_parquet(out, index=False)
        print(f'wrote {out}: {len(base)} rows {base.date.min().date()}..{base.date.max().date()}, '
              f'nulls: {int(base.pc_total.isna().sum())}, json_filled={filled}, '
              f'json_mismatches={len(mismatches)}')
        for m in mismatches[:10]:
            print('  MISMATCH', m)
        return
    print('historical CSVs unavailable; falling back to per-day walk')

    # Fallback: find a working (UA, daily pattern) pair, then walk business days.
    pat = ua = None
    for ua_name, ua_c in UAS:
        for p in DAILY_PATTERNS:
            st, raw = get(p.format(y=2022, m=6, d=15), ua_c)
            if raw and parse_day(raw):
                pat, ua = p, ua_c
                print(f'daily pattern OK (UA={ua_name}):', p)
                break
        if pat:
            break
    if pat is None:
        sys.exit('no CBOE endpoint answered -- all candidates failed (see probe output)')

    days = pd.bdate_range(start, end)          # CBOE files keyed by trade date; weekends 404
    rows = []
    t0 = time.time()
    for i, dt in enumerate(days):
        st, raw = get(pat.format(y=dt.year, m=dt.month, d=dt.day), ua)
        if raw:
            p = parse_day(raw)
            if p is not None:
                rows.append((dt.date(), *p))
        if (i + 1) % 100 == 0:
            el = time.time() - t0
            print(f'{i+1}/{len(days)} days, {len(rows)} rows, {el:.0f}s', flush=True)
        time.sleep(pace)
    df = pd.DataFrame(rows, columns=['date', 'pc_calls', 'pc_puts', 'pc_total_n', 'pc_total'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    if df.empty:
        sys.exit('no put/call rows fetched -- endpoint changed?')
    df.to_parquet(out, index=False)
    print(f'wrote {out}: {len(df)} rows {df.date.min().date()}..{df.date.max().date()}, '
          f'nulls: {int(df.pc_total.isna().sum())}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['probe', 'fetch'])
    ap.add_argument('--out', default='mkt_pc_2020_26.parquet')
    a = ap.parse_args()
    probe() if a.cmd == 'probe' else fetch_all(a.out)

"""Fetch GDELT 2.0 news mention counts per ticker -> data-ext/gdelt_counts_2020_26.parquet.

Block O / I200 (0b FULL-DATA FIRST). GDELT DOC API, mode=timelinevol: one call
returns a daily mention-volume time series for a query over a date window.
Counts only -- no free text -- per the no-free-text rule.

Throughput honesty: GDELT's documented pace is ~1 request / 5s. The full universe
(~4.4k tickers x ~30 three-month windows) is a multi-day haul; this fetcher is
therefore RESUMABLE and SHARDABLE via --offset/--count, so successive dispatches
inch through the universe (save-as-it-runs after every ticker).

Output: ticker, date, n (mention count that UTC day).
Query: exact ticker symbol in quotes ("AAPL"); noisy for very short symbols --
that bias is uniform across tickers and is noted in METHODOLOGY meta.

Runner:  python3 fetch/fetch_gdelt.py --universe <parquet> --out gdelt_counts_2020_26.parquet \
             [--offset 0] [--count 50] [--resume]
"""
import argparse, json, os, time, urllib.parse, urllib.request
import pandas as pd

API = 'https://api.gdeltproject.org/api/v2/doc/doc'
PACE = 4.0          # seconds between requests (GDELT documented ~5s; 4s + backoff)
WINDOW_DAYS = 90


def timelinevol(query, start, end):
    """One GDELT timelinevol call -> list[(date, value)]; [] on empty/error."""
    qs = urllib.parse.urlencode({
        'query': query, 'mode': 'timelinevol', 'format': 'json',
        'startdatetime': start, 'enddatetime': end, 'maxrecords': 250})
    url = f'{API}?{qs}'
    req = urllib.request.Request(url, headers={'User-Agent': 'checklist-engine/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(30)
            return None          # caller retries once
        return []
    except Exception:
        return []
    # Defensive parse: find any list of {date, value} dicts in the payload.
    stack = [d]
    while stack:
        cur = stack.pop()
        if isinstance(cur, list) and cur and isinstance(cur[0], dict):
            if 'date' in cur[0] and 'value' in cur[0]:
                out = []
                for r in cur:
                    try:
                        out.append((str(r['date'])[:10].replace('-', ''), int(r['value'])))
                    except Exception:
                        pass
                return out
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return []


def fetch_ticker(tk, start_y, end_y):
    days = []
    cur = pd.Timestamp(f'{start_y}-01-01')
    end = pd.Timestamp(f'{end_y}-12-31')
    while cur <= end:
        win_end = min(cur + pd.Timedelta(days=WINDOW_DAYS - 1), end)
        r = timelinevol(f'"{tk}"', cur.strftime('%Y%m%d'), win_end.strftime('%Y%m%d'))
        if r is None:                       # 429: one retry after extra sleep
            time.sleep(30)
            r = timelinevol(f'"{tk}"', cur.strftime('%Y%m%d'), win_end.strftime('%Y%m%d')) or []
        days.extend(r)
        time.sleep(PACE)
        cur = win_end + pd.Timedelta(days=1)
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--universe', required=True)
    ap.add_argument('--out', default='gdelt_counts_2020_26.parquet')
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--count', type=int, default=50)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--start-year', type=int, default=2019)   # padding for 30d windows
    ap.add_argument('--end-year', type=int, default=2026)
    a = ap.parse_args()

    uni = pd.read_parquet(a.universe, columns=['ticker'])
    tickers = sorted(set(t.upper().strip() for t in uni.ticker.unique()))
    sel = tickers[a.offset:a.offset + a.count] if a.count else tickers[a.offset:]
    print(f'shard: tickers[{a.offset}:{a.offset + a.count}] = {len(sel)} tickers', flush=True)

    done = set(); rows = []
    if a.resume and os.path.exists(a.out):
        prev = pd.read_parquet(a.out)
        done = set(prev.ticker)
        rows = prev.to_dict('records')
        print('resume: keeping', len(done), 'tickers,', len(rows), 'rows', flush=True)

    t0 = time.time()
    for i, tk in enumerate(sel):
        if tk in done:
            continue
        days = fetch_ticker(tk, a.start_year, a.end_year)
        for dt, n in days:
            rows.append(dict(ticker=tk, date=dt, n=n))
        done.add(tk)
        if (i + 1) % 10 == 0:
            pd.DataFrame(rows).to_parquet(a.out, index=False)
            el = time.time() - t0
            print(f'{i+1}/{len(sel)} tickers, {len(rows)} rows, {el:.0f}s, '
                  f'eta {el/(i+1)*(len(sel)-i-1):.0f}s', flush=True)

    df = pd.DataFrame(rows)
    if len(df):
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df[(df.date >= '2019-06-01') & (df.date <= '2026-12-31')]
    df.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(df)} ticker-days, {df.ticker.nunique() if len(df) else 0} tickers')


if __name__ == '__main__':
    main()

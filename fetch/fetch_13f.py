"""Fetch 13F-HR holdings mentions per ticker (EDGAR full-text search by CUSIP)
-> data-ext/f13_hits_2020_26.parquet.

Block M / I199 (0b FULL-DATA FIRST). Approach, validated 2026-10-25:
  - ticker -> CUSIP via OpenFIGI (anonymous tier: 25 jobs/request, ~25 req/min;
    Common Stock, US exchange). Tickers OpenFIGI cannot map get no rows (NaN in
    the snapshot, flagged).
  - EDGAR FTS (efts.sec.gov/LATEST/search-index) DOES index 13F information
    tables by CUSIP (AAPL CUSIP: >=10k hits). One query per (ticker, year),
    forms=13F-HR + 13F-HR/A, paginated 100/page up to MAX_PAGES. Mega caps
    saturate the page cap -> f13_n is then a LOWER BOUND (flagged in meta;
    monotonic in true filer count).

Raw rows: ticker, cik (filer), adsh, period_ending, file_date. The snapshot
derives PIT values from these (filed < D), so amendments and restatements keep
their natural timeline. Volume: ~4.4k tickers x ~7 years, sharded + resumable;
this is a long-haul job in the GDELT class.

Runner:  python3 fetch/fetch_13f.py --universe <parquet> --out f13_hits_2020_26.parquet \
             [--offset 0] [--count 50] [--resume]
"""
import argparse, json, os, time, urllib.parse, urllib.request
import pandas as pd

SEC_UA = {'User-Agent': 'checklist-engine research contact@example.com'}
MAX_PAGES = 10          # x100 hits per (ticker, year); mega caps saturate
PACE = 2.5              # seconds between FTS requests (fair-use; FTS is undocumented)


def http_json(url, headers, retries=4, timeout=90):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (i + 1))
                continue
            last = e
            time.sleep(2 ** i)
        except Exception as e:
            last = e
            time.sleep(2 ** i)
    print('FAIL', url[:110], type(last).__name__ if last else '?', flush=True)
    return None


def openfigi_map(tickers):
    """ticker -> cusip via OpenFIGI anonymous tier. Returns dict; unmappable
    tickers are absent."""
    out = {}
    jobs = [[{'idType': 'TICKER', 'idValue': tk, 'exchCode': 'US',
              'securityType2': 'Common Stock'}] for tk in tickers]
    for i in range(0, len(jobs), 25):
        batch = jobs[i:i + 25]
        req = urllib.request.Request(
            'https://api.openfigi.com/v3/mapping', data=json.dumps([b[0] for b in batch]).encode(),
            headers={'Content-Type': 'application/json'}, method='POST')
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    res = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(30); continue
                raise
        for tk, rr in zip(tickers[i:i + 25], res):
            for m in rr.get('data', []):
                cus = m.get('idValue') if m.get('idType') == 'CUSIP' else None
                if cus:
                    out[tk] = cus
                    break
        if (i // 25) % 10 == 9:
            print(f'openfigi: {len(out)}/{i + len(batch)} mapped', flush=True)
        time.sleep(2.6)      # ~25 req/min ceiling
    return out


def f13_hits(cusip, year):
    """All FTS hits for a CUSIP in one filing year -> list of dicts."""
    rows = []
    for page in range(MAX_PAGES):
        qs = urllib.parse.urlencode({
            'q': f'"{cusip}"', 'forms': '13F-HR,13F-HR/A',
            'startdt': f'{year}-01-01', 'enddt': f'{year}-12-31',
            'size': 100, 'from': page * 100})
        d = http_json(f'https://efts.sec.gov/LATEST/search-index?{qs}', SEC_UA)
        if not d:
            break
        hits = d.get('hits', {}).get('hits', [])
        for h in hits:
            s = h.get('_source', {})
            adsh = s.get('adsh', '')
            fd = s.get('file_date', '')
            pe = s.get('period_ending', '')
            ciks = s.get('ciks', [])
            if adsh and fd and pe and ciks:
                rows.append(dict(cik=str(ciks[0]).zfill(10), adsh=adsh,
                                 period_ending=pe, file_date=fd))
        if len(hits) < 100:
            break
        time.sleep(PACE)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--universe', required=True)
    ap.add_argument('--out', default='f13_hits_2020_26.parquet')
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--count', type=int, default=50)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--years', default='2019,2020,2021,2022,2023,2024,2025,2026')
    a = ap.parse_args()
    years = [int(y) for y in a.years.split(',')]

    uni = pd.read_parquet(a.universe, columns=['ticker'])
    tickers = sorted(set(t.upper().strip() for t in uni.ticker.unique()))
    sel = tickers[a.offset:a.offset + a.count] if a.count else tickers[a.offset:]
    print(f'shard: tickers[{a.offset}:{a.offset + a.count}] = {len(sel)}', flush=True)

    done = set(); rows = []
    if a.resume and os.path.exists(a.out):
        prev = pd.read_parquet(a.out)
        done = set(prev.ticker)
        rows = prev.to_dict('records')
        print('resume: keeping', len(done), 'tickers,', len(rows), 'rows', flush=True)

    need = [t for t in sel if t not in done]
    cusip_map = openfigi_map(need) if need else {}
    print('cusip mapped:', len(cusip_map), '/', len(need), flush=True)

    t0 = time.time()
    for i, tk in enumerate(need):
        cus = cusip_map.get(tk)
        if cus:
            for y in years:
                for r in f13_hits(cus, y):
                    rows.append(dict(ticker=tk, **r))
                time.sleep(PACE)
        done.add(tk)
        if (i + 1) % 10 == 0:
            pd.DataFrame(rows).to_parquet(a.out, index=False)
            el = time.time() - t0
            print(f'{i+1}/{len(need)} tickers, {len(rows)} rows, {el:.0f}s, '
                  f'eta {el/(i+1)*(len(need)-i-1):.0f}s', flush=True)

    df = pd.DataFrame(rows)
    if len(df):
        df = df.drop_duplicates(subset=['ticker', 'adsh'])
        df = df[(df.file_date >= '2019-06-01') & (df.file_date <= '2026-12-31')]
    df.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(df)} hits, {df.ticker.nunique() if len(df) else 0} tickers')


if __name__ == '__main__':
    main()

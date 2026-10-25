"""Fetch SEC EDGAR Form 4 (insider) FILING-DATE counts -> data-ext/form4_counts_2020_26.parquet.

Block E / I187 date-count lens (0b FULL-DATA FIRST). A Form 4 filing is public
on its filingDate; the snapshot may use it from the next session (strict < D in
facets_world.py). The value lens (shares traded, role) needs XML parsing and is
NOT built here -- date counts only, per the staged plan.

Steps (runner, ~4-6k tickers):
  1. universe tickers from the data-2020-24-v1 release (same file world_fetch.sh gets)
  2. ticker -> CIK map from https://www.sec.gov/files/company_tickers.json
  3. per CIK: data.sec.gov/submissions/CIK##########.json (SEC fair-use: <=10 rps,
     descriptive User-Agent). filings.recent covers ~1000 most recent filings,
     ample for 2020-26 Form 4s; older-page merge is a later refinement.
  4. aggregate Form 4 filings to per (ticker, filingDate) counts

Output: ticker, date (filingDate), n (Form 4 filings that day).
Resumable: writes rows incrementally to a temp parquet every 250 CIKs; --resume
continues from tickers already present.

Runner:  python3 fetch/fetch_form4.py --universe universe_2020_survivors_le2024.parquet \
             --out form4_counts_2020_26.parquet [--limit N] [--resume]
"""
import argparse, json, os, sys, time, urllib.request
import pandas as pd

SEC_HEADERS = {'User-Agent': 'checklist-engine research contact@example.com',
               'Accept-Encoding': 'gzip, deflate'}


def get(url, timeout=60, retries=4):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=SEC_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            if url.endswith('.json.gz') or raw[:2] == b'\x1f\x8b':
                import gzip
                raw = gzip.decompress(raw)
            return raw
        except Exception as e:
            last = e
            time.sleep(2 ** i)
    raise last


def load_cik_map():
    raw = json.loads(get('https://www.sec.gov/files/company_tickers.json'))
    m = {}
    for rec in raw.values():
        t = str(rec.get('ticker', '')).upper().strip()
        if t:
            m[t] = int(rec['cik_str'])
    return m


def form4_dates(cik):
    """Filing dates of Form 4s for one CIK from submissions API (recent page)."""
    url = f'https://data.sec.gov/submissions/CIK{cik:010d}.json'
    d = json.loads(get(url))
    recent = d.get('filings', {}).get('recent', {})
    forms = recent.get('form', []); dates = recent.get('filingDate', [])
    return [dt for f, dt in zip(forms, dates) if f == '4']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--universe', required=True)
    ap.add_argument('--out', default='form4_counts_2020_26.parquet')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--start', default='2020-01-01')
    ap.add_argument('--end', default='2026-12-31')
    a = ap.parse_args()

    uni = pd.read_parquet(a.universe, columns=['ticker'])
    tickers = sorted(set(t.upper().strip() for t in uni.ticker.unique()))
    if a.limit:
        tickers = tickers[:a.limit]
    print('universe tickers:', len(tickers), flush=True)

    done = set()
    rows = []
    if a.resume and os.path.exists(a.out):
        prev = pd.read_parquet(a.out)
        done = set(prev.ticker)
        rows = prev.to_dict('records')
        print('resume: keeping', len(done), 'tickers,', len(rows), 'rows', flush=True)

    cik_map = load_cik_map()
    print('cik map:', len(cik_map), 'tickers', flush=True)

    todo = [t for t in tickers if t not in done]
    print('to fetch:', len(todo), flush=True)
    t0 = time.time(); n_ok = n_miss = 0
    for i, t in enumerate(todo):
        cik = cik_map.get(t)
        if cik is None:
            n_miss += 1
        else:
            try:
                for dt in form4_dates(cik):
                    if a.start <= dt <= a.end:
                        rows.append(dict(ticker=t, date=dt, n=1))
                n_ok += 1
            except Exception as e:
                print('WARN', t, type(e).__name__, str(e)[:80], flush=True)
                n_miss += 1
        if (i + 1) % 250 == 0:
            df = pd.DataFrame(rows)
            agg = df.groupby(['ticker', 'date'], as_index=False).n.sum() if len(df) else df
            agg.to_parquet(a.out, index=False)
            el = time.time() - t0
            print(f'{i+1}/{len(todo)} tickers, {len(agg)} rows, ok={n_ok} miss={n_miss}, '
                  f'{el:.0f}s, eta {el/(i+1)*(len(todo)-i-1):.0f}s', flush=True)
        time.sleep(0.11)   # SEC fair-use <= 10 rps

    df = pd.DataFrame(rows)
    agg = df.groupby(['ticker', 'date'], as_index=False).n.sum() if len(df) else \
        pd.DataFrame(columns=['ticker', 'date', 'n'])
    agg.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(agg)} ticker-days, {agg.ticker.nunique() if len(agg) else 0} tickers '
          f'with Form 4s; ok={n_ok} miss={n_miss}')


if __name__ == '__main__':
    main()

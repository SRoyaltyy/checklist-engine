"""Fetch SEC XBRL fundamentals via the frames API -> data-ext/xbrl_fundamentals_2020_26.parquet.

Block H / I192 (0b FULL-DATA FIRST). The frames API
(data.sec.gov/api/xbrl/frames/us-gaap/{CONCEPT}/USD/CYyyyyQn.json) returns every
entity that filed a value for a calendar period, each row carrying `filed`
(the SEC filing date). Joining on filed < D is point-in-time safe and immune to
restatements (a restatement lands as a NEW filed date; the old value stays the
one knowable before that date -- exactly what the snapshot wants).

Coverage note: CY frames only capture calendar-aligned filers (~70%+ of US
equities are Dec fiscal); fiscal-offset companies get sparser coverage. The
per-CIK companyfacts variant covers everything but is ~GB-scale for the full
universe -- a later refinement if the room wants it.

Output (long): ticker, metric, period_end, filed, val, yoy (for rev/ni).
Metrics (v1): Revenues, NetIncomeLoss, OperatingIncomeLoss, GrossProfit,
Assets, Liabilities, StockholdersEquity, LongTermDebt,
CashAndCashEquivalentsAtCarryingValue, CommonStockSharesOutstanding,
EarningsPerShareBasic, ResearchAndDevelopmentExpense.

Runner:  python3 fetch/fetch_xbrl.py --out xbrl_fundamentals_2020_26.parquet [--concepts X,Y] [--years 2020,2021]
"""
import argparse, json, time, urllib.request
import pandas as pd

SEC_HEADERS = {'User-Agent': 'checklist-engine research contact@example.com'}

CONCEPTS = ['Revenues', 'NetIncomeLoss', 'OperatingIncomeLoss', 'GrossProfit',
            'Assets', 'Liabilities', 'StockholdersEquity', 'LongTermDebt',
            'CashAndCashEquivalentsAtCarryingValue', 'CommonStockSharesOutstanding',
            'EarningsPerShareBasic', 'ResearchAndDevelopmentExpense']
YOY_METRICS = {'Revenues', 'NetIncomeLoss'}


def get_json(url, retries=4):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=SEC_HEADERS)
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2 ** i)
    print('FAIL', url, type(last).__name__, str(last)[:80])
    return None


def load_cik_map():
    d = get_json('https://www.sec.gov/files/company_tickers.json')
    m = {}
    for rec in d.values():
        t = str(rec.get('ticker', '')).upper().strip()
        if t:
            m[int(rec['cik_str'])] = t
    return m


def frame_rows(concept, period):
    """One frames response -> list of dicts (cik, period_end, filed, val)."""
    url = f'https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/USD/{period}.json'
    d = get_json(url)
    if not d or 'data' not in d:
        return []
    out = []
    for r in d['data']:
        val = r.get('val')
        filed = r.get('filed')
        end = r.get('end')
        if val is None or not filed or not end:
            continue
        out.append(dict(cik=int(r['cik']), period_end=end, filed=filed, val=float(val)))
    return out


def periods_for(years):
    ps = []
    for y in years:
        ps.append(f'CY{y}')
        for q in (1, 2, 3, 4):
            ps.append(f'CY{y}Q{q}')
    return ps


def add_yoy(df):
    """YoY growth per (ticker, metric): same quarter/period one year earlier."""
    out = []
    for (t, m), g in df[df.metric.isin(YOY_METRICS)].groupby(['ticker', 'metric']):
        g = g.sort_values('period_end').reset_index(drop=True)
        by_end = dict(zip(g.period_end, g.val))
        yoy = []
        for _, r in g.iterrows():
            pe = pd.Timestamp(r.period_end)
            prev = pe - pd.DateOffset(years=1)
            prev_s = prev.strftime('%Y-%m-%d')
            # tolerate 1-day fiscal drift
            hit = by_end.get(prev_s)
            if hit is None:
                for dt in (prev - pd.Timedelta(days=1), prev + pd.Timedelta(days=1)):
                    hit = by_end.get(dt.strftime('%Y-%m-%d'))
                    if hit is not None:
                        break
            yoy.append((r.val / hit - 1.0) if hit else None)
        g = g.copy(); g['yoy'] = yoy
        out.append(g)
    return pd.concat(out, ignore_index=True) if out else df.iloc[0:0].copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='xbrl_fundamentals_2020_26.parquet')
    ap.add_argument('--concepts', default=','.join(CONCEPTS))
    ap.add_argument('--years', default='2019,2020,2021,2022,2023,2024,2025,2026')
    a = ap.parse_args()
    concepts = [c.strip() for c in a.concepts.split(',') if c.strip()]
    years = [int(y) for y in a.years.split(',')]
    periods = periods_for(years)
    print(f'{len(concepts)} concepts x {len(periods)} periods', flush=True)

    cik2t = load_cik_map()
    print('cik map:', len(cik2t), flush=True)

    rows = []
    t0 = time.time(); n_req = 0
    for c in concepts:
        for p in periods:
            for r in frame_rows(c, p):
                t = cik2t.get(r['cik'])
                if t:
                    rows.append(dict(ticker=t, metric=c, period_end=r['period_end'],
                                     filed=r['filed'], val=r['val']))
            n_req += 1
            time.sleep(0.11)      # SEC fair-use
        df = pd.DataFrame(rows)
        print(f'{c}: cumulative {len(df)} rows, {n_req} requests, {time.time()-t0:.0f}s', flush=True)
        if len(df):
            df.to_parquet(a.out, index=False)   # save-as-it-runs

    df = pd.DataFrame(rows)
    if not len(df):
        sys.exit('no rows fetched')
    df['period_end'] = pd.to_datetime(df['period_end']).dt.strftime('%Y-%m-%d')
    df['filed'] = pd.to_datetime(df['filed']).dt.strftime('%Y-%m-%d')
    yoy = add_yoy(df)
    rest = df[~df.metric.isin(YOY_METRICS)].copy(); rest['yoy'] = None
    out = pd.concat([yoy, rest], ignore_index=True)
    out.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(out)} rows, {out.ticker.nunique()} tickers, '
          f'{out.metric.nunique()} metrics')


if __name__ == '__main__':
    import sys
    main()

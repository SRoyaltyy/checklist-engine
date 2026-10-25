"""Fetch FRED/ALFRED macro series with VINTAGES -> data-ext/fred_wide_2020_26.parquet.

Block I / I195. The FRED_API_KEY Actions secret is required. Missing keys or
incomplete source responses fail the source job; no successful empty fetch.

Point-in-time: ALFRED returns every (vintage_date, observation) pair. A value
is knowable on day D only if its vintage_date < D; among those, the latest
observation date wins. Series that are never revised (market rates) pass
through the same machinery harmlessly.

Output (long): series, obs_date, vintage_date, value.
Default series (v1): DGS10, T10Y2Y, DTB3, ICSA (weekly claims), UMCSENT (monthly).

Runner:  FRED_API_KEY=... python3 fetch/fetch_fred.py --out fred_wide_2020_26.parquet
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request, urllib.error
import pandas as pd

SERIES = ['DGS10', 'T10Y2Y', 'DTB3', 'ICSA', 'UMCSENT']


def alfred_page(key, sid, offset, limit):
    qs=urllib.parse.urlencode(dict(series_id=sid,api_key=key,file_type='json',
        realtime_start='1900-01-01',realtime_end='9999-12-31',output_type=1,
        observation_start='2018-01-01',observation_end='2026-12-31',offset=offset,limit=limit))
    req=urllib.request.Request('https://api.stlouisfed.org/fred/series/observations?'+qs,
        headers={'User-Agent':'checklist-engine research'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=180) as response:return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            code=exc.code
            if code not in (429,500,502,503,504) or attempt==3:
                raise RuntimeError(f'FRED {sid}: HTTP {code}; request URL and key redacted') from None
        except (OSError,ValueError):
            if attempt==3:raise RuntimeError(f'FRED {sid}: transport/JSON failure; request URL and key redacted') from None
        time.sleep(2**attempt)
    raise RuntimeError(f'FRED {sid}: retries exhausted')


def alfred_observations(key, sid, limit=100000):
    out=[];offset=0
    while True:
        page=alfred_page(key,sid,offset,limit)
        observations=page.get('observations',[])
        total=int(page.get('count',len(observations)))
        if not observations and offset<total:raise RuntimeError(f'FRED {sid}: incomplete pagination at {offset}/{total}')
        for item in observations:
            if item.get('value') in (None,'.'):continue
            out.append(dict(series=sid,obs_date=item['date'],
                vintage_date=item['realtime_start'],value=float(item['value'])))
        offset+=len(observations)
        if offset>=total:break
        time.sleep(.25)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='fred_wide_2020_26.parquet')
    ap.add_argument('--series', default=','.join(SERIES))
    a = ap.parse_args()
    key = os.environ.get('FRED_API_KEY', '')
    if not key:
        sys.exit('BLOCKED_SECRET: FRED_API_KEY not set -- wire-only mode, fetch skipped')
    rows = []
    for sid in [s.strip() for s in a.series.split(',') if s.strip()]:
        got = alfred_observations(key, sid)
        rows.extend(got)
        print(sid, len(got), 'vintage observations', flush=True)
        time.sleep(1.5)
    if not rows:
        sys.exit('no observations fetched -- check key/quota')
    df = pd.DataFrame(rows)
    df = df[(df.obs_date >= '2018-01-01') & (df.obs_date <= '2026-12-31')]
    df.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(df)} rows, {df.series.nunique()} series')


if __name__ == '__main__':
    main()

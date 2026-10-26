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
import argparse, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
import pandas as pd
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

SERIES = ['DGS10', 'T10Y2Y', 'DTB3', 'ICSA', 'UMCSENT']


def alfred_page(key, sid, offset, limit, vintage_start, vintage_end):
    qs=urllib.parse.urlencode(dict(series_id=sid,api_key=key,file_type='json',
        realtime_start=vintage_start,realtime_end=vintage_end,output_type=1,
        observation_start='2018-01-01',observation_end='2026-12-31',offset=offset,limit=limit))
    req=urllib.request.Request('https://api.stlouisfed.org/fred/series/observations?'+qs,
        headers={'User-Agent':'checklist-engine research'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=180) as response:return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            code=exc.code
            try:
                detail=json.loads(exc.read()).get('error_message','')
            except Exception:detail=''
            detail=str(detail).replace(key,'[REDACTED]')
            detail=re.sub(r'https?://[^\s]+','[URL REDACTED]',detail)[:400]
            if code not in (429,500,502,503,504) or attempt==3:
                raise RuntimeError(f'FRED {sid}: HTTP {code}; request URL and key redacted; {detail}') from None
        except (OSError,ValueError):
            if attempt==3:raise RuntimeError(f'FRED {sid}: transport/JSON failure; request URL and key redacted') from None
        time.sleep(2**attempt)
    raise RuntimeError(f'FRED {sid}: retries exhausted')


def fred_today(now=None):
    # FRED's server day is the St Louis calendar day, which can lag UTC.
    current=now or datetime.now(timezone.utc)
    return current.astimezone(ZoneInfo('America/Chicago')).date().isoformat()


def alfred_observations(key, sid, limit=100000, start_year=2018, end_year=2026, as_of=None):
    # JSON allows at most 2,000 vintage dates per request. Calendar-year
    # intervals have at most 366 dates, including carry-in information known
    # at the interval start. Paginate observations separately in each interval.
    out=[]
    as_of=as_of or fred_today()
    for year in range(start_year,end_year+1):
        start=f'{year}-01-01';end=min(f'{year}-12-31',as_of);offset=0
        if start>end:break
        while True:
            page=alfred_page(key,sid,offset,limit,start,end)
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
        time.sleep(.2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='fred_wide_2020_26.parquet')
    ap.add_argument('--series', default=','.join(SERIES))
    a = ap.parse_args()
    key = os.environ.get('FRED_API_KEY', '')
    if not key:
        sys.exit('BLOCKED_SECRET: FRED_API_KEY not set -- wire-only mode, fetch skipped')
    from pathlib import Path
    report_path=Path(a.out).with_suffix('.source.json')
    report=dict(source='FRED/ALFRED',status='RUNNING',series={})
    rows = []
    for sid in [s.strip() for s in a.series.split(',') if s.strip()]:
        try:
            got = alfred_observations(key, sid)
            report['series'][sid]=dict(status='PASS',rows=len(got))
        except Exception as exc:
            report.update(status='FAIL',error=str(exc))
            report_path.write_text(json.dumps(report,indent=2))
            raise
        rows.extend(got)
        print(sid, len(got), 'vintage observations', flush=True)
        time.sleep(1.5)
    if not rows:
        sys.exit('no observations fetched -- check key/quota')
    df = pd.DataFrame(rows)
    df = df[(df.obs_date >= '2018-01-01') & (df.obs_date <= '2026-12-31')]
    df.to_parquet(a.out, index=False)
    report.update(status='PASS',rows=len(df))
    report_path.write_text(json.dumps(report,indent=2))
    print(f'wrote {a.out}: {len(df)} rows, {df.series.nunique()} series')


if __name__ == '__main__':
    main()

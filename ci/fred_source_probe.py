"""Secret-safe FRED request diagnostics; never print request URLs or credentials."""
import json,os,re,urllib.parse,urllib.request,urllib.error
from pathlib import Path


def probe(key, full):
    params=dict(series_id='DGS10',api_key=key,file_type='json',observation_start='2026-10-01')
    if full:params.update(realtime_start='1900-01-01',realtime_end='9999-12-31',output_type=1,offset=0,limit=100000)
    url='https://api.stlouisfed.org/fred/series/observations?'+urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url,timeout=120) as response:
            payload=json.loads(response.read())
        return dict(status='PASS',count=payload.get('count'),received=len(payload.get('observations',[])))
    except urllib.error.HTTPError as exc:
        try:detail=str(json.loads(exc.read()).get('error_message',''))
        except Exception:detail=''
        detail=detail.replace(key,'[REDACTED]')
        detail=re.sub(r'https?://[^\\s]+','[URL REDACTED]',detail)[:400]
        return dict(status='FAIL',http_status=exc.code,error=detail)
    except Exception:
        return dict(status='FAIL',error='transport/JSON failure; URL and key redacted')


def main():
    key=os.environ.get('FRED_API_KEY','')
    result=dict(source='FRED/ALFRED',source_commit=os.environ.get('GITHUB_SHA'))
    if not key:result.update(status='FAIL',error='FRED_API_KEY secret missing')
    else:
        result['minimal']=probe(key,False)
        if result['minimal']['status']=='PASS':result['all_versions']=probe(key,True)
        result['status']='PASS' if result.get('all_versions',{}).get('status')=='PASS' else 'FAIL'
    Path('FRED_SOURCE_PROBE.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()

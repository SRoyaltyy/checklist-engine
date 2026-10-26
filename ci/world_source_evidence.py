"""Bind real source failures to coverage; never synthesize numeric values."""
import json
from pathlib import Path


def verified_blocker(record):
    return (isinstance(record,dict) and record.get('http_status') in (403,429,500,502,503,504)
        and str(record.get('url','')).startswith('https://data.sec.gov/')
        and bool(record.get('response_excerpt')) and record.get('attempts',0)>=4
        and record.get('request_spacing_seconds',0)>=1 and '@' in record.get('user_agent','')
        and record.get('accept_encoding')=='gzip')


def blocked_reports(reports):
    return bool(reports) and all(report.get('requested',0)>0 and report.get('rows',0)==0
        and not report.get('done',{}) and len(report.get('errors',{}))==report['requested']
        and all(verified_blocker(r) for r in report['errors'].values()) for report in reports)


def collect(directory):
    if not directory:return {}
    reports=[(file.name,json.loads(file.read_text())) for file in sorted(Path(directory).glob('xbrl_shard_*.progress.json'))]
    failures=[dict(ticker=ticker,report=name,**record)
        for name,report in reports for ticker,record in report.get('errors',{}).items()
        if isinstance(record,dict) and verified_blocker(record)]
    # Partial retrieval cannot be hidden behind a whole-source exemption.
    if failures and blocked_reports([r for _,r in reports]):
        reason='SEC companyfacts blocked after identified, paced requests and retries: '+'; '.join(
            f"{r['ticker']} HTTP {r['http_status']} {r['url']}: {r['response_excerpt']}" for r in failures)
        return {item:dict(status='BLOCKED',source='SEC companyfacts',evidence=failures,reason=reason)
                for item in ('I192','I193','I194')}
    return {}

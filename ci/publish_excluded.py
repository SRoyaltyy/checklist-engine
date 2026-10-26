"""Publish one explicit exclusion roster from existing immutable evidence; fetch no new market data."""
import argparse,csv,hashlib,json,os,subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd

def main():
    root=Path('exclusion-evidence');price_file=root/'prices/FULL_PRICE_RECONCILIATION_AUDIT.json'
    audit=json.loads(price_file.read_text());results=audit['results'];universe=set(results)
    if len(universe)!=8727 or audit['source_commit']!='1a822a1b1b96886bba5621f2be1e25709f67a6db':raise ValueError('Unexpected price proof')
    identities_file=root/'identities/SEC_WORLD_IDENTITIES.json'
    if hashlib.sha256(identities_file.read_bytes()).hexdigest()!='0f62ee169a82dcb7fcdd339fd2606c2de6ef41b886c8ea3d253e620578967f25':raise ValueError('Identity evidence changed')
    identities=json.loads(identities_file.read_text());identity_by_ticker={r['ticker']:r for r in identities['records']}
    listing_file=root/'listings/CURRENT_LISTING_CLASSIFICATION.csv'
    listing=pd.read_csv(listing_file,dtype=str,keep_default_na=False)
    if set(listing.ticker)!=universe or listing.ticker.duplicated().any():raise ValueError('Listing proof universe mismatch')
    classification=dict(zip(listing.ticker,listing.classification))
    cutoff='2026-10-23';reasons={};evidence={};codes={}
    def add(ticker,code,reason,url):
        if ticker not in universe:raise ValueError('Exclusion outside original universe '+ticker)
        reasons.setdefault(ticker,set()).add(reason);codes.setdefault(ticker,set()).add(code);evidence.setdefault(ticker,set()).add(url)
    price_url='https://github.com/SRoyaltyy/checklist-engine/actions/runs/40281068048'
    raw_fail=set();short=set();stale=set();zero_volume=set()
    for ticker,record in results.items():
        if record['status']!='PASS':
            raw_fail.add(ticker);add(ticker,'UNRESOLVED_PRICE_BRIDGE',record.get('reason','Unresolved strict price bridge'),price_url)
        if record.get('short_history_all_sessions_exact'):
            short.add(ticker);add(ticker,'FROZEN_OVERLAP_LT_60',f"Only {record['overlap_rows']} frozen/reference sessions overlap; strict minimum is 60. Exact all-available OHLCV match is diagnostic and does not waive that minimum.",price_url)
        last=record.get('supplemental_end',record.get('source_last',''))
        if last and last<cutoff:
            stale.add(ticker);add(ticker,'STALE_LAST_PRICE_SESSION',f"Published price source last session {last}; expected completed session {cutoff}. No forward fill or invented price.",price_url)
        if record.get('all_overlap_volumes_zero'):
            zero_volume.add(ticker);add(ticker,'UNVERIFIABLE_HISTORICAL_VOLUME_BASIS','All frozen-overlap volumes are zero; cannot independently establish a tradable volume basis from this bridge.',price_url)
    if len(raw_fail)!=30 or len(short)!=242 or len(stale)!=19:raise ValueError('Expected edge-case counts changed')
    proof=json.loads((root/'SEC_FULL_SOURCE_PROOF_SUMMARY.json').read_text());quarantined={int(q['cik']) for q in proof['quarantined']}
    quarantine_names=set()
    for ticker,record in identity_by_ticker.items():
        ciks={int(v['cik']) for v in record['candidates']}
        if ciks&quarantined:
            quarantine_names.add(ticker);add(ticker,'QUARANTINED_SEC_IDENTITY','SEC companyfacts omits root CIK1790169. Separate official CIK and exact entity-name binding exists, but identity remains quarantined; exclude rather than remap or spend further repair runs.','https://github.com/SRoyaltyy/checklist-engine/actions/runs/40283469118')
    if not quarantine_names:raise ValueError('Quarantined CIK has no canonical ticker')
    halt_file=root/'halts/nasdaq_halts_2020_2026.parquet';halts=pd.read_parquet(halt_file)
    halts['halt_day']=pd.to_datetime(halts.halt_date,format='%m/%d/%Y',errors='coerce')
    halts['resume_day']=pd.to_datetime(halts.resume_date,format='%m/%d/%Y',errors='coerce')
    halts=halts[halts.symbol.isin(universe)&(halts.halt_day<=pd.Timestamp(cutoff))].sort_values('halt_day')
    halt_names=set()
    for ticker,group in halts.groupby('symbol'):
        row=group.iloc[-1];last=results[ticker].get('supplemental_end',results[ticker].get('source_last',''))
        if (pd.isna(row.resume_day) or row.resume_day>pd.Timestamp(cutoff)) and last and pd.Timestamp(last)<=row.halt_day:
            halt_names.add(ticker);add(ticker,'UNRESOLVED_HALT',f"Published halt {row['reason']} on {str(row.halt_day)[:10]} has no completed resume by {cutoff}, and no observed price session after the halt. Conservative eligibility exclusion.",'https://github.com/SRoyaltyy/checklist-engine/actions/runs/40281391807')
    required=raw_fail|short|stale|quarantine_names
    if not required<=set(reasons):raise ValueError('Required exclusion omitted')
    out=Path('exclusion-publication');out.mkdir(exist_ok=True);rows=[]
    for ticker in sorted(reasons):
        identity=identity_by_ticker.get(ticker,{})
        ciks=sorted({str(v['cik']) for v in identity.get('candidates',[])})
        record=results[ticker]
        rows.append(dict(ticker=ticker,cik='|'.join(ciks),reason='; '.join(sorted(reasons[ticker])),reason_codes='|'.join(sorted(codes[ticker])),scope='candidate_universe',current_listing_classification=classification[ticker],frozen_overlap_rows=record.get('overlap_rows',record.get('diagnostics',{}).get('overlap_rows','')),latest_price_session=record.get('supplemental_end',record.get('source_last','')),as_of_completed_session=cutoff,evidence=' | '.join(sorted(evidence[ticker]))))
    if any(not r['ticker'] or not r['reason'] for r in rows) or len({r['ticker'] for r in rows})!=len(rows):raise ValueError('Missing reason or duplicate name')
    target=out/'EXCLUDED.csv'
    with target.open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    listed_stock={t for t,c in classification.items() if c=='NON_ETF'}
    clean_count=len(universe-set(reasons));listed_excluded=len(listed_stock&set(reasons))
    summary=dict(status='EXCLUSIONS_LOGGED_DOWNLOAD_PAUSED',as_of_completed_session=cutoff,generated_at_hkt=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat(),unique_excluded=len(rows),reason_counts=dict(Counter(code for r in rows for code in r['reason_codes'].split('|'))),original_universe=len(universe),clean_price_inventory=clean_count,clean_price_inventory_pct=100*clean_count/len(universe),current_non_etf_listing_universe=len(listed_stock),excluded_current_non_etf=listed_excluded,clean_current_non_etf_listing_pct=100*(len(listed_stock)-listed_excluded)/len(listed_stock),quarantined_cik1790169_tickers=sorted(quarantine_names),exclusion_list='docs/EXCLUDED.csv',exclusion_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),input_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (price_file,identities_file,listing_file,halt_file)},source_run='https://github.com/SRoyaltyy/checklist-engine/actions/runs/'+os.environ['GITHUB_RUN_ID'],phase2_world_gate='NOT_RUN',tradeable_97pct_gate='NOT_CLAIMED: full point-in-time liquidity/size eligibility and required context still pending',notes=['One row per canonical ticker; reasons merged, no remapping or deletion of raw source evidence.','The 242 short-history cases have fewer than 60 frozen overlap sessions; this is not a claim that their entire current history is shorter than 60 days.','Current non-ETF listing classification is an inventory comparison, not full historical tradeability.','Candidate exclusions do not waive the required industry/sector/index/breadth/macro context blocks.','No new Phase 1 data block download; await James gap-review result in METHODOLOGY section 0b.'])
    (out/'EXCLUSION_SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print('EXCLUSION_SUMMARY',json.dumps(summary),flush=True)
if __name__=='__main__':main()

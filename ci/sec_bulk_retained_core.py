"""Structured SEC bulk transforms; pure helpers also accept synthetic fixtures."""
from datetime import date
from decimal import Decimal
import json
import math
from pathlib import PurePosixPath
import re

QUARANTINED_CIKS = {1790169}
MEMBER = re.compile(r'CIK(\d{10})(-submissions-\d+)?\.json')
FILING_FIELDS = {'accessionNumber':'accession_number', 'filingDate':'filing_date',
    'reportDate':'report_date', 'acceptanceDateTime':'acceptance_datetime',
    'form':'form', 'primaryDocument':'primary_document', 'isXBRL':'is_xbrl',
    'isInlineXBRL':'is_inline_xbrl'}


def cik_number(value):
    if isinstance(value,bool) or not re.fullmatch(r'\d{1,10}',str(value)):
        raise ValueError('invalid SEC CIK')
    result=int(value)
    if result<1:
        raise ValueError('SEC CIK must be positive')
    return result


def live_candidates(tickers,exchanges):
    result={}
    def add(ticker,cik):
        if not isinstance(ticker,str) or not ticker or ticker!=ticker.strip():
            raise ValueError('invalid current ticker key')
        result.setdefault(ticker,set()).add(cik_number(cik))
    if not isinstance(tickers,dict) or not tickers:
        raise ValueError('empty current ticker map')
    for row in tickers.values():
        add(row['ticker'],row['cik_str'])
    fields=exchanges['fields']
    if len(set(fields))!=len(fields) or not {'ticker','cik','exchange'}<=set(fields) or not exchanges['data']:
        raise ValueError('invalid exchange ticker map')
    for values in exchanges['data']:
        if len(values)!=len(fields):
            raise ValueError('exchange ticker columns differ')
        row=dict(zip(fields,values));add(row['ticker'],row['cik'])
    return result


def resolve_identities(records,current):
    rows=[]
    if len({r['ticker'] for r in records})!=len(records):
        raise ValueError('duplicate retained ticker')
    for record in sorted(records,key=lambda r:r['ticker']):
        ticker=record['ticker'];old=set()
        if record['status']=='UNIQUE_CIK':
            if len(record['candidates'])!=1:
                raise ValueError('archived unique identity has multiple candidates')
            candidate=record['candidates'][0]
            if not candidate.get('quarantined') and not candidate.get('quarantined_for_join'):
                old={cik_number(candidate['cik'])}
        live=set(current.get(ticker,set()))
        blocked=(old|live)&QUARANTINED_CIKS
        old-=QUARANTINED_CIKS;live-=QUARANTINED_CIKS
        candidates=old|live
        if record['status']=='QUARANTINED_ISSUER_PRODUCT_ALIAS':
            status='QUARANTINED_ISSUER_PRODUCT_ALIAS';candidates=set();selected=None
        elif old and live and old!=live:
            status='ARCHIVED_CURRENT_CONFLICT';selected=None
        elif len(live)>1:
            status='AMBIGUOUS_CURRENT';selected=None
        elif old:
            status='ARCHIVED_AND_CURRENT_AGREE' if live else 'ARCHIVED_ONLY_CANDIDATE'
            selected=next(iter(old))
        elif len(live)==1:
            status='CURRENT_ONLY_CANDIDATE';selected=next(iter(live))
        else:
            status='INTEGRITY_QUARANTINED_CIK' if blocked else 'NO_CIK';selected=None
        rows.append(dict(ticker=ticker,cik=selected,status=status,candidate_ciks=sorted(candidates),
            withheld_ciks=sorted(blocked),observed_first_filed=record.get('shares_first_filed'),
            observed_last_filed=record.get('shares_last_filed'),
            valid_from=None,valid_to_exclusive=None,historical_join_allowed=False))
    return rows


def members_by_cik(names,selected,kind):
    result={};seen=set()
    for name in names:
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError('unsafe SEC ZIP member')
        match=MEMBER.fullmatch(path.name)
        if not match:
            continue
        cik=int(match[1])
        if cik not in selected:
            continue
        if cik in QUARANTINED_CIKS:
            raise ValueError('integrity-quarantined CIK selected')
        if kind=='companyfacts' and match[2]:
            raise ValueError('unexpected companyfacts history member')
        if path.name in seen:
            raise ValueError('duplicate SEC ZIP member basename')
        seen.add(path.name);result.setdefault(cik,[]).append(name)
    return {c:sorted(v,key=lambda n:('-submissions-' in n,n)) for c,v in result.items()}


def iso_date(value):
    if value in (None,''):
        return None
    if not isinstance(value,str) or date.fromisoformat(value).isoformat()!=value:
        raise ValueError('invalid SEC date key')
    return value


def submission_rows(payload,cik):
    root='filings' in payload
    if root and cik_number(payload['cik'])!=cik:
        raise ValueError('submissions filename/body CIK differs')
    recent=payload['filings']['recent'] if root else payload
    accessions=recent.get('accessionNumber',[])
    if not isinstance(accessions,list):
        raise ValueError('filing accession column must be an array')
    for key in FILING_FIELDS:
        if key in recent and (not isinstance(recent[key],list) or len(recent[key])!=len(accessions)):
            raise ValueError('filing parallel column lengths differ: '+key)
    for i,accession in enumerate(accessions):
        if not isinstance(accession,str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',accession):
            raise ValueError('invalid filing accession identifier')
        row=dict(cik=cik)
        for key,column in FILING_FIELDS.items():
            value=recent[key][i] if key in recent else None
            row[column]=None if value is None or value=='' else str(value)
        for column in ('filing_date','report_date'):
            row[column]=iso_date(row[column])
        # Filing/acceptance dates remain separate from reporting-period dates.
        yield row


def annotate_filing_observations(groups):
    """Preserve each reported record; never choose or combine disputed metadata."""
    rows=[];examples=[]
    counters=dict(distinct_accessions=len(groups),duplicate_accession_observations=0,
                  exact_duplicate_observations=0,accessions_with_conflicting_metadata=0)
    fields=list(FILING_FIELDS.values())
    for accession,observations in sorted(groups.items()):
        values={field:sorted({r[field] for r in observations if r[field] is not None}) for field in fields}
        conflicts=sorted(field for field,v in values.items() if len(v)>1)
        variants={tuple(r[field] for field in fields) for r in observations}
        counters['duplicate_accession_observations']+=len(observations)-1
        counters['exact_duplicate_observations']+=len(observations)-len(variants)
        if conflicts:
            counters['accessions_with_conflicting_metadata']+=1
            if len(examples)<20:
                examples.append(dict(cik=observations[0]['cik'],accession_number=accession,
                    conflict_fields=conflicts,reported_values={field:values[field] for field in conflicts}))
        for original in sorted(observations,key=lambda r:(r['source_member'],r['source_row'])):
            rows.append(dict(original,conflict_fields=conflicts))
    return rows,counters,examples


def entity_row(payload,cik):
    if cik_number(payload['cik'])!=cik:
        raise ValueError('entity filename/body CIK differs')
    return dict(cik=cik,sic=None if payload.get('sic') in (None,'') else int(payload['sic']),
        current_tickers=list(payload.get('tickers') or []),
        current_exchanges=list(payload.get('exchanges') or []),
        state_of_incorporation=payload.get('stateOfIncorporation'),
        identity_scope='CURRENT_ENTITY_METADATA_NOT_HISTORICAL_OWNERSHIP')


def companyfact_rows(payload,cik,counters):
    if not isinstance(payload,dict):raise ValueError('companyfacts member is not an object')
    body_cik=cik_number(payload['cik']) if 'cik' in payload else None
    if body_cik is not None and body_cik!=cik:
        raise ValueError('companyfacts filename/body CIK differs')
    if body_cik is None:
        counters['companyfacts_members_without_body_cik']=counters.get('companyfacts_members_without_body_cik',0)+1
        counters.setdefault('companyfacts_ciks_without_body_cik',[]).append(cik)
    if not payload:
        counters['empty_companyfacts_payloads']=counters.get('empty_companyfacts_payloads',0)+1
        counters.setdefault('empty_companyfacts_ciks',[]).append(cik)
        return
    if not isinstance(payload.get('facts',{}),dict):raise ValueError('companyfacts facts container is not an object')
    sequence=0
    for taxonomy,concepts in payload.get('facts',{}).items():
        for concept,body in concepts.items():
            for unit,values in body.get('units',{}).items():
                for value in values:
                    sequence+=1;counters['source_fact_values']+=1
                    numeric=value.get('val')
                    if isinstance(numeric,bool) or not isinstance(numeric,(int,float,Decimal)):
                        counters['non_numeric_fact_values']+=1;continue
                    exact=numeric if isinstance(numeric,Decimal) else Decimal(str(numeric))
                    if not exact.is_finite():
                        raise ValueError('nonfinite SEC numeric fact')
                    converted=float(exact)
                    representable=math.isfinite(converted)
                    filed=iso_date(value.get('filed'))
                    if filed is None:counters['numeric_facts_without_filed_date']+=1
                    if body_cik is None:
                        counters['fact_rows_without_body_cik']=counters.get('fact_rows_without_body_cik',0)+1
                    yield dict(cik=cik,body_cik=body_cik,
                        cik_evidence='BODY_AND_FILENAME_AGREE' if body_cik is not None else 'FILENAME_ONLY_BODY_CIK_ABSENT',
                        taxonomy=taxonomy,concept=concept,unit=unit,
                        start=iso_date(value.get('start')),end=iso_date(value.get('end')),
                        val_text=str(exact),val_float64=converted if representable else None,
                        float64_exact=representable and Decimal.from_float(converted)==exact,
                        accession_number=value.get('accn'),fiscal_year=value.get('fy'),
                        fiscal_period=value.get('fp'),form=value.get('form'),filed=filed,
                        frame=value.get('frame'),source_sequence=sequence)


def decode_source(raw):
    return json.loads(raw,parse_float=Decimal)

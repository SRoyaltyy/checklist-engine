"""Independent raw-to-row verification. Does not import SEC producer transforms."""
from collections import Counter,defaultdict
from decimal import Decimal
import hashlib
import json
import math

IDENTITY_FIELDS=['ticker','cik','status','candidate_ciks','withheld_ciks',
    'observed_first_filed','observed_last_filed','valid_from','valid_to_exclusive','historical_join_allowed']
FILING_SOURCE={'accessionNumber':'accession_number','filingDate':'filing_date','reportDate':'report_date',
    'acceptanceDateTime':'acceptance_datetime','form':'form','primaryDocument':'primary_document',
    'isXBRL':'is_xbrl','isInlineXBRL':'is_inline_xbrl'}
FIELDS=dict(identity=IDENTITY_FIELDS,
    filings=['cik',*FILING_SOURCE.values(),'source_member','source_row','conflict_fields'],
    entities=['cik','sic','current_tickers','current_exchanges','state_of_incorporation','identity_scope'],
    facts=['cik','taxonomy','concept','unit','start','end','val_text','val_float64','float64_exact',
           'accession_number','fiscal_year','fiscal_period','form','filed','frame','source_sequence'])


def check(condition,message):
    if not condition:raise ValueError(message)


class RowDigests:
    """Hash every ordered field of every row, retaining only a digest per CIK."""
    def __init__(self,kind):
        self.kind=kind;self.hashes={};self.counts=Counter();self.last_cik=None

    def add(self,row):
        check(set(row)==set(FIELDS[self.kind]),'row fields differ: '+self.kind)
        cik=row['cik']
        check(type(cik) is int and cik>0 and cik!=1790169,'invalid/quarantined row CIK')
        check(self.last_cik is None or cik>=self.last_cik,'CIK row order differs')
        self.last_cik=cik
        values=[row[k] for k in FIELDS[self.kind]]
        if self.kind=='facts':
            i=FIELDS['facts'].index('val_float64')
            values[i]=None if values[i] is None else float(values[i]).hex()
        raw=(json.dumps(values,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode()
        self.hashes.setdefault(cik,hashlib.sha256()).update(raw);self.counts[cik]+=1

    def summary(self):
        return {str(c):dict(rows=self.counts[c],sha256=self.hashes[c].hexdigest()) for c in sorted(self.hashes)}


def identities(archived,ticker_map,exchange_map):
    """Reconcile exact keys independently; current candidates are never ownership."""
    current=defaultdict(set)
    for row in ticker_map.values():current[row['ticker']].add(int(row['cik_str']))
    for cells in exchange_map['data']:
        row=dict(zip(exchange_map['fields'],cells));current[row['ticker']].add(int(row['cik']))
    result=[]
    for row in sorted(archived,key=lambda r:r['ticker']):
        old=set()
        if row['status']=='UNIQUE_CIK':
            check(len(row['candidates'])==1,'archived unique candidate count differs')
            candidate=row['candidates'][0]
            if not candidate.get('quarantined') and not candidate.get('quarantined_for_join'):
                old.add(int(candidate['cik']))
        live=current[row['ticker']].copy();withheld=sorted((old|live)&{1790169})
        old.discard(1790169);live.discard(1790169);candidates=sorted(old|live)
        selected=None
        if row['status']=='QUARANTINED_ISSUER_PRODUCT_ALIAS':
            status=row['status'];candidates=[]
        elif old and live and live!=old:status='ARCHIVED_CURRENT_CONFLICT'
        elif len(live)>1:status='AMBIGUOUS_CURRENT'
        elif old:
            status='ARCHIVED_AND_CURRENT_AGREE' if live else 'ARCHIVED_ONLY_CANDIDATE';selected=min(old)
        elif live:status='CURRENT_ONLY_CANDIDATE';selected=min(live)
        else:status='INTEGRITY_QUARANTINED_CIK' if withheld else 'NO_CIK'
        result.append(dict(ticker=row['ticker'],cik=selected,status=status,candidate_ciks=candidates,
            withheld_ciks=withheld,observed_first_filed=row.get('shares_first_filed'),
            observed_last_filed=row.get('shares_last_filed'),valid_from=None,valid_to_exclusive=None,
            historical_join_allowed=False))
    return result


class RawAudit:
    def __init__(self,kind):
        check(kind in ('submissions','companyfacts'),'unknown raw kind')
        self.kind=kind;self.current=None;self.groups=defaultdict(list);self.seen=set()
        self.populated=set();self.dates=[];self.examples=[]
        self.rows=RowDigests('filings' if kind=='submissions' else 'facts')
        self.entities=RowDigests('entities')
        self.counts=dict(source_members=0,distinct_accessions=0,duplicate_accession_observations=0,
            exact_duplicate_observations=0,accessions_with_conflicting_metadata=0,source_fact_values=0,
            non_numeric_fact_values=0,numeric_facts_without_filed_date=0,filings_without_filed_date=0,
            filings_without_acceptance_timestamp=0)

    def add_row(self,row):
        self.rows.add(row);self.populated.add(row['cik'])
        date=row['filing_date' if self.kind=='submissions' else 'filed']
        if date:self.dates=[min([date]+self.dates),max([date]+self.dates)]

    def member(self,cik,name,raw):
        check(self.current is None or cik>=self.current,'raw CIK order differs')
        if cik!=self.current:
            self.finish_cik();self.current=cik
        self.seen.add(cik);self.counts['source_members']+=1
        value=json.loads(raw,parse_float=Decimal)
        if self.kind=='companyfacts':
            check(int(value['cik'])==cik,'facts body CIK differs')
            self.facts(value,cik)
        else:
            if 'filings' in value:
                check(int(value['cik'])==cik,'submissions body CIK differs')
                self.entities.add(dict(cik=cik,sic=int(value['sic']) if value.get('sic') not in (None,'') else None,
                    current_tickers=value.get('tickers') or [],current_exchanges=value.get('exchanges') or [],
                    state_of_incorporation=value.get('stateOfIncorporation'),
                    identity_scope='CURRENT_ENTITY_METADATA_NOT_HISTORICAL_OWNERSHIP'))
                columns=value['filings']['recent']
            else:columns=value
            for i,acc in enumerate(columns.get('accessionNumber',[])):
                row=dict(cik=cik,source_member=name,source_row=i+1)
                for source,target in FILING_SOURCE.items():
                    cell=columns[source][i] if source in columns else None
                    row[target]=None if cell is None or cell=='' else str(cell)
                self.groups[acc].append(row)

    def finish_cik(self):
        for acc,rows in sorted(self.groups.items()):
            self.counts['distinct_accessions']+=1
            self.counts['duplicate_accession_observations']+=len(rows)-1
            variants={tuple(r[k] for k in FILING_SOURCE.values()) for r in rows}
            self.counts['exact_duplicate_observations']+=len(rows)-len(variants)
            values={k:sorted({r[k] for r in rows if r[k] is not None}) for k in FILING_SOURCE.values()}
            conflicts=sorted(k for k,v in values.items() if len(v)>1)
            if conflicts:
                self.counts['accessions_with_conflicting_metadata']+=1
                if len(self.examples)<20:self.examples.append(dict(cik=rows[0]['cik'],accession_number=acc,
                    conflict_fields=conflicts,reported_values={k:values[k] for k in conflicts}))
            for row in sorted(rows,key=lambda r:(r['source_member'],r['source_row'])):
                self.counts['filings_without_filed_date']+=row['filing_date'] is None
                self.counts['filings_without_acceptance_timestamp']+=row['acceptance_datetime'] is None
                self.add_row(dict(row,conflict_fields=conflicts))
        self.groups.clear()

    def facts(self,payload,cik):
        sequence=0
        for taxonomy,concepts in payload.get('facts',{}).items():
            for concept,body in concepts.items():
                for unit,items in body.get('units',{}).items():
                    for item in items:
                        sequence+=1;self.counts['source_fact_values']+=1
                        number=item.get('val')
                        if type(number) not in (int,float,Decimal):
                            self.counts['non_numeric_fact_values']+=1;continue
                        number=number if isinstance(number,Decimal) else Decimal(str(number))
                        check(number.is_finite(),'nonfinite raw fact')
                        floating=float(number);finite=math.isfinite(floating)
                        filed=item.get('filed') or None
                        self.counts['numeric_facts_without_filed_date']+=filed is None
                        self.add_row(dict(cik=cik,taxonomy=taxonomy,concept=concept,unit=unit,
                            start=item.get('start') or None,end=item.get('end') or None,val_text=str(number),
                            val_float64=floating if finite else None,
                            float64_exact=finite and Decimal.from_float(floating)==number,
                            accession_number=item.get('accn'),fiscal_year=item.get('fy'),
                            fiscal_period=item.get('fp'),form=item.get('form'),filed=filed,
                            frame=item.get('frame'),source_sequence=sequence))

    def finish(self,selected):
        self.finish_cik()
        return dict(status='PASS_RETAINED_SOURCE_EXTRACTION',rows=sum(self.rows.counts.values()),
            entity_rows=sum(self.entities.counts.values()) if self.kind=='submissions' else None,
            archive_ciks=len(self.seen),populated_ciks=sorted(self.populated),
            missing_archive_ciks=sorted(set(selected)-self.seen),
            ciks_without_output_rows=sorted(self.seen-self.populated),
            filing_record_model='SOURCE_OBSERVATIONS_WITH_CONFLICT_FIELDS' if self.kind=='submissions' else None,
            conflict_examples=self.examples,first_filed_date=min(self.dates) if self.dates else None,
            last_filed_date=max(self.dates) if self.dates else None,**self.counts)

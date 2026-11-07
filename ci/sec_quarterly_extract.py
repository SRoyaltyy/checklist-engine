"""Stream fixed quarterly source fields into immutable parquet parts on runners."""
from collections import Counter
import hashlib
from pathlib import Path
import re
import zipfile

from ci.sec_quarterly_core import fixed_rows,table_members
from ci.sec_quarterly_fields import TABLES,filing_date_iso,value_unit_13f


COMMON=['source_window','source_zip_name','source_member','source_row','parent_link_status',
        'filing_date_raw','filing_date_iso','filing_date_status','period_of_report_raw','document_type']
SPECIFIC=dict(form345=['issuer_cik_raw','issuer_cik','issuer_cik_status','retained_retrieval_candidate'],
    form13f=['filing_manager_cik_raw','filing_manager_cik','filing_manager_cik_status','reported_market_value_unit'])


def identifier(value):
    if value in (None,''):return None,'MISSING_SOURCE_CIK'
    if not re.fullmatch(r'[0-9]{1,10}',value) or int(value)<1:return None,'INVALID_SOURCE_CIK'
    return int(value),'SOURCE_IDENTIFIER_NOT_HISTORICAL_OWNERSHIP'


def annotate(row,parent,kind,table,window,zip_name,retained_ciks):
    result=dict(row,source_window=window,source_zip_name=zip_name)
    result['parent_link_status']='SELF_SUBMISSION' if table=='SUBMISSION' else (
        'MATCHED_SUBMISSION' if parent is not None else 'SOURCE_SUBMISSION_MISSING')
    parent={} if parent is None else parent
    filed=parent.get('FILING_DATE');result['filing_date_raw']=filed
    try:parsed=filing_date_iso(filed)
    except ValueError:parsed=None;status='INVALID_SOURCE_DATE'
    else:status='KNOWN_SOURCE_DATE' if parsed else 'MISSING_SOURCE_DATE'
    result.update(filing_date_iso=parsed,filing_date_status=status,
        period_of_report_raw=parent.get('PERIOD_OF_REPORT' if kind=='form345' else 'PERIODOFREPORT'),
        document_type=parent.get('DOCUMENT_TYPE' if kind=='form345' else 'SUBMISSIONTYPE'))
    if kind=='form345':
        raw=parent.get('ISSUERCIK');cik,cik_status=identifier(raw)
        result.update(issuer_cik_raw=raw,issuer_cik=cik,issuer_cik_status=cik_status,
                      retained_retrieval_candidate=cik in retained_ciks if cik is not None else None)
    else:
        raw=parent.get('CIK');cik,cik_status=identifier(raw)
        result.update(filing_manager_cik_raw=raw,filing_manager_cik=cik,filing_manager_cik_status=cik_status,
            reported_market_value_unit=value_unit_13f(parsed) if parsed else 'UNKNOWN_FILING_DATE')
    return result


def schema(kind,table):
    import pyarrow as pa
    names=TABLES[kind][table]['columns']+COMMON+SPECIFIC[kind]
    types={name:pa.string() for name in names}
    types['source_row']=pa.int64()
    types['issuer_cik' if kind=='form345' else 'filing_manager_cik']=pa.int64()
    if kind=='form345':types['retained_retrieval_candidate']=pa.bool_()
    return pa.schema([(name,types[name]) for name in names])


class FixedSink:
    def __init__(self,publisher,kind,table,window,source_zip,part_rows=500000):
        self.publisher=publisher;self.kind=kind;self.table=table;self.window=window;self.source_zip=source_zip
        self.schema=schema(kind,table);self.part_rows=part_rows;self.writer=None;self.part=0;self.rows=0;self.total=0
        self.ciks=set();self.parent_failures=0

    def write(self,rows):
        import pyarrow as pa
        import pyarrow.parquet as pq
        if not rows:return
        if self.writer is None:
            safe=re.sub(r'[^A-Za-z0-9_-]','_',self.window)
            self.path=self.publisher.root/f'sec_{self.kind}_{safe}_{self.table.lower()}-{self.part:05d}.parquet'
            self.writer=pq.ParquetWriter(self.path,self.schema,compression='zstd')
        self.writer.write_table(pa.Table.from_pylist(rows,schema=self.schema))
        key='issuer_cik' if self.kind=='form345' else 'filing_manager_cik'
        self.ciks.update(r[key] for r in rows if r[key] is not None)
        self.parent_failures+=sum(r['parent_link_status']=='SOURCE_SUBMISSION_MISSING' for r in rows)
        self.rows+=len(rows);self.total+=len(rows)
        if self.rows>=self.part_rows:self.close()

    def close(self):
        import pyarrow.parquet as pq
        if self.writer is None:return
        self.writer.close();self.writer=None
        key='issuer_cik' if self.kind=='form345' else 'filing_manager_cik';actual=set()
        with pq.ParquetFile(self.path) as file:
            if not file.schema_arrow.equals(self.schema) or file.metadata.num_rows!=self.rows:
                raise ValueError('actual quarterly parquet schema/row count differs')
            for batch in file.iter_batches(batch_size=100000,columns=[key]):
                actual.update(v for v in batch.column(0).to_pylist() if v is not None)
            if actual!=self.ciks:raise ValueError('actual quarterly parquet source CIKs differ')
            schema_sha=hashlib.sha256(str(file.schema_arrow).encode()).hexdigest()
        self.publisher.emit(self.path,'fixed_source_parquet',rows=self.rows,source_window=self.window,
            source_zip=self.source_zip,table=self.table,source_cik_field=key,source_ciks=sorted(actual),
            schema_sha256=schema_sha,parent_link_failures=self.parent_failures)
        self.part+=1;self.rows=0;self.ciks=set();self.parent_failures=0

    def abort(self):
        if self.writer is not None:
            self.writer.close();self.writer=None;self.path.unlink(missing_ok=True)


def extract_zip(path,kind,window,publisher,retained_ciks):
    """No stock-date join, issuer inference, owner collapse or financial coercion."""
    report=dict(kind=kind,source_zip=path.name,source_window=window,tables={},absent_tables=[],
        excluded_tables=[],scoring_gate='CLOSED',historical_ticker_ownership='NOT_PROVEN')
    with zipfile.ZipFile(path) as archive:
        members=table_members(archive)
        if 'SUBMISSION' not in members:raise ValueError('SEC quarterly ZIP lacks SUBMISSION table')
        parents={};parent_meta={};spec=TABLES[kind]['SUBMISSION']
        for row in fixed_rows(archive,members['SUBMISSION'],spec['columns'],spec['required'],parent_meta):
            accession=row['ACCESSION_NUMBER']
            if not accession or accession in parents:raise ValueError('missing/duplicate source submission accession')
            parents[accession]=row
        report['source_submissions']=len(parents)
        report['excluded_tables']=sorted(set(members)-set(TABLES[kind]))
        for table,spec in TABLES[kind].items():
            if table not in members:report['absent_tables'].append(table);continue
            metadata={};counts=Counter();ciks=set();filed=[];sink=FixedSink(publisher,kind,table,window,path.name)
            try:
                batch=[]
                for row in fixed_rows(archive,members[table],spec['columns'],spec['required'],metadata):
                    parent=row if table=='SUBMISSION' else parents.get(row['ACCESSION_NUMBER'])
                    row=annotate(row,parent,kind,table,window,path.name,retained_ciks)
                    counts[row['parent_link_status']]+=1;counts[row['filing_date_status']]+=1
                    if kind=='form345':
                        if row['issuer_cik'] is not None:ciks.add(row['issuer_cik'])
                        counts['retained_retrieval_rows']+=row['retained_retrieval_candidate'] is True
                    if row['filing_date_iso']:
                        date=row['filing_date_iso'];filed=[min([date]+filed),max([date]+filed)]
                    batch.append(row)
                    if len(batch)>=50000:sink.write(batch);batch=[]
                sink.write(batch);sink.close()
                report['tables'][table]=dict(metadata,output_rows=sink.total,counts=dict(counts),
                    retained_issuer_ciks=sorted(ciks&set(retained_ciks)),
                    first_filed_date=min(filed) if filed else None,last_filed_date=max(filed) if filed else None)
            finally:sink.abort()
    report['status']='PASS_FIXED_SOURCE_FIELDS_NOT_A_STOCK_DATE_JOIN'
    return report

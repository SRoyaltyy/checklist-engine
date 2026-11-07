"""Independent fixed-field contract and raw reconstruction; no producer imports."""
from collections import Counter
import csv
from datetime import date,datetime
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
import zipfile

FIELDS={'form345':{
 'SUBMISSION':'ACCESSION_NUMBER FILING_DATE DOCUMENT_TYPE ISSUERCIK PERIOD_OF_REPORT DATE_OF_ORIG_SUB NO_SECURITIES_OWNED NOT_SUBJECT_SEC16 FORM3_HOLDINGS_REPORTED FORM4_TRANS_REPORTED ISSUERTRADINGSYMBOL AFF10B5ONE',
 'REPORTINGOWNER':'ACCESSION_NUMBER RPTOWNERCIK RPTOWNER_RELATIONSHIP',
 'NONDERIV_TRANS':'ACCESSION_NUMBER NONDERIV_TRANS_SK TRANS_DATE TRANS_ACQUIRED_DISP_CD TRANS_FORM_TYPE TRANS_CODE EQUITY_SWAP_INVOLVED TRANS_TIMELINESS TRANS_SHARES TRANS_PRICEPERSHARE DEEMED_EXECUTION_DATE SHRS_OWND_FOLWNG_TRANS VALU_OWND_FOLWNG_TRANS DIRECT_INDIRECT_OWNERSHIP',
 'DERIV_TRANS':'ACCESSION_NUMBER DERIV_TRANS_SK TRANS_DATE TRANS_ACQUIRED_DISP_CD TRANS_FORM_TYPE TRANS_CODE EQUITY_SWAP_INVOLVED TRANS_TIMELINESS TRANS_SHARES TRANS_PRICEPERSHARE DEEMED_EXECUTION_DATE SHRS_OWND_FOLWNG_TRANS VALU_OWND_FOLWNG_TRANS DIRECT_INDIRECT_OWNERSHIP CONV_EXERCISE_PRICE TRANS_TOTAL_VALUE EXCERCISE_DATE EXPIRATION_DATE UNDLYNG_SEC_SHARES UNDLYNG_SEC_VALUE',
 'NONDERIV_HOLDING':'ACCESSION_NUMBER NONDERIV_HOLDING_SK TRANS_FORM_TYPE SHRS_OWND_FOLWNG_TRANS VALU_OWND_FOLWNG_TRANS DIRECT_INDIRECT_OWNERSHIP',
 'DERIV_HOLDING':'ACCESSION_NUMBER DERIV_HOLDING_SK TRANS_FORM_TYPE CONV_EXERCISE_PRICE EXERCISE_DATE EXPIRATION_DATE UNDLYNG_SEC_SHARES UNDLYNG_SEC_VALUE SHRS_OWND_FOLWNG_TRANS VALU_OWND_FOLWNG_TRANS DIRECT_INDIRECT_OWNERSHIP',
},'form13f':{
 'SUBMISSION':'ACCESSION_NUMBER FILING_DATE SUBMISSIONTYPE CIK PERIODOFREPORT',
 'COVERPAGE':'ACCESSION_NUMBER REPORTCALENDARORQUARTER ISAMENDMENT AMENDMENTNO AMENDMENTTYPE CONFDENIEDEXPIRED DATEDENIEDEXPIRED DATEREPORTED REASONFORNONCONFIDENTIALITY REPORTTYPE FORM13FFILENUMBER CRDNUMBER SECFILENUMBER PROVIDEINFOFORINSTRUCTION5',
 'OTHERMANAGER':'ACCESSION_NUMBER OTHERMANAGER_SK CIK FORM13FFILENUMBER CRDNUMBER SECFILENUMBER',
 'SUMMARYPAGE':'ACCESSION_NUMBER OTHERINCLUDEDMANAGERSCOUNT TABLEENTRYTOTAL TABLEVALUETOTAL ISCONFIDENTIALOMITTED',
 'OTHERMANAGER2':'ACCESSION_NUMBER SEQUENCENUMBER CIK FORM13FFILENUMBER CRDNUMBER SECFILENUMBER',
 'INFOTABLE':'ACCESSION_NUMBER INFOTABLE_SK CUSIP VALUE SSHPRNAMT SSHPRNAMTTYPE FIGI PUTCALL INVESTMENTDISCRETION OTHERMANAGER VOTING_AUTH_SOLE VOTING_AUTH_SHARED VOTING_AUTH_NONE',
}}
FIELDS={kind:{table:columns.split() for table,columns in tables.items()} for kind,tables in FIELDS.items()}
COMMON='source_window source_zip_name source_member source_row parent_link_status filing_date_raw filing_date_iso filing_date_status period_of_report_raw document_type'.split()
EXTRA={'form345':'issuer_cik_raw issuer_cik issuer_cik_status retained_retrieval_candidate'.split(),
       'form13f':'filing_manager_cik_raw filing_manager_cik filing_manager_cik_status reported_market_value_unit'.split()}


def require(condition,message):
    if not condition:raise ValueError(message)


def columns(kind,table):return FIELDS[kind][table]+COMMON+EXTRA[kind]


class RowHash:
    def __init__(self):self.hash=hashlib.sha256();self.rows=0
    def add(self,values):
        self.hash.update((json.dumps(values,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode());self.rows+=1
    def result(self):return dict(rows=self.rows,sha256=self.hash.hexdigest())


def source_cik(raw):
    if raw is None or raw=='':return None,'MISSING_SOURCE_CIK'
    if not re.fullmatch('[0-9]{1,10}',raw) or int(raw)==0:return None,'INVALID_SOURCE_CIK'
    return int(raw),'SOURCE_IDENTIFIER_NOT_HISTORICAL_OWNERSHIP'


def parent_context(row,kind,selected):
    raw=row.get('FILING_DATE');parsed=None
    if raw in (None,''):status='MISSING_SOURCE_DATE'
    else:
        try:
            if re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}',raw):parsed=date.fromisoformat(raw).isoformat()
            elif re.fullmatch('[0-9]{2}-[A-Za-z]{3}-[0-9]{4}',raw):parsed=datetime.strptime(raw,'%d-%b-%Y').date().isoformat()
            else:raise ValueError('unrecognized raw date')
        except ValueError:status='INVALID_SOURCE_DATE'
        else:status='KNOWN_SOURCE_DATE'
    period=row.get('PERIOD_OF_REPORT' if kind=='form345' else 'PERIODOFREPORT')
    document=row.get('DOCUMENT_TYPE' if kind=='form345' else 'SUBMISSIONTYPE')
    cik_raw=row.get('ISSUERCIK' if kind=='form345' else 'CIK');cik,cik_status=source_cik(cik_raw)
    if kind=='form345':extra=[cik_raw,cik,cik_status,cik in selected if cik is not None else None]
    else:extra=[cik_raw,cik,cik_status,'UNKNOWN_FILING_DATE' if parsed is None else ('USD' if parsed>='2023-01-03' else 'USD_THOUSANDS')]
    return [raw,parsed,status,period,document],extra


def inventory(archive):
    tables={}
    for info in archive.infolist():
        path=PurePosixPath(info.filename)
        require(not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename,'unsafe quarterly raw member')
        require(not info.flag_bits&1,'encrypted quarterly raw member')
        if not info.is_dir() and path.suffix.lower() in ('.txt','.tsv'):
            name=path.stem.upper();require(name not in tables,'duplicate quarterly raw table');tables[name]=info
    return tables


def rows(archive,member,metadata):
    with archive.open(member) as binary,io.TextIOWrapper(binary,encoding='utf-8-sig',newline='') as text:
        reader=csv.reader(text,delimiter='\t',quoting=csv.QUOTE_NONE,strict=True)
        header=next(reader);require(len(set(header))==len(header) and all(header),'duplicate/blank raw columns')
        metadata.update(source_columns=header,source_member=member.filename,rows=0)
        for index,values in enumerate(reader,1):
            require(len(values)==len(header),f'raw TSV width differs at source row {index}')
            metadata['rows']+=1
            yield dict(zip(header,(None if v=='' else v for v in values))),index


def raw_window(path,kind,window,selected):
    hashes={};report=dict(kind=kind,source_zip=path.name,source_window=window,tables={},absent_tables=[],
        excluded_tables=[],scoring_gate='CLOSED',historical_ticker_ownership='NOT_PROVEN')
    with zipfile.ZipFile(path) as archive:
        members=inventory(archive);require('SUBMISSION' in members,'raw source lacks SUBMISSION')
        parents={};meta={}
        for row,index in rows(archive,members['SUBMISSION'],meta):
            accession=row.get('ACCESSION_NUMBER');require(bool(accession) and accession not in parents,'missing/duplicate raw parent key')
            parents[accession]=parent_context(row,kind,selected)
        report['source_submissions']=len(parents);report['excluded_tables']=sorted(set(members)-set(FIELDS[kind]))
        for table,fields in FIELDS[kind].items():
            if table not in members:report['absent_tables'].append(table);continue
            meta={};counts=Counter();ciks=set();dates=[];hashes[table]=RowHash()
            for row,index in rows(archive,members[table],meta):
                context=parents.get(row.get('ACCESSION_NUMBER'));known=context is not None
                if context is None:context=parent_context({},kind,selected)
                common,extra=context
                link='SELF_SUBMISSION' if table=='SUBMISSION' else ('MATCHED_SUBMISSION' if known else 'SOURCE_SUBMISSION_MISSING')
                values=[row.get(k) for k in fields]+[window,path.name,members[table].filename,index,link]+common+extra
                hashes[table].add(values);counts[link]+=1;counts[common[2]]+=1
                if kind=='form345':
                    if extra[1] is not None:ciks.add(extra[1])
                    counts['retained_retrieval_rows']+=extra[3] is True
                if common[1]:dates=[min([common[1]]+dates),max([common[1]]+dates)]
            header=meta['source_columns']
            report['tables'][table]=dict(meta,selected_columns=[f for f in fields if f in header],
                optional_columns_absent=sorted(set(fields)-set(header)),output_rows=hashes[table].rows,
                counts=dict(counts),retained_issuer_ciks=sorted(ciks&set(selected)),
                first_filed_date=min(dates) if dates else None,last_filed_date=max(dates) if dates else None)
    report['status']='PASS_FIXED_SOURCE_FIELDS_NOT_A_STOCK_DATE_JOIN'
    return report,{table:value.result() for table,value in hashes.items()}

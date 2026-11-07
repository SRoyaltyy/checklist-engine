"""Fixed-cell selections, based on SEC dataset manuals; no prose-derived features.

Primary schema references:
https://www.sec.gov/files/insider_transactions_readme.pdf
https://www.sec.gov/files/form_13f_readme.pdf
Actual archived headers remain authoritative and are checked before extraction.
"""
from datetime import date
import re
from ci.sec_quarterly_core import MONTHS


def fields(required,optional=()):
    return dict(required=list(required),columns=list(dict.fromkeys([*required,*optional])))


TRANSACTION=['TRANS_FORM_TYPE','TRANS_CODE','EQUITY_SWAP_INVOLVED','TRANS_TIMELINESS',
    'TRANS_SHARES','TRANS_PRICEPERSHARE','DEEMED_EXECUTION_DATE','SHRS_OWND_FOLWNG_TRANS',
    'VALU_OWND_FOLWNG_TRANS','DIRECT_INDIRECT_OWNERSHIP']
DERIVATIVE=['CONV_EXERCISE_PRICE','TRANS_TOTAL_VALUE','EXCERCISE_DATE','EXPIRATION_DATE',
            'UNDLYNG_SEC_SHARES','UNDLYNG_SEC_VALUE']
TABLES=dict(form345={
    'SUBMISSION':fields(['ACCESSION_NUMBER','FILING_DATE','DOCUMENT_TYPE','ISSUERCIK'],
        ['PERIOD_OF_REPORT','DATE_OF_ORIG_SUB','NO_SECURITIES_OWNED','NOT_SUBJECT_SEC16',
         'FORM3_HOLDING_REPORTED','FORM4_TRANS_REPORTED','ISSUERTRADINGSYMBOL','AFF10B5ONE']),
    'REPORTINGOWNER':fields(['ACCESSION_NUMBER','RPTOWNERCIK','RPTOWNER_RELATIONSHIP']),
    'NONDERIV_TRANS':fields(['ACCESSION_NUMBER','NONDERIV_TRANS_SK','TRANS_DATE','TRANS_ACQUIRED_DISP_CD'],TRANSACTION),
    'DERIV_TRANS':fields(['ACCESSION_NUMBER','DERIV_TRANS_SK','TRANS_DATE','TRANS_ACQUIRED_DISP_CD'],TRANSACTION+DERIVATIVE),
    'NONDERIV_HOLDING':fields(['ACCESSION_NUMBER','NONDERIV_HOLDING_SK'],
        ['TRANS_FORM_TYPE','SHRS_OWND_FOLWNG_TRANS','VALU_OWND_FOLWNG_TRANS','DIRECT_INDIRECT_OWNERSHIP']),
    'DERIV_HOLDING':fields(['ACCESSION_NUMBER','DERIV_HOLDING_SK'],
        ['TRANS_FORM_TYPE','CONV_EXERCISE_PRICE','EXCERCISE_DATE','EXPIRATION_DATE',
         'UNDLYNG_SEC_SHARES','UNDLYNG_SEC_VALUE','SHRS_OWND_FOLWNG_TRANS','VALU_OWND_FOLWNG_TRANS',
         'DIRECT_INDIRECT_OWNERSHIP']),
},form13f={
    'SUBMISSION':fields(['ACCESSION_NUMBER','FILING_DATE','SUBMISSIONTYPE','CIK','PERIODOFREPORT']),
    'COVERPAGE':fields(['ACCESSION_NUMBER'],['REPORTCALENDARORQUARTER','ISAMENDMENT','AMENDMENTNO','AMENDMENTTYPE',
        'CONFDENIEDEXPIRED','DATEDENIEDEXPIRED','DATEREPORTED','REASONFORNONCONFIDENTIALITY','REPORTTYPE',
        'FORM13FFILENUMBER','CRDNUMBER','SECFILENUMBER','PROVIDEINFOFORINSTRUCTION5']),
    'OTHERMANAGER':fields(['ACCESSION_NUMBER','OTHERMANAGER_SK'],['CIK','FORM13FFILENUMBER','CRDNUMBER','SECFILENUMBER']),
    'SUMMARYPAGE':fields(['ACCESSION_NUMBER'],['OTHERINCLUDEDMANAGERSCOUNT','TABLEENTRYTOTAL','TABLEVALUETOTAL','ISCONFIDENTIALOMITTED']),
    'OTHERMANAGER2':fields(['ACCESSION_NUMBER','SEQUENCENUMBER'],['CIK','FORM13FFILENUMBER','CRDNUMBER','SECFILENUMBER']),
    'INFOTABLE':fields(['ACCESSION_NUMBER','INFOTABLE_SK','CUSIP','VALUE','SSHPRNAMT','SSHPRNAMTTYPE'],
        ['FIGI','PUTCALL','INVESTMENTDISCRETION','OTHERMANAGER','VOTING_AUTH_SOLE','VOTING_AUTH_SHARED','VOTING_AUTH_NONE']),
})


def filing_date_iso(value):
    if value in (None,''):return None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return date.fromisoformat(value).isoformat()
    match=re.fullmatch(r'(\d{2})-([A-Za-z]{3})-(\d{4})',value)
    if not match or match[2].lower() not in MONTHS:raise ValueError('unrecognized SEC filing date format')
    return date(int(match[3]),MONTHS[match[2].lower()],int(match[1])).isoformat()


def value_unit_13f(filing_date):
    parsed=filing_date_iso(filing_date)
    if parsed is None:return 'UNKNOWN_FILING_DATE'
    return 'USD' if parsed>='2023-01-03' else 'USD_THOUSANDS'

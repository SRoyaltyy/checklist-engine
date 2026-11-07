"""Strict source catalog/TSV readers for fixed-field quarterly SEC acquisition."""
import csv
from datetime import date
from html.parser import HTMLParser
import io
from pathlib import PurePosixPath
import re
from urllib.parse import urljoin,urlsplit

PAGES=dict(form345='https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets',
           form13f='https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets')
MONTHS={m:i+1 for i,m in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])}


class Links(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            for key,value in attrs:
                if key=='href' and value:self.urls.append(value)


def filename_label(name,kind):
    """Quarter labels are not inferred actual filing-date bounds."""
    match=re.fullmatch(r'(20\d{2})q([1-4])_'+kind+r'\.zip',name,re.IGNORECASE)
    if match:
        year,quarter=map(int,match.groups())
        return dict(label=f'{year}Q{quarter}',nominal_year=year,nominal_quarter=quarter,
            filename_start_date=None,filename_end_date=None,sort_key=date(year,3*quarter-2,1))
    match=re.fullmatch(r'(\d{2})([a-z]{3})(20\d{2})-(\d{2})([a-z]{3})(20\d{2})_'+kind+r'\.zip',name,re.IGNORECASE)
    if not match:raise ValueError('unrecognized published SEC dataset filename: '+name)
    d1,m1,y1,d2,m2,y2=match.groups()
    try:
        start=date(int(y1),MONTHS[m1.lower()],int(d1));end=date(int(y2),MONTHS[m2.lower()],int(d2))
    except (ValueError,KeyError):raise ValueError('invalid SEC filename date range') from None
    if end<start or (end-start).days>366:raise ValueError('invalid SEC source window length')
    return dict(label=f'{start.isoformat()}_{end.isoformat()}',nominal_year=None,nominal_quarter=None,
        filename_start_date=start.isoformat(),filename_end_date=end.isoformat(),sort_key=start)


def source_catalog(html,kind,start_year=2020,end_year=None):
    if kind not in PAGES:raise ValueError('unknown SEC structured dataset')
    end_year=date.today().year if end_year is None else end_year
    parser=Links();parser.feed(html);result={};names={}
    for link in parser.urls:
        url=urljoin(PAGES[kind],link);parts=urlsplit(url)
        if parts.scheme!='https' or parts.hostname not in ('sec.gov','www.sec.gov'):continue
        name=PurePosixPath(parts.path).name
        if not name.lower().endswith('_'+kind+'.zip'):continue
        if parts.username or parts.password or parts.port not in (None,443) or parts.query or parts.fragment:
            raise ValueError('unexpected official dataset URL credentials/port/query/fragment')
        if '..' in PurePosixPath(parts.path).parts or '\\' in parts.path:raise ValueError('unsafe official ZIP path')
        label=filename_label(name,kind)
        years=[label['nominal_year']] if label['nominal_year'] else [int(label[k][:4]) for k in ('filename_start_date','filename_end_date')]
        if max(years)<start_year or min(years)>end_year:continue
        if name.lower() in names and names[name.lower()]!=url:
            raise ValueError('ambiguous duplicate ZIP basename in official source index: '+name)
        names[name.lower()]=url
        result[url]=dict(url=url,name=name,**label)
    if not result:raise ValueError('official index has no requested structured sources')
    ordered=sorted(result.values(),key=lambda r:(r['sort_key'],r['name']))
    for row in ordered:row.pop('sort_key')
    return ordered


def table_members(archive):
    tables={}
    for info in archive.infolist():
        path=PurePosixPath(info.filename)
        if path.is_absolute() or '..' in path.parts or '\\' in info.filename:
            raise ValueError('unsafe quarterly SEC ZIP member')
        if info.flag_bits&1:raise ValueError('encrypted SEC source member')
        if info.is_dir() or path.suffix.lower() not in ('.tsv','.txt'):continue
        stem=path.stem.upper()
        if stem in tables:raise ValueError('duplicate quarterly SEC table basename: '+stem)
        tables[stem]=info
    return tables


def fixed_rows(archive,member,columns,required,metadata):
    """Stream exact cells, rejecting ragged rows; prose columns never enter output."""
    if not set(required)<=set(columns) or len(columns)!=len(set(columns)):
        raise ValueError('invalid fixed field selection')
    with archive.open(member) as binary,io.TextIOWrapper(binary,encoding='utf-8-sig',newline='') as text:
        reader=csv.reader(text,delimiter='\t',quoting=csv.QUOTE_NONE,strict=True)
        try:header=next(reader)
        except StopIteration:raise ValueError('empty SEC source table') from None
        if len(header)!=len(set(header)) or any(not c for c in header):raise ValueError('invalid/duplicate SEC column header')
        if 'source_member' in header or 'source_row' in header:raise ValueError('reserved source provenance column in SEC table')
        selected=[c for c in columns if c in header]
        metadata.update(source_member=member.filename,source_columns=header,selected_columns=selected,
                        optional_columns_absent=sorted(set(columns)-set(header)),rows=0)
        missing=sorted(set(required)-set(header))
        if missing:raise ValueError('required SEC source columns absent: '+','.join(missing))
        positions=[header.index(c) for c in selected]
        for index,cells in enumerate(reader,1):
            if len(cells)!=len(header):
                raise ValueError(f'SEC ragged TSV row {index}: expected {len(header)} cells, received {len(cells)}')
            metadata['rows']+=1
            yield dict(zip(selected,(None if cells[i]=='' else cells[i] for i in positions)),
                       source_member=member.filename,source_row=index)

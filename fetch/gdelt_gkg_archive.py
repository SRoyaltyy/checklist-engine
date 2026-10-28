"""Read hash-verified GKG 2.1 archives as counts/tone only, never article text."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

CATALOG='https://data.gdeltproject.org/gdeltv2/masterfilelist.txt'
BASE='https://data.gdeltproject.org/gdeltv2/'
FORMAT=re.compile(r'/gdeltv2/(\d{14})\.gkg\.csv\.zip')


def checked_stamp(value):
    if not re.fullmatch(r'\d{14}',value):raise ValueError('GKG batch timestamp must have 14 digits')
    date=datetime.strptime(value,'%Y%m%d%H%M%S')
    if date.second or date.minute%15:raise ValueError('GKG batch must be a 15-minute boundary')
    return date.replace(tzinfo=timezone.utc)


def select_catalog(stream,stamps,max_bytes=180000000):
    """One bounded catalog request; keep complete byte hash and exact receipts."""
    wanted=set(stamps)
    for stamp in wanted:checked_stamp(stamp)
    selected={};count=0;digest=hashlib.sha256();lines=0;markers=0;blanks=0
    while True:
        raw=stream.readline(4097)
        if not raw:break
        count+=len(raw);lines+=1;digest.update(raw)
        if count>max_bytes or len(raw)>4096:raise ValueError('GKG catalog exceeds bounded capture')
        fields=raw.decode('ascii').split()
        if not fields:blanks+=1;continue
        if fields in (['http://data.gdeltproject.org/gdeltv2/'],['https://data.gdeltproject.org/gdeltv2/']):
            markers+=1;continue
        if len(fields)!=3:raise ValueError('GKG catalog line schema differs')
        url=urllib.parse.urlsplit(fields[2]);match=FORMAT.fullmatch(url.path)
        if not match or match[1] not in wanted:continue
        if url.hostname!='data.gdeltproject.org' or url.scheme not in ('http','https') or url.query or url.fragment or url.port:
            raise ValueError('GKG catalog archive URL outside official source')
        if not fields[0].isdigit() or not re.fullmatch('[0-9a-f]{1,32}',fields[1]):
            raise ValueError('GKG catalog size/MD5 differs')
        row=dict(stamp=match[1],bytes=int(fields[0]),md5=fields[1].zfill(32),url=BASE+match[1]+'.gkg.csv.zip')
        if match[1] in selected and selected[match[1]]!=row:raise ValueError('conflicting GKG catalog archive')
        selected[match[1]]=row
    return selected,dict(url=CATALOG,bytes=count,lines=lines,official_root_marker_lines=markers,blank_lines=blanks,
                         sha256=digest.hexdigest(),complete_catalog=True,
                         missing_stamps=sorted(wanted-set(selected)))


def normalize_org(value):return ' '.join(value.casefold().split())


def alias_index(entities):
    aliases={}
    if len({e['entity_id'] for e in entities})!=len(entities):raise ValueError('duplicate probe entity id')
    for entity in entities:
        if not entity['entity_id'] or not entity['aliases']:raise ValueError('entity id and explicit aliases required')
        for name in entity['aliases']:
            key=normalize_org(name)
            if len(key)<3:raise ValueError('short or empty organization alias')
            if key in aliases and aliases[key]!=entity['entity_id']:raise ValueError('ambiguous organization alias')
            aliases[key]=entity['entity_id']
    return aliases


def tone_values(value):
    if not value:return None
    try:
        fields=value.decode('ascii').split(',')
        if len(fields)!=7:return None
        numbers=[float(x) for x in fields]
        if not all(math.isfinite(x) for x in numbers):return None
        if not -100<=numbers[0]<=100 or any(not 0<=x<=100 for x in numbers[1:6]):return None
        if numbers[6]<0 or not numbers[6].is_integer():return None
        return numbers[0],int(numbers[6])
    except (ValueError,UnicodeError):return None


def parse_archive(raw,receipt,entities,max_uncompressed_bytes=512000000):
    """Counts are unique GKG records, not a claim of unique articles over time."""
    stamp=receipt['stamp'];checked_stamp(stamp)
    if len(raw)!=receipt['bytes'] or hashlib.md5(raw,usedforsecurity=False).hexdigest()!=receipt['md5']:
        raise ValueError('GKG source size/MD5 differs from official catalog')
    aliases=alias_index(entities);counters={e['entity_id']:Counter() for e in entities};counters['__corpus__']=Counter()
    tones={key:[] for key in counters};seen={};quarantine=Counter();metadata=Counter();member_hash=hashlib.sha256()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files=archive.infolist()
        expected=stamp+'.gkg.csv'
        if len(files)!=1 or files[0].filename!=expected or files[0].file_size>max_uncompressed_bytes:
            raise ValueError('GKG archive member/expanded size differs')
        with archive.open(files[0]) as stream:
            while True:
                line=stream.readline(8000001)
                if not line:break
                if len(line)>8000000:raise ValueError('GKG record exceeds bounded line length')
                member_hash.update(line);metadata['raw_rows']+=1
                fields=line.rstrip(b'\r\n').split(b'\t')
                if len(fields)!=27:quarantine['COLUMN_COUNT']+=1;continue
                try:
                    record=fields[0].decode('ascii');date=fields[1].decode('ascii')
                    if date!=stamp or not re.fullmatch(re.escape(stamp)+r'-(?:T)?\d+',record):
                        raise ValueError('GKG archive dates differ from the requested historical batch')
                    if record in seen:
                        if seen[record]!=hashlib.sha256(line).digest():raise ValueError('conflicting duplicate GKG record')
                        metadata['identical_duplicate_rows']+=1;continue
                    seen[record]=hashlib.sha256(line).digest()
                except UnicodeError:
                    quarantine['IDENTITY_ENCODING']+=1;continue
                if fields[2]!=b'1':metadata['non_web_rows_excluded']+=1;continue
                selected={'__corpus__'}
                try:
                    names=fields[13].decode('utf-8').split(';')
                    selected.update(aliases[name] for name in {normalize_org(n) for n in names} if name in aliases)
                except UnicodeError:quarantine['ORGANIZATION_ENCODING']+=1
                tone=tone_values(fields[15])
                if not fields[15]:metadata['blank_tone_rows']+=1
                elif tone is None:metadata['invalid_tone_rows']+=1
                metadata['web_records']+=1;metadata['translated_record_marker' if '-T' in record else 'untranslated_record_marker']+=1
                for entity in selected:
                    counter=counters[entity];counter['record_count']+=1
                    if tone is None:counter['tone_missing']+=1;continue
                    score,words=tone;counter['tone_observations']+=1;counter['word_count']+=words
                    counter['positive_records' if score>0 else 'negative_records' if score<0 else 'neutral_records']+=1
                    tones[entity].append(score)
    if metadata['web_records']==0:raise ValueError('archive has no valid web records; not a zero news count')
    rows=[];org_complete=not quarantine
    for entity,counter in counters.items():
        scores=tones[entity];count=counter['record_count']
        # A corrupt/unreadable row can hide an alias match; do not invent a
        # whole-file zero from the successfully parsed subset.
        observed_count=count if count or org_complete else None
        rows.append(dict(batch_timestamp=stamp,entity_id=entity,record_count=observed_count,
            tone_observations=counter['tone_observations'],tone_mean=math.fsum(scores)/len(scores) if scores else None,
            tone_sum=math.fsum(scores) if scores else None,tone_sum_squares=math.fsum(x*x for x in scores) if scores else None,
            positive_records=counter['positive_records'],negative_records=counter['negative_records'],
            neutral_records=counter['neutral_records'],word_count=counter['word_count'],tone_missing=counter['tone_missing'],
            tone_complete=counter['tone_missing']==0,
            complete_file_parse=org_complete,source_scope='REQUESTED_15_MINUTE_ENGLISH_CATALOG_FILE',
            identity_scope='EXPLICIT_PROBE_ALIASES_NOT_HISTORICAL_TICKER_MAPPING'))
    return rows,dict(**metadata,quarantine=dict(quarantine),member_sha256=member_hash.hexdigest(),
        archive_sha256=hashlib.sha256(raw).hexdigest(),member_bytes=files[0].file_size,
        source_collection='WEB_ONLY',count_unit='unique GKG records within this file; not globally deduplicated articles',
        free_text_persisted=False,complete_file_parse=org_complete)


def fetch_bytes(url,bound):
    request=urllib.request.Request(url,headers={'User-Agent':'checklist-engine numeric-archive-reader'})
    with urllib.request.urlopen(request,timeout=180) as response:
        raw=response.read(bound+1)
        if len(raw)>bound:raise ValueError('GKG archive exceeds bounded download')
        return raw,dict(http_status=response.status,last_modified=response.headers.get('Last-Modified'),etag=response.headers.get('ETag'),
                        observed_at=datetime.now(timezone.utc).isoformat())


def run(root,request):
    import pandas as pd
    from ci.release_assets import gh_retry,publish_assets
    root.mkdir(parents=True,exist_ok=True)
    report=dict(status='INCOMPLETE_GKG_ARCHIVE_CAPTURE',request=request,source_commit=os.environ['GITHUB_SHA'],attempts=[],parts=[],
        historical_full_interval_gate='NOT_PROVEN; three 15-minute files are not continuous history',
        ticker_identity_gate='NOT_PROVEN; exact demonstration aliases only',
        point_in_time_gate='NOT_PROVEN; record batch timestamp and current Last-Modified are not historical byte-vintage proof',
        world_gate='NOT_RUN',scoring_gate='CLOSED')
    report_file=root/'GDELT_GKG_SOURCE_REPORT.json';files=[];blocked=False
    try:
        req=urllib.request.Request(CATALOG,headers={'User-Agent':'checklist-engine numeric-archive-reader'})
        with urllib.request.urlopen(req,timeout=180) as response:
            selected,catalog=select_catalog(response,request['stamps'],request['max_catalog_bytes'])
        report['catalog']=catalog
        for stamp in request['stamps']:
            receipt=dict(stamp=stamp)
            try:
                if blocked:receipt['status']='NOT_ATTEMPTED_AFTER_ACCESS_OR_RATE_LIMIT';report['attempts'].append(receipt);continue
                if stamp not in selected:raise ValueError('requested historical batch missing from official catalog')
                source=selected[stamp];receipt.update(source)
                raw,headers=fetch_bytes(source['url'],request['max_archive_bytes']);receipt.update(headers)
                rows,stats=parse_archive(raw,source,request['entities'],request['max_uncompressed_bytes'])
                frame=pd.DataFrame(rows)
                for column in ('record_count','tone_observations','positive_records','negative_records','neutral_records','word_count','tone_missing'):
                    frame[column]=frame[column].astype('Int64')
                for column in ('tone_mean','tone_sum','tone_sum_squares'):frame[column]=frame[column].astype('float64')
                frame['batch_timestamp']=pd.to_datetime(frame.batch_timestamp,format='%Y%m%d%H%M%S',utc=True).astype('datetime64[ns, UTC]')
                file=root/(stamp+'.numeric.parquet');frame.to_parquet(file,index=False,compression='zstd')
                receipt.update(status='NUMERIC_ARCHIVE_ROWS_RETURNED',statistics=stats)
                files.append(file);report['parts'].append(dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),rows=len(rows)))
            except urllib.error.HTTPError as exc:
                receipt.update(status='SOURCE_ERROR',http_status=exc.code,error=str(exc));blocked=exc.code in (401,403,429)
            except Exception as exc:receipt.update(status='SOURCE_ERROR',error=str(exc))
            report['attempts'].append(receipt);report_file.write_text(json.dumps(report,indent=2)+'\n')
            print('GKG_ARCHIVE_CAPTURE',stamp,receipt['status'],flush=True);time.sleep(6)
    except Exception as exc:report['catalog_error']=str(exc)
    complete=len(files)==len(request['stamps'])
    report['status']='BOUNDED_GKG_ARCHIVE_NUMERIC_CAPTURE_NOT_FULL_HISTORY' if complete else 'PARTIAL_OR_FAILED_GKG_ARCHIVE_CAPTURE'
    report_file.write_text(json.dumps(report,indent=2)+'\n')
    if files:
        tag=f"gdelt-gkg-numeric-v1-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
        gh_retry('release','create',tag,'--draft','--title',tag,'--target',os.environ['GITHUB_SHA'],
                 '--notes','Official GKG archive numeric-only capture. Three batch files, not continuous history/PIT/ticker approval.')
        publish_assets(tag,report_file,*files);gh_retry('release','edit',tag,'--draft=false')
    if not complete:raise RuntimeError('GKG archive source incomplete; failures retained, no zero filling')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True)
    args=parser.parse_args();run(Path(args.directory),json.loads(Path('ci/GDELT_GKG_ARCHIVE_REQUEST.json').read_text()))

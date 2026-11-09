"""Synthetic complete cached and scheduled routes; no network or market inputs."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from ci.sec_quarterly_profile import profile_zip
from ci.sec_quarterly_retained import run


class Publisher:
    def __init__(self,root):self.root=root;self.assets=[]
    def emit(self,path,kind,**metadata):
        raw=path.read_bytes();binding=dict(name=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),kind=kind,**metadata)
        self.assets.append(binding);path.unlink();return binding
    def json(self,name,value,kind):
        path=self.root/name;path.write_text(json.dumps(value));return self.emit(path,kind)


class RunnerTests(unittest.TestCase):
    def test_cached_push_avoids_vendor_and_schedule_refreshes_all_published_windows(self):
        for event in ('push','schedule'):
            with self.subTest(event=event),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);out=root/'output';out.mkdir();path=root/'2020q1_form345.zip'
                with zipfile.ZipFile(path,'w') as archive:
                    archive.writestr('SUBMISSION.tsv','ACCESSION_NUMBER\tFILING_DATE\tDOCUMENT_TYPE\tISSUERCIK\nA\t02-JAN-2020\t4\t123\n')
                    archive.writestr('NONDERIV_TRANS.tsv','ACCESSION_NUMBER\tNONDERIV_TRANS_SK\tTRANS_DATE\tTRANS_ACQUIRED_DISP_CD\tTRANS_SHARES\nA\t1\t01-JAN-2020\tA\t10.25\n')
                raw_zip=path.read_bytes();profile=profile_zip(path)
                window=dict(name=path.name,url='https://www.sec.gov/files/'+path.name,label='2020Q1',
                    nominal_year=2020,nominal_quarter=1,filename_start_date=None,filename_end_date=None)
                source=dict(url=window['url'],bytes=len(raw_zip),sha256=hashlib.sha256(raw_zip).hexdigest(),started_at='original acquisition time')
                proof=dict(release='sec-bulk-readback-v1-1-1',commit='a'*40,receipt_sha256='b'*64)
                request=dict(version=2,scope='SEC_QUARTERLY_FIXED_FIELDS_2020_LATEST',execute=event=='push',
                    bulk_readback=proof,profile_sources={'form345':dict(run='1',attempt='1',commit='c'*40,receipt_sha256='d'*64)})
                request_path=root/'request.json';request_path.write_text(json.dumps(request))
                class Cache:
                    tag='synthetic-profile';report=dict(index=dict(url='synthetic index'));windows=[dict(window=window)]
                    def get(self,receipt):return path,source,profile
                downloaded=[]
                def fresh(url,target,maximum):
                    downloaded.append(url)
                    if url==window['url']:target.write_bytes(raw_zip);return source
                    body=('<a href="'+window['url']+'">published data</a>').encode();target.write_bytes(body)
                    return dict(url=url,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
                with patch.dict(os.environ,dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='SRoyaltyy/checklist-engine',
                        GITHUB_EVENT_NAME=event,GITHUB_RUN_ID='123',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='e'*40)),\
                        patch('ci.sec_quarterly_retained.REQUEST',request_path),\
                        patch('ci.sec_quarterly_retained.bulk_prerequisite',return_value=dict(producer={})),\
                        patch('ci.sec_quarterly_retained.retained_ciks',return_value=({123},dict(retained_names=8439))),\
                        patch('ci.sec_quarterly_retained.ProfileCache',return_value=Cache()) as cache,\
                        patch('ci.sec_quarterly_retained.Publisher',return_value=Publisher(out)),\
                        patch('ci.sec_quarterly_retained.download',side_effect=fresh),\
                        patch('ci.sec_quarterly_retained.relay_configuration',return_value=dict(matches_inspected_production_worker=True)),\
                        patch('ci.sec_quarterly_retained.releases.publish_assets'),patch('ci.sec_quarterly_retained.releases.gh_retry'):
                    report=run('form345',out)
                self.assertEqual(report['status'],'PASS_ALL_PUBLISHED_QUARTERLY_FIXED_FIELDS_SOURCE_ONLY')
                self.assertEqual(report['windows'][0]['source']['started_at'],'original acquisition time')
                self.assertEqual(report['windows'][0]['extraction']['tables']['NONDERIV_TRANS']['output_rows'],1)
                self.assertEqual(report['published_catalog'],[window])
                self.assertEqual(len(downloaded),0 if event=='push' else 2)
                self.assertEqual(cache.call_count,1 if event=='push' else 0)


if __name__=='__main__':unittest.main()

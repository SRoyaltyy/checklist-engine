"""Synthetic access-proof schema and scope checks; no external requests."""
import json
import os
import unittest
from unittest.mock import patch
from ci.sec_runner_access import SOURCES,inspect,main,validate_request


class AccessProofTests(unittest.TestCase):
    def test_fixed_scope_allows_only_execute_toggle(self):
        request=dict(version=1,scope='SIX_DECLARED_OFFICIAL_ENDPOINTS_ONLY',max_response_bytes=10000000,attempts_per_endpoint=1,execute=False)
        self.assertEqual(validate_request(request),request)
        for key,value in [('execute',1),('max_response_bytes',10000001),('attempts_per_endpoint',2),('extra',True)]:
            bad=dict(request,**{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):validate_request(bad)

    def test_runner_guard_prevents_local_source_reads(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,'only on the authorized GitHub runner'):main()

    def test_nonempty_ticker_schema(self):
        self.assertEqual(inspect('tickers',b'{"0":{"cik_str":1,"ticker":"TEST"}}',SOURCES[0][1]),{'rows':1})
        for raw in [b'{}',b'{"0":{"ticker":"TEST"}}',b'<html>Denied</html>']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):inspect('tickers',raw,SOURCES[0][1])

    def test_exchange_schema(self):
        value=dict(fields=['cik','ticker','exchange'],data=[[1,'TEST','TEST']])
        self.assertEqual(inspect('exchange_tickers',json.dumps(value).encode(),SOURCES[1][1]),{'rows':1})
        value['data']=[]
        with self.assertRaises(ValueError):inspect('exchange_tickers',json.dumps(value).encode(),SOURCES[1][1])

    def test_official_link_not_unrelated_or_empty_page(self):
        url=SOURCES[2][1]
        link='https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/2020q1_form345.zip'
        self.assertEqual(inspect('form345_index',('<a href="'+link+'">zip</a>').encode(),url)['verified_official_zip_links'],1)
        for html in ['Denied','<a href="https://other.example/2020q1_form345.zip">bad</a>']:
            with self.subTest(html=html),self.assertRaises(ValueError):inspect('form345_index',html.encode(),url)

    def test_sample_cik_and_numeric_payload_required(self):
        value=dict(cik=320193,units={'USD':[{'val':100}]})
        self.assertEqual(inspect('numeric_concept',json.dumps(value).encode(),SOURCES[5][1]),{'rows':1})
        for bad in [dict(cik=1,units=value['units']),dict(cik=320193,units={}),dict(cik=320193,units={'USD':[{'val':'text'}]})]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):inspect('numeric_concept',json.dumps(bad).encode(),SOURCES[5][1])


if __name__=='__main__':
    unittest.main()

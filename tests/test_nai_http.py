"""Synthetic HTTP transport checks; no network or market data."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.parse

from scripts.nai import common as c

SOURCE = 'https://www.sec.gov/files/company_tickers.json'
RELAY = 'https://private.example/route?token=secret-test-token&url=old'


class HTTPTests(unittest.TestCase):
    def test_error_excerpt_preserves_reason_instead_of_css_and_redacts_ip(self):
        raw=('<title>SEC.gov | Access denied</title><style>'+'x'*1500+'</style>'
             '<script>hidden()</script><h1>Undeclared automated tool</h1>'
             '<p>Contact &amp; identify. IP 192.0.2.3</p>').encode()
        result=c.response_excerpt(raw)
        self.assertIn('Undeclared automated tool',result)
        self.assertIn('Contact & identify.',result)
        self.assertNotIn('hidden',result)
        self.assertNotIn('192.0.2.3',result)
        self.assertNotIn('x'*50,result)

    def setUp(self):
        self.env = patch.dict(os.environ, {'PRIMARY_ACTION_RELAY_URL':RELAY}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        c._last[0] = 0

    def test_sec_uses_relay_encoded_target_and_declared_contact(self):
        with patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'{}')) as network:
            self.assertEqual(c.get(SOURCE),b'{}')
        request = network.call_args.args[0]
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query),
                         {'token':['secret-test-token'],'url':[SOURCE]})
        self.assertIn('@',request.get_header('User-agent'))
        self.assertEqual(request.get_header('Accept-encoding'),'identity')

    def test_configured_contact_precedence(self):
        with patch.dict(os.environ,{'SEC_USER_AGENT':'Named research contact@example.test','SEC_UA':'Legacy legacy@example.test'}):
            with patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'{}')) as network:
                c.get(SOURCE)
            self.assertEqual(network.call_args.args[0].get_header('User-agent'),'Named research contact@example.test')

    def test_missing_relay_fails_before_network(self):
        os.environ.pop('PRIMARY_ACTION_RELAY_URL')
        with patch.object(c.urllib.request,'urlopen') as network:
            with self.assertRaisesRegex(RuntimeError,'DIRECT_SEC_REQUEST_FORBIDDEN'):
                c.get(SOURCE)
        network.assert_not_called()

    def test_internal_transport_cannot_bypass(self):
        with patch.object(c.urllib.request,'urlopen') as network:
            with self.assertRaisesRegex(RuntimeError,'DIRECT_SEC_REQUEST_FORBIDDEN'):
                c._get(SOURCE)
        network.assert_not_called()

    def test_invalid_relay_and_target_rejected(self):
        for relay in ['http://private.example/','https://user:password@private.example/','https://www.sec.gov/']:
            with self.subTest(relay=relay),patch.dict(os.environ,{'PRIMARY_ACTION_RELAY_URL':relay}):
                with self.assertRaises(ValueError):c._relay(SOURCE)
        for target in ['https://sec.gov.evil.example/a','http://www.sec.gov/a','https://user:password@data.sec.gov/a']:
            with self.subTest(target=target),self.assertRaises(ValueError):c._relay(target)

    def test_invalid_contact_rejected(self):
        for agent in ['unnamed','Name user@example.test\r\nBad: value']:
            with self.subTest(agent=agent),self.assertRaises(ValueError):c.get(SOURCE,ua=agent)

    def test_denial_is_one_attempt_with_redacted_evidence(self):
        def denied(request,**kwargs):
            raise urllib.error.HTTPError(request.full_url,403,'Forbidden',{},io.BytesIO(('<h1>Denied</h1>'+RELAY).encode()))
        with patch.object(c.urllib.request,'urlopen',side_effect=denied) as network:
            with self.assertRaises(c.SourceError) as caught:c.get(SOURCE,tries=6)
        self.assertEqual(network.call_count,1)
        evidence = caught.exception.evidence
        self.assertEqual((evidence['url'],evidence['route'],evidence['http_status'],evidence['attempts']),(SOURCE,'relay',403,1))
        self.assertEqual(evidence['request_spacing_seconds'],1.)
        self.assertNotIn('private.example',str(caught.exception))
        self.assertNotIn('secret-test-token',json.dumps(evidence))
        self.assertIn('Denied',evidence['response_excerpt'])

    def test_rate_denial_is_not_retried(self):
        error=urllib.error.HTTPError(SOURCE,429,'Too Many Requests',{},io.BytesIO(b'Rate threshold'))
        with patch.object(c.urllib.request,'urlopen',side_effect=error) as network:
            with self.assertRaises(c.SourceError):c.get(SOURCE)
        self.assertEqual(network.call_count,1)

    def test_transient_failure_can_retry_politely(self):
        error=urllib.error.HTTPError(SOURCE,503,'Unavailable',{},io.BytesIO(b'Temporary'))
        with patch.object(c.urllib.request,'urlopen',side_effect=[error,io.BytesIO(b'ok')]) as network,patch.object(c.time,'sleep') as sleep:
            self.assertEqual(c.get(SOURCE,tries=2),b'ok')
        self.assertEqual(network.call_count,2)
        self.assertIn(1,[x.args[0] for x in sleep.call_args_list])

    def test_stream_is_atomic_and_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            dest=str(Path(directory)/'data.bin')
            Path(dest).write_bytes(b'old')
            with patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'new-data')):
                with self.assertRaisesRegex(ValueError,'byte limit'):c.get(SOURCE,dest,max_bytes=2)
            self.assertEqual(Path(dest).read_bytes(),b'old')
            self.assertFalse(Path(dest+'.part').exists())
            with patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'new-data')),patch.object(c.time,'sleep'):
                self.assertEqual(c.get(SOURCE,dest),dest)
            self.assertEqual(Path(dest).read_bytes(),b'new-data')
            self.assertFalse(Path(dest+'.part').exists())

    def test_bounded_small_response(self):
        with patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'1234')):
            with self.assertRaisesRegex(ValueError,'byte limit'):c.get(SOURCE,max_bytes=3)

    def test_nonsec_source_stays_direct(self):
        source='https://cdn.finra.org/equity/regsho/daily/example.txt'
        with patch.object(c.urllib.request,'urlopen',return_value=io.BytesIO(b'1')) as network:
            self.assertEqual(c.get(source),b'1')
        self.assertEqual(network.call_args.args[0].full_url,source)


if __name__ == '__main__':
    unittest.main()

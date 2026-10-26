import gzip,io,json,urllib.error,urllib.parse
from unittest.mock import patch
import pytest
from fetch.sec_client import get_json,relay_target,SECSourceError

SOURCE='https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json'
RELAY='https://private-relay.example/route?token=secret-test-token'

def test_relay_success_uses_encoded_original_url_headers_and_gzip(monkeypatch,capsys):
    monkeypatch.setenv('PRIMARY_ACTION_RELAY_URL',RELAY)
    response=io.BytesIO(gzip.compress(b'{"facts":{"us-gaap":{}}}'))
    with patch('urllib.request.urlopen',return_value=response) as request,patch('time.sleep') as delay:
        assert get_json(SOURCE)=={'facts':{'us-gaap':{}}}
    req=request.call_args.args[0]
    query=urllib.parse.parse_qs(urllib.parse.urlsplit(req.full_url).query)
    assert query['url']==[SOURCE] and query['token']==['secret-test-token']
    assert '@' in req.get_header('User-agent') and req.get_header('Accept-encoding')=='gzip'
    delay.assert_called_with(1.)
    output=capsys.readouterr().out
    assert SOURCE in output and 'route=relay' in output
    assert 'private-relay' not in output and 'secret-test-token' not in output

def test_relay_http_failure_preserves_source_identity_and_redacts_proxy(monkeypatch):
    monkeypatch.setenv('PRIMARY_ACTION_RELAY_URL',RELAY)
    def blocked(req,**kwargs):
        raise urllib.error.HTTPError(req.full_url,403,RELAY,{},io.BytesIO(RELAY.encode()))
    with patch('urllib.request.urlopen',side_effect=blocked) as request,patch('time.sleep'):
        with pytest.raises(SECSourceError) as caught:get_json(SOURCE)
    assert request.call_count==4
    assert caught.value.url==SOURCE and caught.value.evidence['route']=='relay'
    assert caught.value.evidence['attempts']==4
    printed=str(caught.value)+json.dumps(caught.value.evidence)
    assert 'private-relay' not in printed and 'secret-test-token' not in printed

@pytest.mark.parametrize('source',['https://evil.example/a','https://data.sec.gov.evil.example/a'])
def test_relay_rejects_non_sec_targets(source):
    with pytest.raises(ValueError):relay_target(RELAY,source)

@pytest.mark.parametrize('relay',['http://proxy.example/','https://user:secret@proxy.example/'])
def test_relay_rejects_insecure_or_embedded_credentials(relay):
    with pytest.raises(ValueError):relay_target(relay,SOURCE)


def test_missing_relay_fails_before_any_sec_network_request(monkeypatch):
    monkeypatch.delenv('PRIMARY_ACTION_RELAY_URL',raising=False)
    with patch('urllib.request.urlopen') as network:
        with pytest.raises(RuntimeError,match='DIRECT_SEC_REQUEST_FORBIDDEN'):get_json(SOURCE)
    network.assert_not_called()


def test_internal_transport_cannot_bypass_relay_guard():
    from fetch.sec_client import _request_bytes
    with patch('urllib.request.urlopen') as network:
        with pytest.raises(RuntimeError,match='DIRECT_SEC_REQUEST_FORBIDDEN'):_request_bytes(SOURCE,SOURCE,4,False,'direct')
    network.assert_not_called()

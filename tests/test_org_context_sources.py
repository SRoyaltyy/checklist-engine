import hashlib

import pandas as pd
import pytest

from fetch.org_context_sources import numeric, project, verify_blob


def test_numeric_projection_excludes_news_and_keeps_missing_and_parse_failures_distinct():
    raw = b'Ticker,Price,Market Cap,Short Float,News Title,Daily Digest,Company,Open\nAAPL,123.5,2.1T,1.5%,headline,paragraph,Apple,-\nEMPTY,-,bad,0%,more,text,Name,10\n'
    frame, profile = project(raw, 'theme')
    assert set(frame) == {'Ticker', 'Price', 'Market Cap', 'Short Float', 'Open'}
    assert frame['Market Cap'].iloc[0] == 2.1e12
    assert frame['Short Float'].iloc[0] == .015
    assert frame['Short Float'].iloc[1] == 0
    assert pd.isna(frame.Price.iloc[1]) and pd.isna(frame.Open.iloc[0])
    assert profile['unparsed_numeric']['Market Cap'] == 1
    assert profile['unparsed_numeric']['Price'] == 0
    assert 'News Title' in profile['excluded_columns']


def test_peer_membership_is_a_fixed_captured_list_and_numeric_peers_remain_numeric():
    raw = ('ticker,' + ','.join('peer_' + str(i) for i in range(1, 11)) + '\nA,' + ','.join(['B'] * 10) + '\n').encode()
    frame, profile = project(raw, 'correlations')
    assert frame.peer_10.iloc[0] == 'B'
    assert 'NOT_PROVEN' in profile['scope']
    frame, _ = project(b'Ticker,rs_week,n_peers,peers\nA,-3.2,10,B|C\n', 'peer_rs')
    assert frame.rs_week.iloc[0] == -3.2 and frame.n_peers.iloc[0] == 10


def test_source_blob_hash_and_size_both_required():
    raw = b'raw source'
    meta = dict(path='data/test.csv', size=len(raw),
                git_blob_sha1=hashlib.sha1(b'blob 10\0' + raw).hexdigest())
    verify_blob(raw, meta)
    with pytest.raises(ValueError, match='size/blob'):
        verify_blob(raw + b'!', meta)
    with pytest.raises(ValueError, match='size/blob'):
        verify_blob(b'RAW source', meta)


def test_nonfinite_and_unrecognized_numeric_values_do_not_become_zero():
    assert pd.isna(numeric('inf')[0]) and numeric('inf')[1]
    assert pd.isna(numeric('unknown')[0]) and numeric('unknown')[1]
    assert numeric('1,200K') == (1200000., False)

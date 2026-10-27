import pytest
from fetch.gdelt_source_probe import parse_payload

START, END = '20200101000000', '20200131235959'


def payload(value, norm=100):
    return {'timeline': [{'data': [{'date': '20200102T000000Z', 'value': value, 'norm': norm}]}]}


def test_raw_article_counts_and_norm_preserved_while_tone_keeps_fraction_and_sign():
    raw = parse_payload(payload(23), 'TimelineVolRaw', START, END)
    assert raw.value.iloc[0] == 23 and raw.norm.iloc[0] == 100
    tone = parse_payload(payload(-1.2345), 'TimelineTone', START, END)
    assert tone.value.iloc[0] == -1.2345 and 'norm' not in tone


@pytest.mark.parametrize('value,norm', [(.45, 100), (-1, 100), (101, 100), (1, float('nan'))])
def test_raw_mode_never_truncates_percentages_or_invalid_counts(value, norm):
    with pytest.raises(ValueError):
        parse_payload(payload(value, norm), 'TimelineVolRaw', START, END)


def test_old_request_cannot_accept_silently_substituted_recent_history():
    data = payload(10)
    data['timeline'][0]['data'][0]['date'] = '20261002T000000Z'
    with pytest.raises(ValueError, match='outside requested'):
        parse_payload(data, 'TimelineVolRaw', START, END)


def test_empty_error_and_article_text_payloads_cannot_become_zero_counts():
    for data in ({'timeline': []}, {'timeline': [{'data': []}]}, {'articles': [{'title': 'text'}]}):
        with pytest.raises(ValueError):
            parse_payload(data, 'TimelineVolRaw', START, END)
    with pytest.raises(ValueError, match='only numeric'):
        parse_payload({}, 'ArtList', START, END)

import pytest

from sec_ticker_history import dated_ticker_rows,canonical_cik


def submission():
    return {
        "cik": "0000001750",
        "tickers": ["AIR"],
        "exchanges": ["NYSE"],
        "formerNames": [{"name": "AAR CORP", "from": "2000-01-01T00:00:00.000Z", "to": "2002-01-01T00:00:00.000Z"}],
        "filings": {"recent": {"filingDate": ["2024-01-02"], "form": ["10-K"]}, "files": []},
    }


def test_current_tickers_and_former_legal_names_are_not_a_dated_ticker_map():
    assert dated_ticker_rows(submission()) == []


def test_a_ticker_column_on_filings_is_not_silently_dropped():
    document = submission()
    document["filings"]["recent"]["ticker"] = ["AIR"]
    with pytest.raises(ValueError, match="ticker field"):
        dated_ticker_rows(document)


def test_older_filing_pages_are_inspected_without_inventing_a_ticker_history():
    assert dated_ticker_rows(submission(), [{'filingDate':['2020-01-02']}]) == []
    with pytest.raises(ValueError,match='older filing columns'):
        dated_ticker_rows(submission(), [{'ticker':['AIR']}])


@pytest.mark.parametrize('document',[None,[],{}])
def test_invalid_root_shape_is_rejected(document):
    with pytest.raises(ValueError,match='submissions ticker shape'):
        dated_ticker_rows(document)


@pytest.mark.parametrize('value',[1750,'1750','0000001750'])
def test_equivalent_cik_representations_have_one_numeric_key(value):
    assert canonical_cik(value)==1750


@pytest.mark.parametrize('value',[True,None,0,-1,1750.0,'1.75e3',' 1750','1750.0','10000000000'])
def test_noncanonical_or_out_of_range_cik_is_rejected(value):
    with pytest.raises(ValueError,match='CIK'):canonical_cik(value)

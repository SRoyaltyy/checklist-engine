import pytest

from sec_ticker_history import dated_ticker_rows


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

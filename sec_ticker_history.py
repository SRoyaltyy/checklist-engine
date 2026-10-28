"""Current SEC ticker lists are not a historical ticker map.

companyfacts has no ticker. submissions.json has tickers and exchanges as
parallel undated lists, plus formerNames with from/to dates. Those former
names are legal names, not tickers. Filing rows have no ticker column.
A current ticker is not written onto 2020.
"""
import re


def canonical_cik(value):
    """SEC publishes equivalent integer and zero-padded decimal-string CIKs."""
    if isinstance(value,bool) or not re.fullmatch(r'[0-9]{1,10}',str(value)) or not 0<int(value)<=9999999999:
        raise ValueError('canonical numeric CIK required')
    return int(value)


def dated_ticker_rows(submission, filing_pages=()):
    """Return dated ticker assignments. An undated current list returns none."""
    if not isinstance(submission, dict) or not isinstance(submission.get("tickers"), list) or not isinstance(submission.get("formerNames"), list):
        raise ValueError("submissions ticker shape differs")
    recent = submission.get("filings", {}).get("recent", {})
    if any("ticker" in str(key).lower() for key in recent):
        raise ValueError("filing columns include a ticker field this reader does not map")
    for page in filing_pages:
        if not isinstance(page, dict):
            raise ValueError("older filing page shape differs")
        if any("ticker" in str(key).lower() for key in page):
            raise ValueError("older filing columns include a ticker field this reader does not map")
    return []

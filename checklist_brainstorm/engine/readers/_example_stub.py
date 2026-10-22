"""Example reader (files starting with _ are skipped by the runner).
Copy to readers/<owner>.py and fill in. Contract: answer(ticker, date) -> list of dicts."""
def answer(ticker, date):
    # date is 'YYYY-MM-DD'; use only data published before 09:25 ET on that date.
    return [
        {"row_id": "XX-EXAMPLE-001", "ticker": ticker, "date": date, "answer": "YES", "reason": "", "data_as_of": "2026-10-20"},
        {"row_id": "XX-EXAMPLE-002", "ticker": ticker, "date": date, "answer": "NOT_READY", "reason": "held:no_nightly_archive", "data_as_of": ""},
    ]

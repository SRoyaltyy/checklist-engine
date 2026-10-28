"""Comparison rows are visible on the next SPY session after the source session."""

NEXT_SPY_SESSION = {
    "2020-01-02": "2020-01-03",
    "2020-01-03": "2020-01-06",
    "2020-01-09": "2020-01-10",
    "2020-01-31": "2020-02-03",
    "2020-03-30": "2020-03-31",
    "2020-04-06": "2020-04-07",
    "2020-04-28": "2020-04-29",
    "2020-06-24": "2020-06-25",
    "2024-01-11": "2024-01-12",
    "2024-01-12": "2024-01-16",
    "2024-01-19": "2024-01-22",
    "2024-02-09": "2024-02-12",
    "2024-04-09": "2024-04-10",
    "2024-04-16": "2024-04-17",
    "2024-05-07": "2024-05-08",
    "2024-07-05": "2024-07-08"
}


def visible_on(source_date):
    if not source_date:
        return ""
    try:
        return NEXT_SPY_SESSION[source_date]
    except KeyError as exc:
        raise KeyError("no next SPY session for " + source_date) from exc

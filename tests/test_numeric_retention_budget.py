from ci.numeric_retention_measure import weighted_projection


def test_row_weighted_budget_uses_mean_bytes_per_native_row():
    reports = [
        {"retained_value_container_bytes": 178920377, "source_rows": 9271},
        {"retained_value_container_bytes": 29072127, "source_rows": 1712},
        {"retained_value_container_bytes": 40005933, "source_rows": 2259},
    ]
    mean, missing = weighted_projection(reports, None)
    assert missing is None
    assert 17000 < mean < 20000
    _, weighted = weighted_projection(reports, 31104142)
    assert 500e9 < weighted < 600e9

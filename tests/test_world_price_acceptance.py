import pytest
from ci.accept_world_prices import validate

def inputs():
    record=dict(status="PASS",overlap_rows=60,supplemental_end="2026-10-23",
       frozen_values_unchanged=True,supplemental_basis="vendor_split_adjusted_quote_matching_frozen",
       median_return_difference=.001,p99_return_difference=.01,median_volume_ratio=1.)
    return {"GOOD":record,"BAD":{"status":"FAIL"}},[{"ticker":"BAD","reason":"explicit unresolved bridge"}],{"GOOD":"NON_ETF","BAD":"ETF"}

def test_logged_failures_are_excluded_and_good_source_is_retained():
    r,e,c=inputs();out=validate(r,e,c,"2026-10-23")
    assert [x["ticker"] for x in out]==["GOOD"]

@pytest.mark.parametrize("change,message",[
    ({"overlap_rows":59},"short history"),
    ({"short_history_all_sessions_exact":True},"short history"),
    ({"supplemental_end":"2026-10-22"},"stale"),
    ({"all_overlap_volumes_zero":True},"zero-volume"),
    ({"median_volume_ratio":float("nan")},"bridge metric"),
    ({"supplemental_basis":"dividend_adjusted"},"quote basis"),
    ({"frozen_values_unchanged":False},"unchanged"),
])
def test_bad_source_cannot_hide_behind_a_pass_label(change,message):
    r,e,c=inputs();r["GOOD"].update(change)
    with pytest.raises(ValueError,match=message):validate(r,e,c,"2026-10-23")

def test_unlogged_failure_or_blank_reason_stops_acceptance():
    r,e,c=inputs()
    with pytest.raises(ValueError,match="unlogged failed"):validate(r,[],c,"2026-10-23")
    e[0]["reason"]=" "
    with pytest.raises(ValueError,match="blank exclusion"):validate(r,e,c,"2026-10-23")

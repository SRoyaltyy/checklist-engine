import pytest
from ci.accepted_price_stitch import membership


def test_threshold_uses_original_universe_not_only_present_shards():
    inputs = {'records': [{'ticker': str(i)} for i in range(100)]}
    records = [{'ticker': str(i)} for i in range(95)]
    missing, percent = membership(inputs, records, 95)
    assert percent == 95 and missing == [str(i) for i in range(95, 100)]
    with pytest.raises(ValueError, match='below'): membership(inputs, records[:-1], 95)


@pytest.mark.parametrize('actual', [['a', 'a'], ['a', 'foreign']])
def test_duplicate_or_foreign_tickers_cannot_inflate_coverage(actual):
    with pytest.raises(ValueError, match='duplicate or foreign'):
        membership({'records': [{'ticker': 'a'}, {'ticker': 'b'}]}, [{'ticker': t} for t in actual], 95)


def test_configuration_cannot_lower_owner_threshold():
    with pytest.raises(ValueError, match='95 to 100'):
        membership({'records': [{'ticker': 'a'}]}, [{'ticker': 'a'}], 94)


def test_pinned_prior_source_exclusions_remain_in_original_universe_denominator():
    inputs={'records':[{'ticker':str(i)} for i in range(8447)],'current_exclusions':280}
    with pytest.raises(ValueError,match='below'):
        membership(inputs,inputs['records'][:8192],95)
    missing,percent=membership(inputs,inputs['records'],95)
    assert missing==[] and percent==100*8447/8727

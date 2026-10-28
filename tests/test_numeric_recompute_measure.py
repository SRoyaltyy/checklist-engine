import numpy as np
import pandas as pd
import pytest
from ci.numeric_recompute_measure import compare_frame,sha


def sample():
    bits=np.array([0,2**63,0x7ff8000000000123,0x7ff0000000000000],dtype='<u8')
    frame=pd.DataFrame(dict(available_from=pd.date_range('2020-01-01',periods=4),value=bits.view('<f8')))
    metadata=dict(rows=4,raw_sha256=sha(bits.tobytes()),dates_sha256=sha(frame.available_from.to_numpy(dtype='datetime64[ns]').view('<i8').tobytes()))
    return frame,metadata


def test_all_bits_and_availability_dates_match_independent_stored_hashes():
    frame,metadata=sample();result=compare_frame(frame,['value'],metadata)
    assert result['numeric_cells']==4 and result['mismatches']==0


@pytest.mark.parametrize('change',['signed_zero','nan_payload','date','column','shape'])
def test_numerically_equal_bit_changes_and_schema_or_date_changes_are_rejected(change):
    frame,metadata=sample()
    if change=='signed_zero':frame.loc[1,'value']=0.0
    elif change=='nan_payload':frame.loc[2,'value']=np.array([0x7ff8000000000456],dtype='<u8').view('<f8')[0]
    elif change=='date':frame.loc[0,'available_from']=pd.Timestamp('2019-12-31')
    elif change=='column':frame=frame.rename(columns={'value':'other'})
    elif change=='shape':frame=frame.iloc[:3]
    with pytest.raises(ValueError,match='recomputed'):compare_frame(frame,['value'],metadata)

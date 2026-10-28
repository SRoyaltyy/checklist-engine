import numpy as np
import pandas as pd
import pytest
from market_storage import exact_int64,assert_exact_frame


def test_scaled_integer_encoding_requires_every_bit_to_roundtrip():
    assert exact_int64([1.25,2.5],100).tolist()==[125,250]
    for values in ([26.629999],[100.000001],[-0.0],[np.nan],[np.inf],[1e30]):
        assert exact_int64(values,100) is None
    huge=np.array([2**63-1,2**53+1],dtype=np.int64)
    assert exact_int64(huge).tobytes()==huge.tobytes()
    assert exact_int64(np.array([2**63],dtype=np.uint64)) is None


@pytest.mark.parametrize('writer',['outside','daily','candles'])
def test_panel_writers_keep_fractional_volume_and_all_float_bits(tmp_path,writer):
    from outside_market import write_lossless,read_lossless
    from light_box_market import write_panel,write_candles
    import pyarrow.parquet as pq
    values=np.array([0,2**63,0x7ff8000000000123,0x3ff0000000000001],dtype='<u8').view('<f8')
    frame=pd.DataFrame(dict(ticker=['SPY']*4,date=pd.date_range('2020-01-02',periods=4),
        available_from=pd.date_range('2020-01-03',periods=4),open=values,high=values,low=values,close=values,
        volume=[1.000001,2.5,3.0,-0.0]))
    file=tmp_path/'bits.parquet'
    if writer=='outside':
        frame['vendor_volume']=[1.25,2.0,3.0,4.0]
        meta=write_lossless(frame,file);restored=read_lossless(file,meta['price_storage'])
    elif writer=='daily':
        frame['adj_close']=values;write_panel(frame,file);restored=pq.read_table(file).to_pandas()
    else:
        frame['timeframe']='1d';write_candles(frame,file);restored=pq.read_table(file).to_pandas()
    assert_exact_frame(frame,restored)


def test_vendor_volume_is_not_rounded_because_main_volume_is_integer(tmp_path):
    from outside_market import write_lossless,read_lossless
    frame=pd.DataFrame(dict(ticker=['SPY'],date=pd.to_datetime(['2020-01-02']),available_from=pd.to_datetime(['2020-01-03']),
        open=[1.25],high=[1.25],low=[1.25],close=[1.25],volume=[2**53+1],vendor_volume=[1.000001]))
    file=tmp_path/'independent.parquet';meta=write_lossless(frame,file);restored=read_lossless(file,meta['price_storage'])
    assert restored.volume.iloc[0]==2**53+1
    assert restored.vendor_volume.to_numpy().tobytes()==frame.vendor_volume.to_numpy().tobytes()

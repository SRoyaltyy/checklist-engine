"""Exact storage helpers for the outside-market panels; no tolerance rounding."""
import numpy as np
import pandas as pd
import pyarrow as pa


def exact_int64(values,scale=1):
    source=np.asarray(values)
    if source.dtype.kind in 'iu' and scale==1:
        if source.size and (int(source.min())<-(2**63) or int(source.max())>=2**63):return None
        return source.astype(np.int64)
    if source.dtype.kind not in 'fiu':return None
    original=np.asarray(values,dtype=np.float64)
    scaled=np.rint(original*scale)
    if not np.isfinite(scaled).all() or (scaled<-(2**63)).any() or (scaled>=2**63).any():return None
    integers=scaled.astype(np.int64)
    restored=integers.astype(np.float64)/scale
    if restored.tobytes()!=original.tobytes():return None
    return integers


def exact_arrow_table(frame):
    table=pa.Table.from_pandas(frame,preserve_index=False)
    # NaN payload/sign bits are values too; do not replace them with Arrow nulls.
    for i,column in enumerate(frame):
        if frame[column].dtype==np.dtype('float64'):
            table=table.set_column(i,column,pa.array(frame[column].to_numpy(),type=pa.float64(),from_pandas=False))
    return table


def assert_exact_frame(original,restored):
    pd.testing.assert_frame_equal(original,restored,check_dtype=False,check_exact=True)
    for column in original:
        values=original[column]
        if values.dtype.kind=='f':
            if values.to_numpy(dtype=np.float64).tobytes()!=restored[column].to_numpy(dtype=np.float64).tobytes():
                raise ValueError('stored float bits differ: '+column)
        elif values.dtype.kind in 'iu' and values.tolist()!=restored[column].tolist():
            raise ValueError('stored integer values differ: '+column)

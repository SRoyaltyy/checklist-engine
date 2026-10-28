"""Existing VIX comparison definitions on authenticated CBOE native grids."""
import numpy as np
from outside_vol import divide
from world_context_native import KEYS
from world_context_store import validate_factor

RATIOS=(('vol_vix_over_vix3m','vix','vix3m',True),
        ('vol_vix9d_over_vix','vix9d','vix',True),
        ('vol_vix9d_over_vix3m','vix9d','vix3m',True),
        ('vol_vix3m_minus_vix','vix3m','vix',False),
        ('vol_vix_minus_vix9d','vix','vix9d',False))


def term_native(source):
    """Preserve every grid row, including unavailable source intervals.

    ALFRED VIXCLS remains its own vintage series. These five existing definitions
    consistently use the CBOE VIX/VIX9D/VIX3M prints already retained in source.
    """
    validate_factor(source)
    names={s for _,left,right,_ in RATIOS for s in (left,right)}
    for name in names:
        column='cboe_'+name+'_close'
        if column not in source or source[column].dtype!=np.dtype('float64'):
            raise ValueError('authenticated float64 CBOE close required: '+column)
    out=source[list(KEYS)].copy()
    for column,left,right,ratio in RATIOS:
        a=source['cboe_'+left+'_close'].to_numpy();b=source['cboe_'+right+'_close'].to_numpy()
        out[column]=divide(a,b) if ratio else a-b
    return out

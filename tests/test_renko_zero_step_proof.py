import copy
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from ci.renko_zero_step_proof import FRAMES,numeric_receipt,validate_checks,validate_request


def frame():
    bits=np.array([0,0x8000000000000000,0x7ff8000000000001,0x7ff0000000000000],dtype='uint64')
    return pd.DataFrame({'value':bits.view('float64'),'available_from':pd.date_range('2020-01-02',periods=4)})


@pytest.mark.parametrize('change',['signed_zero','nan_payload','value','dates'])
def test_exact_receipt_rejects_every_bit_or_date_change(change):
    before=frame();expected=numeric_receipt(before,['value']);after=before.copy()
    if change=='dates':after.loc[0,'available_from']+=pd.Timedelta(days=1)
    else:
        index={'signed_zero':0,'nan_payload':2,'value':3}[change]
        values=after.value.to_numpy(copy=True).view('uint64')
        values[index]^=np.uint64(1 if change=='nan_payload' else 0x8000000000000000)
        after['value']=values.view('float64')
    with pytest.raises(ValueError,match='numeric/date bits'):numeric_receipt(after,['value'],expected)
    assert numeric_receipt(before,['value'],expected)['mismatches']==0


def test_numeric_column_order_and_membership_are_part_of_proof():
    source=frame();source['other']=1.
    with pytest.raises(ValueError,match='registry/order'):numeric_receipt(source,['other','value'])


def test_worker_import_stays_free_of_math_until_frozen_path_is_installed():
    script='import sys; import ci.renko_zero_step_proof; assert not {"facets_world","world_timeframes","ci.compact_world_build"}.intersection(sys.modules)'
    subprocess.run([sys.executable,'-c',script],check=True,timeout=10)


@pytest.mark.parametrize('change',['missing','duplicate','reordered','wrong_columns','wrong_cells','mismatch'])
def test_partial_or_misbound_native_proofs_cannot_pass(change):
    checks=[dict(timeframe=tf,rows=3,columns=1044,numeric_cells=3132,mismatches=0) for tf in FRAMES]
    validate_checks(checks)
    if change=='missing':checks.pop()
    elif change=='duplicate':checks[-1]=copy.deepcopy(checks[0])
    elif change=='reordered':checks[0],checks[1]=checks[1],checks[0]
    else:checks[0][{'wrong_columns':'columns','wrong_cells':'numeric_cells','mismatch':'mismatches'}[change]]=1
    with pytest.raises(ValueError,match='complete exact'):validate_checks(checks)


@pytest.mark.parametrize('stocks',[['MAN','EYE'],['MAN','EYE','EYE'],['MAN','MNTS','EYE','OTHER']])
def test_original_three_stock_plan_cannot_be_reduced_or_substituted(stocks):
    request=dict(stocks=[dict(ticker=s) for s in stocks],target=dict(member='45514c54.bars.parquet'),worker_timeout_seconds=900)
    with pytest.raises(ValueError,match='original three'):validate_request(request)


def test_committed_request_preserves_pins_and_separate_scope():
    request=json.loads(Path('ci/RENKO_ZERO_STEP_PROOF_REQUEST.json').read_text(encoding='utf-8'))
    validate_request(request)
    previous=json.loads(Path('ci/RELATIVE_NATIVE_REQUEST.json').read_text(encoding='utf-8'))
    for key in ('parent_proof','stocks','benchmark'):assert request[key]==previous[key]
    assert request['candidate_fingerprint']!=request['base_fingerprint']

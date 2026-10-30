import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
from ci.price_numeric_runtime_trace import bit_differences,selectors,sha
from tests.test_row0_part172_replay import packet


def test_selector_retains_known_and_missing_counterexamples_with_row_binding():
    a,registry=packet([[0,1],[None,0]],'1'*64);b,_=packet([[1,1],[0,0]],'2'*64)
    result=selectors(a,b,registry)
    assert [(r['query_row'],r['old_code'],r['replay_code']) for r in result]==[(0,1,2),(1,0,1)]
    assert all(r['row_keys_sha256']=='c'*64 for r in result)


def test_numeric_comparison_has_no_epsilon_or_missing_coercion():
    a=np.array([1.,0.,np.nan]);b=np.array([np.nextafter(1.,2.),-0.,0.])
    assert bit_differences(a,b)==dict(bit_differences=3,known_value_differences=2,known_missing_differences=1)


def test_fresh_worker_loads_bound_math_and_emits_exact_profile_and_prefix_evidence(tmp_path):
    from ci.renko_recipe import BASE_COMMIT,derive
    manifest=json.loads(Path('recipes/renko_zero_step_v1/RECIPE.json').read_text())
    files={name:subprocess.check_output(['git','show',BASE_COMMIT+':'+name]) for name in manifest['files']}
    recipe=tmp_path/'recipe'
    for name,raw in derive(files).items():
        file=recipe/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(raw)
    dates=pd.bdate_range('2020-01-01',periods=320).as_unit('ns');close=100+np.cos(np.arange(320)/9)+np.arange(320)*.001
    bars=pd.DataFrame(dict(date=dates,open=close-.1,high=close+.5,low=close-.5,close=close,volume=1000.))
    bars_file=tmp_path/'bars.parquet';calendar=tmp_path/'calendar.parquet';bars.to_parquet(bars_file,index=False)
    pd.DataFrame(dict(date=dates)).to_parquet(calendar,index=False)
    config=dict(bars=str(bars_file),bars_sha256=sha(bars_file.read_bytes()),calendar=str(calendar),calendar_sha256=sha(calendar.read_bytes()),
        stock=dict(ticker='SYN',query_rows=320,selectors=[dict(question_id=q,query_row=217,old_code=1,replay_code=2,
            row_keys_sha256=sha(b'SYN'+dates.asi8.tobytes())) for q in ('RETURN_SKEW20:rising1__1d','I070_default_per_candle_sigma:rising1__1d')]),profile='synthetic',prefix_checks=True)
    root=tmp_path/'worker';root.mkdir();(root/'WORKER.json').write_text(json.dumps(config),encoding='utf-8')
    subprocess.run([sys.executable,'-m','ci.price_numeric_runtime_trace','worker','--directory',str(root),'--recipe',str(recipe)],check=True,timeout=60)
    result=json.loads((root/'TRACE.json').read_text(encoding='utf-8'))
    assert all(s['status']=='TRACED' for s in result['selectors'])
    assert len(result['prefix_checks'])==2 and result['observed_log_calls']
    assert result['runtime']['numpy']==np.__version__ and result['scoring_gate']=='CLOSED'
    assert result['runtime']['active_ufunc_dispatch']['log']
    assert result['I070_parameter_selection'].startswith('ALL_FROZEN_I070_SETTINGS')

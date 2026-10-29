import json
from pathlib import Path
import subprocess
import sys
import textwrap

import numpy as np
import pytest
import talib

from ci.renko_recipe import BASE_COMMIT,BASE_FACETS_SHA,patch_facets,sha


def original():
    return subprocess.check_output(['git','show',BASE_COMMIT+':facets_world.py'])


def renko_function(raw):
    text=raw.decode();start=text.index('    # M217 Renko:');end=text.index('    # M220 Point & Figure:',start)
    scope={'np':np,'talib':talib}
    exec('def run(c,h,l):\n    out={}\n'+text[start:end]+'    return out["tv_renko_dir"],out["tv_renko_n"]\n',scope)
    return scope['run']


def test_guard_is_confined_to_the_two_exact_frozen_loops_and_keeps_float64():
    raw=original();assert sha(raw)==BASE_FACETS_SHA
    patched=patch_facets(raw);before=raw.split(b'    # M217 Renko:');after=patched.split(b'    # M217 Renko:')
    assert before[0]==after[0]
    assert before[1].split(b'    # M220 Point & Figure:')[1]==after[1].split(b'    # M220 Point & Figure:')[1]
    assert patched.count(b'raise FloatingPointError("Renko brick cannot advance')==2
    assert b"out['tv_renko_dir'] = rk_dir.astype(np.float64)" in patched
    assert b"out['tv_renko_n'] = rk_n.astype(np.float64)" in patched
    for changed in (raw+b'\n',patched):
        with pytest.raises(ValueError,match='exact frozen'):patch_facets(changed)


@pytest.mark.parametrize('seed',range(10))
def test_all_terminating_legacy_values_and_counter_resets_remain_bit_exact(seed):
    rng=np.random.default_rng(seed)
    c=50+np.cumsum(rng.normal(0,.7,500));h=c+rng.uniform(.1,1,len(c));l=c-rng.uniform(.1,1,len(c))
    old=renko_function(original())(c,h,l);new=renko_function(patch_facets(original()))(c,h,l)
    for expected,actual in zip(old,new):
        np.testing.assert_array_equal(expected.view('uint64'),actual.view('uint64'))


def test_decaying_positive_atr_flat_tail_terminates_without_fabricating_bricks(tmp_path):
    raw=patch_facets(original());text=raw.decode();start=text.index('    # M217 Renko:');end=text.index('    # M220 Point & Figure:',start)
    script='import numpy as np, talib\n'+'def run(c,h,l):\n    out={}\n'+text[start:end]+'    return out["tv_renko_dir"],out["tv_renko_n"]\n'
    script+='c=np.full(700,37.);h=c.copy();l=c.copy();h[:21]=38.;l[:21]=36.\na,b=run(c,h,l)\nassert (a==0).all() and (b==0).all()\n'
    file=tmp_path/'guarded.py';file.write_text(script,encoding='utf-8')
    subprocess.run([sys.executable,str(file)],check=True,timeout=10)


def test_nonzero_nonadvancing_distance_fails_explicitly_instead_of_approximating():
    raw=patch_facets(original());scope={'np':np,'talib':type('ATR',(),{'ATR':staticmethod(lambda h,l,c,timeperiod:np.array([np.nan,1e-20]))})}
    text=raw.decode();start=text.index('    # M217 Renko:');end=text.index('    # M220 Point & Figure:',start)
    exec('def run(c,h,l):\n    out={}\n'+text[start:end]+'    return out\n',scope)
    with pytest.raises(FloatingPointError,match='nonzero price distance'):
        scope['run'](np.array([37.,38.]),np.array([37.,38.]),np.array([37.,38.]))

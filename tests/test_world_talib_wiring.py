"""Regression test: facets_world TA-Lib wiring actually produces columns.

History (2026-10-25): `discover()` stored the {input: None} placeholder dict as
the feed spec; `compute_talib()` then fell into its non-list branch and EVERY
TA-Lib function raised KeyError, swallowed by `except Exception: continue` —
so all 76 functions silently produced zero columns and the release shards
(world-2020-26-v1, 114 cols) contain no TA-Lib data at all. The build exits 0,
so nothing downstream noticed. This test pins the contract with a stub talib
module so it runs without TA-Lib installed.

Run: python3 tests/test_world_talib_wiring.py
"""
import os, sys, types
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _FakeFn:
    """Mimics talib.abstract.Function for a fixed function table."""
    TABLE = {
        # name: (input_names, output_names, kind_group)
        'RSI': (['price'], ['real'], 'Momentum Indicators'),
        'MACD': (['close'], ['macd', 'macdsignal', 'macdhist'], 'Momentum Indicators'),
        'BBANDS': (['close'], ['upperband', 'middleband', 'lowerband'], 'Overlap Studies'),
        'SMA': (['close'], ['real'], 'Overlap Studies'),
        'CDLDOJI': (['open', 'high', 'low', 'close'], ['integer'], 'Pattern Recognition'),
        'AD': (['high', 'low', 'close', 'volume'], ['real'], 'Volume Indicators'),
        'OBV': (['close', 'volume'], ['real'], 'Volume Indicators'),
        # needs open interest -> must be skipped by _feed
        'STOCHRSI_BAD': (['close', 'openinterest'], ['real'], 'Momentum Indicators'),
    }

    def __init__(self, name):
        if name not in self.TABLE:
            raise AttributeError(name)
        self.name = name
        ins, outs, _ = self.TABLE[name]
        self.input_names = ins
        self.output_names = outs

    def __call__(self, d):
        ins, outs, _ = self.TABLE[self.name]
        assert all(k in d for k in ins), f'{self.name} missing inputs'
        n = len(d[ins[0]])
        res = tuple(np.arange(n, dtype=float) + i for i, _ in enumerate(outs))
        return res[0] if len(res) == 1 else res


def _install_stub():
    mod = types.ModuleType('talib')
    abs_mod = types.ModuleType('talib.abstract')
    abs_mod.Function = _FakeFn
    mod.abstract = abs_mod
    groups = {}
    for name, (_, _, g) in _FakeFn.TABLE.items():
        groups.setdefault(g, []).append(name)
    mod.get_function_groups = lambda: groups
    mod.get_functions = lambda: list(_FakeFn.TABLE)
    sys.modules['talib'] = mod
    sys.modules['talib.abstract'] = abs_mod
    return mod


def main():
    mod = _install_stub()
    for m in list(sys.modules):
        if m == 'facets_world':
            del sys.modules[m]

    import facets_world as fw

    funcs = fw.discover()
    # 'STOCHRSI_BAD' needs open interest -> skipped
    assert 'STOCHRSI_BAD' not in funcs, 'open-interest function must be skipped'
    # every feed spec must be a LIST of input names (the old bug stored a dict)
    for name, (kind, need) in funcs.items():
        assert isinstance(need, list) and need and all(isinstance(x, str) for x in need), \
            f'{name}: feed spec must be a list of input names, got {type(need)}'
    print(f'discover: {len(funcs)} functions, all feed specs are input-name lists')

    n = 60
    o = np.full(n, 10.0); h = np.full(n, 11.0); l = np.full(n, 9.0)
    c = np.linspace(10, 20, n); v = np.full(n, 1000.0)
    cols = fw.compute_talib(o, h, l, c, v, funcs)

    # single-output keeps the plain name
    for nm in ('RSI', 'SMA', 'AD', 'OBV'):
        assert nm in cols, f'missing single-output column {nm}'
    # multi-output emits one column per output with suffix
    for nm in ('MACD_macd', 'MACD_macdsignal', 'MACD_macdhist',
               'BBANDS_upperband', 'BBANDS_middleband', 'BBANDS_lowerband'):
        assert nm in cols, f'missing multi-output column {nm}'
    # 6 single-output (RSI, SMA, AD, OBV, CDLDOJI... minus skipped) + 3 MACD + 3 BBANDS
    assert len(cols) == 11, f'expected 11 columns, got {len(cols)}: {sorted(cols)}'
    # pattern converted to -1/0/+1 domain is not in this stub table; check arrays
    assert cols['RSI'].dtype == np.float32 and cols['RSI'].shape == (n,)
    assert np.allclose(cols['MACD_macdhist'], np.arange(n, dtype=float) + 2)

    # no silent zero-column outcome: compute must produce >= len(funcs) columns
    # (more when multi-output functions exist) — the old code returned {}.
    assert len(cols) >= len(funcs), 'silent empty result regression'

    # ticker_frame integration: shift-by-one must still hold with talib columns
    import pandas as pd
    d = pd.DataFrame({'date': pd.date_range('2024-01-01', periods=n, freq='B'),
                      'open': o, 'high': h, 'low': l, 'close': c, 'volume': v})
    df = fw.ticker_frame('TEST', d, funcs, None, None, None)
    for nm in ('RSI', 'MACD_macd'):
        assert nm in df.columns, f'ticker_frame dropped {nm}'
        arr = df[nm].to_numpy()
        # shifted: value at D uses bars <= D-1 -> first row NaN, row t = raw t-1
        assert np.isnan(arr[0]), f'{nm} first row must be NaN after shift'
        assert np.allclose(arr[1:], cols[nm][:-1]), f'{nm} shift mismatch'
    print('ticker_frame: shift-by-one verified on talib columns')

    print('PASS: all talib wiring assertions (7/7 groups)')


if __name__ == '__main__':
    main()

"""Amendment A1 tests: state x rule interaction term in scoring/combine.py.
1) predict_parts z_out accumulates per-variant-group score sums correctly.
2) surface_summary picks GROUP-DEPENDENT cells when W is present, one global cell when absent.
3) fit_model with interactions recovers a planted interaction (lower loss than additive).
Run: python3 tests/test_combine_interactions.py"""
import os, sys, types
import numpy as np

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = []
def ok(name, cond):
    PASS.append((name, bool(cond)))
    if not cond: print(f'FAIL: {name}')

# talib stub (local talib is a non-functional shim)
tl = types.ModuleType('talib')
def _nan(*a, **k): return np.nan
tl.__getattr__ = lambda n: (lambda *a, **k: (np.nan, np.nan, np.nan) if n in ('MACD', 'BBANDS')
                            else (np.nan, np.nan) if n in ('STOCH', 'STOCHF', 'AROON', 'STOCHRSI')
                            else np.nan)
sys.modules.setdefault('talib', tl)
sys.path.insert(0, D)
from scoring import combine as C

# ---------------------------------------------------------------- 1) z accumulation
def test_z_accum():
    cols = ['RSI14|zone_route|1d|20', 'RSI14|speed|1d|20', 'MACD|cross_event|1d|20']
    F = C.Featurizer(cols)
    ok('groups: 2 variants', F.r == 2 and list(F.group_names) == ['MACD', 'RSI14'])
    M = np.array([[0, 1, 0], [1, -1, 1], [-1, 0, 1]], np.int8)   # 3 trades x 3 q
    lut = np.zeros((3, 256), np.float32)
    lut[0, 0] = 1.0; lut[0, 1] = 2.0          # q0 RSI14
    lut[1, 0] = 10.0; lut[1, 1] = 20.0        # q1 RSI14
    lut[2, 0] = 100.0; lut[2, 1] = 200.0      # q2 MACD
    out = np.zeros(3); z = np.zeros((3, F.r))
    F.predict_parts([(M, cols)], lut, out=out, z_out=z)
    g_rsi = F.group_names.index('RSI14'); g_macd = F.group_names.index('MACD')
    ok('z RSI14', np.allclose(z[:, g_rsi], [21.0, 2.0, 10.0]))   # blank(-1)->lut idx 255 = 0
    ok('z MACD', np.allclose(z[:, g_macd], [100.0, 200.0, 200.0]))
    ok('ts', np.allclose(out, [121.0, 202.0, 210.0]))
    # streaming across two parts must equal one part
    out2 = np.zeros(3); z2 = np.zeros((3, F.r))
    F.predict_parts([(M[:, :1], cols[:1]), (M[:, 1:], cols[1:])], lut, out=out2, z_out=z2)
    ok('z streaming equals single part', np.allclose(z2, z) and np.allclose(out2, out))

# ------------------------------------------------- 2) strategy map varies by state
def test_surface_state_dependence():
    rng = np.random.default_rng(3)
    n = 400
    cells = np.array([[m, h, s] for m in (2, 30) for s in (0, 5) for h in (1, 15)], np.int16)
    rf = np.stack([cells[:, 0] / 30.0, cells[:, 1] / 30.0, cells[:, 2] / 30.0,
                   (cells[:, 2] == 0).astype(np.float32)], 1).astype(np.float32)
    # two trade groups: z = +1/-1 in the single group; W tilts EV toward cell (30,15,0) for z>0
    z = np.where(np.arange(n) < n // 2, 1.0, -1.0)[:, None]
    W = np.array([[0.5, 0.5, 0.0, 8.0]], np.float64)         # m, h, -, s_none: unique argmax
    # realised returns: group +1 wins big with (30,15,0) [cell 6]; group -1 wins with (2,1,5) [cell 1]
    best_idx = np.where(z[:, 0] > 0, 6, 1)                        # index into cells
    # build pre_d with tp/sl arrays so rule_ret_mat gives the realised pattern
    NH = 30
    pre_d = dict(tp_day=np.full((29, n), -1, np.int16), tp_ret=np.full((29, n), np.nan, np.float32),
                 sl_day=np.full((29, n), -1, np.int16), sl_ret=np.full((29, n), np.nan, np.float32),
                 clos=np.zeros((NH, n), np.float32), didx=np.zeros(n, np.int64))
    for i in range(n):
        m, h, s = (int(v) for v in cells[best_idx[i]])
        mi = m - 2
        pre_d['tp_day'][mi, i] = 0
        pre_d['tp_ret'][mi, i] = 0.30 if s == 0 else 0.02
    class B: bench = np.zeros((29, 30, 30, 1), np.float32)
    ts = np.zeros(n)
    args = (ts, ts, np.zeros(4), np.zeros(4), 0.0, 0.0, pre_d, cells, rf, {'bench': B.bench}, 't')
    _, det_no = C.surface_summary(*args)
    cells_picked_no = set(det_no['cell'].tolist())
    _, det_yes = C.surface_summary(*args, z=dict(l=z, r=z), W_l=W, W_r=W)
    picked = cells[det_yes['cell']]
    grp_pos = z[:, 0] > 0
    ok('additive: one global cell', len(cells_picked_no) == 1)
    ok('A1: pos group picks s_none', all(picked[grp_pos, 2] == 0))
    ok('A1: neg group picks stop=5', all(picked[~grp_pos, 2] == 5))
    ok('A1: realised EV positive', det_yes['ev'].mean() > 0)

# ------------------------------------------------------- 3) fit recovers interaction
def test_fit_recovers_W():
    rng = np.random.default_rng(11)
    n_tr, n_q = 300, 4
    cols = ['RSI14|a|1d|5', 'RSI14|b|1d|5', 'MACD|c|1d|5', 'ATR14|d|1d|5']   # 3 groups
    M = rng.integers(-1, 2, (n_tr, n_q)).astype(np.int8)
    M[ M == 2 ] = 0
    parts = [(M, cols)]
    F = C.Featurizer(cols); F.fit(parts)
    n_cells = 12
    cells = np.tile(np.array([[20, 15, 0]], np.int16), (n_cells, 1))
    rf = np.stack([cells[:, 0] / 30.0, cells[:, 1] / 30.0, cells[:, 2] / 30.0,
                   (cells[:, 2] == 0).astype(np.float32)], 1).astype(np.float32)
    tidx = np.repeat(np.arange(n_tr), 2)
    cid = rng.integers(0, n_cells, len(tidx))
    g_rsi = F.group_names.index('RSI14')
    z_true = (M[:, 0] == 1).astype(float) * 2 - 1                     # +/-1 by first RSI answer
    ret = np.where(rf[cid][:, 3] > 0, z_true[tidx] * 0.1, -z_true[tidx] * 0.05).astype(np.float32)
    _, _, _, hist_add, W_add = C.fit_model(F, parts, tidx, cid, ret, cells, rf, iters=80, target='ridge', interactions=False)
    _, _, _, hist_int, W_int = C.fit_model(F, parts, tidx, cid, ret, cells, rf, iters=80, target='ridge', interactions=True)
    ok('interactions lower loss', hist_int[-1] < hist_add[-1] * 0.7)
    ok('W estimated', W_int is not None and abs(W_int[g_rsi, 3]) > 0.5)
    ok('additive W is None', W_add is None)

test_z_accum(); test_surface_state_dependence(); test_fit_recovers_W()
n_fail = sum(1 for _, c in PASS if not c)
print(f'COMBINE INTERACTION TESTS {"PASS" if not n_fail else "FAIL"} ({len(PASS)-n_fail}/{len(PASS)} passed)')
sys.exit(1 if n_fail else 0)

"""Viewport recipes for the single-stock TradingView-style display (METHODOLOGY §0b #149/#155/#159).

Every recipe is a pure function over daily OHLCV numpy arrays with a cutoff index:

    recipe(dates, O, H, L, C, V, cutoff) -> dict

where bars 0..cutoff (inclusive) are the only bars knowable at the setup date
(candle end < setup date S). Day-S data is never read: the caller passes cutoff
= last bar with date < S.

Return dict:
    id       recipe id (e.g. 'VIEW_RG_COUNT_5D')
    status   'READY' | 'DISABLED'
    blocker  str, only when DISABLED (shown in the picker, never drawn)
    label    measured-quantity sentence for the on-chart label box
    answer   str answer line (may be '' when blank/not applicable)
    binary   list of derived strict YES/NO questions (§0b 2026-10-29 22:51/23:05):
             [{'qid': '<recipe>/<rung>', 'q': '<feature + comparator + literal threshold>',
               'a': 'YES' | 'NO' | 'NOT_EVALUABLE'}]. A blank feature -> binary = None
             (every derived question is NOT_EVALUABLE, never silently NO).
    ops      list of drawing primitives, all in bar-index space:
        {'op': 'recolour', 'bars': [i, ...]}                purple candles + volume bars
        {'op': 'vband', 'i0': a, 'i1': b}                 light-purple band behind bars a..b
        {'op': 'hlines', 'levels': [(price, 'label'), ...]}
        {'op': 'dots', 'pts': [(i, price, 'label'), ...]}
        {'op': 'polyline', 'pts': [(i, price), ...]}
        {'op': 'vline_cutoff': True}                      dashed cutoff marker (always added by renderer)

Colour rule everywhere: red iff close < open, green iff close > open, doji
(close == open) is neither. One reading only — anything with two readings is
flagged AMBIGUOUS and not drawn (#155/#156).
"""
import numpy as np

READY = 'READY'
DISABLED = 'DISABLED'

RED, GREEN, PURPLE = 'red', 'green', 'purple'


# ---------------------------------------------------------------- helpers
def _window(cutoff, n):
    """indices of the nearest n completed bars ending at cutoff, inclusive."""
    return np.arange(max(0, cutoff - n + 1), cutoff + 1)


def _colours(O, C):
    """per-bar colour: red close<open, green close>open, doji neither -> '' ."""
    out = np.where(C < O, RED, np.where(C > O, GREEN, ''))
    return out


def _res(id_, label, answer='', ops=(), status=READY, blocker='', binary=()):
    return dict(id=id_, status=status, blocker=blocker, label=label,
                answer=answer, ops=list(ops),
                binary=None if binary is None else list(binary))


def _blank(id_, label, reason):
    return _res(id_, label, answer=f'blank ({reason})', ops=[], binary=None)


def _yn(cond):
    return 'YES' if cond else 'NO'


def _bq(qid, q, a):
    return {'qid': qid, 'q': q, 'a': a}


# ---------------------------------------------------------------- 1. mockup: red:green COUNT, nearest 5
def view_rg_count_5d(dates, O, H, L, C, V, cutoff):
    id_ = 'VIEW_RG_COUNT_5D'
    label = ('Red:green candle COUNT ratio, nearest 5 completed daily candles '
             '(red iff close<open, green iff close>open, doji counts as neither)')
    w = _window(cutoff, 5)
    if len(w) < 5:
        return _blank(id_, label, 'fewer than 5 completed bars before cutoff')
    col = _colours(O[w], C[w])
    r = int((col == RED).sum()); g = int((col == GREEN).sum())
    doji = 5 - r - g
    ans = f'R:G = {r}:{g}' + (f' (doji {doji})' if doji > 0 else '')
    binary = [
        _bq(f'{id_}/red_majority', 'red majority of nearest 5 completed daily candles '
            '(red_count > green_count; doji counts as neither)?', _yn(r > g)),
        _bq(f'{id_}/red_gt_4', 'red_count of nearest 5 completed daily candles > 4?', _yn(r > 4)),
        _bq(f'{id_}/red_ge_3', 'red_count of nearest 5 completed daily candles >= 3?', _yn(r >= 3)),
        _bq(f'{id_}/green_ge_1', 'green_count of nearest 5 completed daily candles >= 1?', _yn(g >= 1)),
    ]
    return _res(id_, label, ans, [
        {'op': 'vband', 'i0': int(w[0]), 'i1': int(w[-1])},
        {'op': 'recolour', 'bars': [int(i) for i in w]},
    ], binary=binary)


# ---------------------------------------------------------------- 1b. red:green EXACT-candle recolour example (§0b 22:45 #163)
def view_rg_exact_5d(dates, O, H, L, C, V, cutoff):
    """Same R:G measurement as mockup 1, but only the exact qualifying candles
    are recoloured purple (never circled): the majority-colour candles are the
    evidence set. Tie or all-doji -> no exact recolour (window band only)."""
    id_ = 'VIEW_RG_EXACT_5D'
    label = ('Red:green EXACT-candle recolour example (§0b 22:45 #163): nearest 5 completed daily '
             'candles; the candles of the majority colour (the answer evidence) are recoloured '
             'purple exactly — no circles, no whole-window recolour; doji counts as neither')
    w = _window(cutoff, 5)
    if len(w) < 5:
        return _blank(id_, label, 'fewer than 5 completed bars before cutoff')
    col = _colours(O[w], C[w])
    r = int((col == RED).sum()); g = int((col == GREEN).sum())
    doji = 5 - r - g
    ans = f'R:G = {r}:{g}' + (f' (doji {doji})' if doji > 0 else '')
    if r > g:
        exact = [int(i) for i, c in zip(w, col) if c == RED]
        ans += f' — exact recolour: {r} red candle(s) (majority evidence)'
    elif g > r:
        exact = [int(i) for i, c in zip(w, col) if c == GREEN]
        ans += f' — exact recolour: {g} green candle(s) (majority evidence)'
    else:
        exact = []
        ans += ' — tie, no majority-colour evidence candles (window band only)'
    binary = [
        _bq(f'{id_}/red_majority', 'red majority of nearest 5 completed daily candles '
            '(red_count > green_count; doji counts as neither)?', _yn(r > g)),
        _bq(f'{id_}/red_gt_4', 'red_count of nearest 5 completed daily candles > 4?', _yn(r > 4)),
        _bq(f'{id_}/red_ge_3', 'red_count of nearest 5 completed daily candles >= 3?', _yn(r >= 3)),
        _bq(f'{id_}/green_ge_1', 'green_count of nearest 5 completed daily candles >= 1?', _yn(g >= 1)),
    ]
    ops = [{'op': 'vband', 'i0': int(w[0]), 'i1': int(w[-1])}]
    if exact:
        ops.append({'op': 'recolour', 'bars': exact})
    return _res(id_, label, ans, ops, binary=binary)


# ---------------------------------------------------------------- 2. mockup: Fib from window HH/LL, 60d
FIB_RATIOS = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)


def view_fib_hhll_60d(dates, O, H, L, C, V, cutoff):
    id_ = 'VIEW_FIB_HHLL_60D'
    label = ('Fibonacci retracement of the past 60 daily bars from window highest-high to lowest-low '
             '(H = max(high), L = min(low), ties -> most recent bar)')
    w = _window(cutoff, 60)
    if len(w) < 60:
        return _blank(id_, label, 'fewer than 60 completed bars before cutoff')
    Hw, Lw = H[w], L[w]
    hi = int(w[np.argmax(Hw)])          # argmax returns FIRST max -> most recent tie is rightmost,
    hi = int(w[len(Hw) - 1 - np.argmax(Hw[::-1])])   # so scan reversed for the rightmost
    lo = int(w[len(Lw) - 1 - np.argmin(Lw[::-1])])
    Hp, Lp = float(H[hi]), float(L[lo])
    R = Hp - Lp
    if R == 0:
        return _blank(id_, label, 'H == L, range is zero')
    levels = [(Hp - r * R, f'{r:.3f}' if r not in (0.0, 0.5, 1.0) else f'{r:g}') for r in FIB_RATIOS]
    pct = (Hp - float(C[cutoff])) / R
    # adjacent levels bracketing cutoff close
    below = [lv for lv in FIB_RATIOS if Hp - lv * R >= C[cutoff]]
    above = [lv for lv in FIB_RATIOS if Hp - lv * R <= C[cutoff]]
    lo_r = max(below) if below else 0.0
    hi_r = min(above) if above else 1.0
    ans = (f'H={Hp:.4g} L={Lp:.4g} pct={(pct * 100):.1f}% '
           f'bracket [{hi_r:g}..{lo_r:g}]')
    binary = [
        _bq(f'{id_}/lower_half', 'cutoff close in lower half of the 60d HH/LL range '
            '(pct = (H - close) / (H - L) >= 0.5)?', _yn(pct >= 0.5)),
        _bq(f'{id_}/deep_retrace', 'deep retracement into the 60d range '
            '(pct >= 0.618)?', _yn(pct >= 0.618)),
        _bq(f'{id_}/near_high', 'cutoff close near the 60d window high '
            '(pct <= 0.236)?', _yn(pct <= 0.236)),
    ]
    ops = [{'op': 'recolour', 'bars': [hi, lo]},
           {'op': 'hlines', 'levels': levels},
           {'op': 'shade_between', 'p0': Hp - lo_r * R, 'p1': Hp - hi_r * R}]
    return _res(id_, label, ans, ops, binary=binary)


# ---------------------------------------------------------------- 3. mockup: three descending swing highs
def _swing_highs(H, cutoff, side=5):
    """confirmable swing highs up to cutoff: bar i with high[i] = max(high[i-side..i+side]);
    ties -> leftmost pivot. Confirmable iff i+side <= cutoff. Returns list of bar indices, time order."""
    out = []
    upto = min(len(H) - side, cutoff - side + 1)
    for i in range(side, upto):
        win = H[i - side:i + side + 1]
        if H[i] == win.max():
            out.append(i)          # argmax semantics: first max wins -> leftmost on ties
    return out


def view_lower_swing_highs_3(dates, O, H, L, C, V, cutoff):
    id_ = 'VIEW_LOWER_SWING_HIGHS_3'
    label = ('Three descending fractal swing highs (pivot = unique window max of 11 bars, L=5 each side, '
             'ties -> leftmost; confirmable when i+5 <= cutoff)')
    if cutoff < 10:
        return _blank(id_, label, 'not enough bars to confirm pivots before cutoff')
    sh = _swing_highs(H, cutoff)
    pts = [(i, float(H[i]), f'{float(H[i]):.4g}') for i in sh[-3:]]
    if len(sh) < 3:
        ans = f'NOT_EVALUABLE (need 3 confirmable swing highs, have {len(sh)})'
        a = 'NOT_EVALUABLE'
    elif H[sh[-3]] > H[sh[-2]] > H[sh[-1]]:
        ans = f'YES ({float(H[sh[-3]]):.4g} > {float(H[sh[-2]]):.4g} > {float(H[sh[-1]]):.4g})'
        a = 'YES'
    else:
        ans = (f'NO (last 3 highs {float(H[sh[-3]]):.4g}, {float(H[sh[-2]]):.4g}, '
               f'{float(H[sh[-1]]):.4g} not strictly descending)')
        a = 'NO'
    binary = [_bq(f'{id_}/descending_3',
                  'last 3 confirmable fractal swing highs (L=5, ties -> leftmost) '
                  'each strictly lower than the previous '
                  '(high[H1] > high[H2] > high[H3])?', a)]
    ops = [{'op': 'dots', 'pts': pts},
           {'op': 'polyline', 'pts': [(i, p) for i, p, _ in pts]}]
    return _res(id_, label, ans, ops, binary=binary)


# ---------------------------------------------------------------- 4. mockup: volume today vs mean of last 20
def view_vol_vs_mean_20d(dates, O, H, L, C, V, cutoff):
    id_ = 'VIEW_VOL_VS_MEAN_20D'
    label = ('Volume today vs mean of last 20 completed daily bars (base INCLUDES cutoff bar): '
             'ratio = V_cutoff / mean(V over cutoff-19..cutoff)')
    w = _window(cutoff, 20)
    if len(w) < 20:
        return _blank(id_, label, 'fewer than 20 completed bars before cutoff')
    vw = V[w].astype(float)
    if not np.isfinite(vw).all():
        return _blank(id_, label, 'missing/nonfinite volume in the 20-bar base')
    m = float(vw.mean())
    if m == 0:
        return _blank(id_, label, 'base mean volume is zero')
    ratio = float(V[cutoff]) / m
    ans = f'V={int(V[cutoff])} mean20={m:.1f} ratio={ratio:.3f}'
    binary = [
        _bq(f'{id_}/above_mean', 'cutoff volume above its 20d mean '
            '(V_cutoff / mean20 > 1; base includes cutoff bar)?', _yn(ratio > 1)),
        _bq(f'{id_}/heavy', 'cutoff volume more than double its 20d mean (ratio > 2)?', _yn(ratio > 2)),
        _bq(f'{id_}/spike', 'cutoff volume more than triple its 20d mean (ratio > 3)?', _yn(ratio > 3)),
    ]
    return _res(id_, label, ans, [
        {'op': 'recolour_vol', 'bars': [int(i) for i in w]},
        {'op': 'hlines', 'levels': [(m, '20d avg (incl. today)')]},
    ], binary=binary)


# ---------------------------------------------------------------- 5. lower_highs10 (pinned chart picture)
def lower_highs10(dates, O, H, L, C, V, cutoff):
    id_ = 'lower_highs10'
    label = ('lower_highs10: count of bars in the last 10 completed daily bars with '
             'High < High of the immediately preceding bar')
    w = _window(cutoff, 10)
    if w[0] < 1:      # need the bar before the window for the first comparison
        return _blank(id_, label, 'fewer than 11 completed bars before cutoff')
    hits = [int(i) for i in w if H[i] < H[i - 1]]
    ans = f'count = {len(hits)} / 10'
    k = len(hits)
    binary = [
        _bq(f'{id_}/ge_5', 'at least half of the last 10 completed daily bars are lower highs '
            '(count of High[i] < High[i-1] >= 5)?', _yn(k >= 5)),
        _bq(f'{id_}/ge_8', 'at least 8 of the last 10 completed daily bars are lower highs '
            '(count >= 8)?', _yn(k >= 8)),
        _bq(f'{id_}/all_10', 'all of the last 10 completed daily bars are lower highs '
            '(count = 10)?', _yn(k == 10)),
    ]
    return _res(id_, label, ans, [{'op': 'recolour', 'bars': hits}], binary=binary)


# ---------------------------------------------------------------- 6. cp_gr_body20 (pinned chart picture)
def cp_gr_body20(dates, O, H, L, C, V, cutoff):
    id_ = 'cp_gr_body20'
    label = ('cp_gr_body20 BODY-SUM ratio (not candle count): sum of green |close-open| bodies / '
             'sum of red |close-open| bodies over the last 20 completed daily bars; '
             'green iff close>open, red iff close<open, doji in neither sum')
    w = _window(cutoff, 20)
    if len(w) < 20:
        return _blank(id_, label, 'fewer than 20 completed bars before cutoff')
    body = np.abs(C[w] - O[w])
    g = body[C[w] > O[w]].sum()
    r = body[C[w] < O[w]].sum()
    q = ('green absolute-body sum > red absolute-body sum over the last 20 completed '
         'daily bars (body-sum ratio > 1; doji in neither sum)?')
    if r == 0 and g == 0:
        ans = 'green=0 red=0 ratio undefined (all doji)'
        binary = [_bq(f'{id_}/gt_1', q, 'NOT_EVALUABLE')]
    elif r == 0:
        ans = f'green={g:.4g} red=0 ratio=inf'
        binary = [_bq(f'{id_}/gt_1', q, 'YES')]      # infinite ratio per §0 ratio rule
    else:
        ans = f'green={g:.4g} red={r:.4g} ratio={g / r:.3f}'
        binary = [_bq(f'{id_}/gt_1', q, _yn(g > r))]
    return _res(id_, label, ans, [{'op': 'recolour', 'bars': [int(i) for i in w]}],
                binary=binary)


# ---------------------------------------------------------------- 7. C22 / I080 RVOL20
def rvol20(dates, O, H, L, C, V, cutoff):
    id_ = 'RVOL20'
    label = ('RVOL20: V_cutoff / SMA20(volume over the 20 bars STRICTLY before cutoff, today excluded); '
             'spike iff RVOL > 3')
    if cutoff < 20:
        return _blank(id_, label, 'fewer than 21 completed bars before cutoff')
    base = V[cutoff - 20:cutoff].astype(float)
    if not np.isfinite(base).all() or base.mean() == 0:
        return _blank(id_, label, 'base volumes missing or zero mean')
    sma = float(base.mean())
    rv = float(V[cutoff]) / sma
    ans = f'RVOL={rv:.3f} ({"spike" if rv > 3 else "no spike"})  cutoff V={int(V[cutoff])} SMA20(prior)={sma:.1f}'
    binary = [
        _bq(f'{id_}/spike', 'volume spike at cutoff (RVOL = V_cutoff / SMA20(prior 20, '
            'today excluded) > 3)?', _yn(rv > 3)),
        _bq(f'{id_}/elevated', 'elevated volume at cutoff (RVOL > 1.5)?', _yn(rv > 1.5)),
    ]
    return _res(id_, label, ans, [
        {'op': 'recolour_vol', 'bars': [cutoff]},
        {'op': 'hlines', 'levels': [(sma, 'SMA20 volume (prior 20)')]},
    ], binary=binary)


# ---------------------------------------------------------------- 8. I074 pivot points (prior calendar period)
def _prior_period_slice(dates, cutoff, period):
    """(i0, i1) bar-index slice of the PRIOR completed calendar period, or None.
    period in {'W','M','Q'} -> prior week / month / quarter, relative to cutoff's period."""
    import pandas as pd
    d = pd.DatetimeIndex(dates[:cutoff + 1])
    dc = d[cutoff]
    if period == 'W':
        cur_start = dc - pd.Timedelta(days=dc.weekday())          # Monday of cutoff week
    elif period == 'M':
        cur_start = dc.replace(day=1)
    else:
        q = (dc.month - 1) // 3
        cur_start = pd.Timestamp(dc.year, q * 3 + 1, 1)
    prev_end = cur_start - pd.Timedelta(days=1)
    if period == 'W':
        prev_start = prev_end - pd.Timedelta(days=prev_end.weekday())
    elif period == 'M':
        prev_start = prev_end.replace(day=1)
    else:
        pq = (prev_end.month - 1) // 3
        prev_start = pd.Timestamp(prev_end.year, pq * 3 + 1, 1)
    m = (d >= prev_start) & (d <= prev_end)
    idx = np.where(m)[0]
    return (int(idx[0]), int(idx[-1])) if len(idx) else None


def i074_pivots(dates, O, H, L, C, V, cutoff, period='M'):
    id_ = 'I074_PIVOTS_STD'
    label = (f'I074 Pivot Points Standard, prior completed calendar { {"W":"week","M":"month","Q":"quarter"}[period] }: '
             'P=(H+L+C)/3, R1=2P-L, S1=2P-H, R2=P+(H-L), S2=P-(H-L) '
             '(H=max high wick, L=min low wick, C=final session close of that period)')
    sl = _prior_period_slice(dates, cutoff, period)
    if sl is None:
        return _blank(id_, label, 'prior period has no completed bars before cutoff')
    i0, i1 = sl
    Hp, Lp, Cp = float(H[i0:i1 + 1].max()), float(L[i0:i1 + 1].min()), float(C[i1])
    P = (Hp + Lp + Cp) / 3
    lv = [(P, 'P'), (2 * P - Lp, 'R1'), (2 * P - Hp, 'S1'), (P + (Hp - Lp), 'R2'), (P - (Hp - Lp), 'S2')]
    ans = f'P={P:.4g} R1={lv[1][0]:.4g} S1={lv[2][0]:.4g} R2={lv[3][0]:.4g} S2={lv[4][0]:.4g}'
    cc = float(C[cutoff])
    per = {"W": "week", "M": "month", "Q": "quarter"}[period]
    binary = [
        _bq(f'{id_}/above_p', f'cutoff close above the prior {per} standard pivot '
            f'(close > P = (H+L+C)/3)?', _yn(cc > P)),
        _bq(f'{id_}/above_r1', f'cutoff close above the prior {per} R1 (close > R1 = 2P - L)?',
            _yn(cc > lv[1][0])),
        _bq(f'{id_}/below_s1', f'cutoff close below the prior {per} S1 (close < S1 = 2P - H)?',
            _yn(cc < lv[2][0])),
    ]
    return _res(id_, label, ans, [{'op': 'hlines', 'levels': lv}], binary=binary)


# ---------------------------------------------------------------- 9. I101 Donchian(20)
def i101_donchian20(dates, O, H, L, C, V, cutoff):
    id_ = 'I101_DONCHIAN20'
    label = ('I101 Donchian(20): Upper = max(high) of the prior 20 bars (cutoff EXCLUDED), '
             'Lower = min(low) of the prior 20; mid = average; most-recent-bar tie wins')
    if cutoff < 20:
        return _blank(id_, label, 'fewer than 21 completed bars before cutoff')
    w = np.arange(cutoff - 20, cutoff)          # strictly before cutoff
    Hw, Lw = H[w], L[w]
    up, dn = float(Hw.max()), float(Lw.min())
    i_up = int(w[len(Hw) - 1 - np.argmax(Hw[::-1])])   # most recent tie
    i_dn = int(w[len(Lw) - 1 - np.argmin(Lw[::-1])])
    mid = (up + dn) / 2
    ans = f'upper={up:.4g} lower={dn:.4g} mid={mid:.4g}'
    cc = float(C[cutoff])
    binary = [
        _bq(f'{id_}/breakout_up', 'cutoff close above the prior-20 Donchian upper '
            '(close > max(high) of the 20 bars strictly before cutoff)?', _yn(cc > up)),
        _bq(f'{id_}/breakdown', 'cutoff close below the prior-20 Donchian lower '
            '(close < min(low) of the 20 bars strictly before cutoff)?', _yn(cc < dn)),
    ]
    return _res(id_, label, ans, [
        {'op': 'hlines', 'levels': [(up, 'upper20'), (dn, 'lower20'), (mid, 'mid')]},
        {'op': 'recolour', 'bars': [i_up, i_dn]},
    ], binary=binary)


# ---------------------------------------------------------------- 10. chart-shape similarity (#158) — DISABLED stub
def chart_shape_similarity(dates, O, H, L, C, V, cutoff):
    return _res(
        'CHART_SHAPE_SIMILARITY',
        'Chart-shape similarity + side-by-side (§0b #158): window = last N candles at timeframe Y '
        'ending at the setup-date open-knowable bar; shape = closes min-max normalised to 0-1; '
        'match iff Pearson correlation > 0.90 strictly; pool = all stocks, windows ending strictly '
        'before setup date.',
        status=DISABLED,
        blocker='GPT owns the N/Y/K grid (§0b #158 / VIEWPORT_READY_FOR_KIMI_V1); Kimi must not invent N, Y or K. '
                'Stubbed in the picker as disabled until GPT finalises the grid.',
        binary=None)   # switched off: #161 requires similarity>0.90 as YES/NO questions before mining


# ---------------------------------------------------------------- registry
PICKER = [
    ('VIEW_RG_COUNT_5D', 'Red:green candle count, nearest 5 daily candles (mockup 1)', view_rg_count_5d),
    ('VIEW_RG_EXACT_5D', 'Red:green EXACT-candle purple recolour example, nearest 5 (§0b 22:45 #163)', view_rg_exact_5d),
    ('VIEW_FIB_HHLL_60D', 'Fibonacci retracement, past 60 daily bars, HH/LL anchors (mockup 2)', view_fib_hhll_60d),
    ('VIEW_LOWER_SWING_HIGHS_3', 'Three descending fractal swing highs, L=5 (mockup 3)', view_lower_swing_highs_3),
    ('VIEW_VOL_VS_MEAN_20D', 'Volume today vs mean of last 20 daily bars, inclusive base (mockup 4)', view_vol_vs_mean_20d),
    ('lower_highs10', 'lower_highs10: count of lower highs in last 10 bars (pinned chart picture)', lower_highs10),
    ('cp_gr_body20', 'cp_gr_body20: green/red body-SUM ratio over 20 bars (pinned chart picture)', cp_gr_body20),
    ('RVOL20', 'C22/I080 RVOL20: cutoff volume vs SMA20 of prior 20 (today excluded)', rvol20),
    ('I074_PIVOTS_STD', 'I074 Pivot Points Standard, prior calendar week/month/quarter', i074_pivots),
    ('I101_DONCHIAN20', 'I101 Donchian(20): prior-20 upper/lower/mid', i101_donchian20),
    ('CHART_SHAPE_SIMILARITY', 'Chart-shape similarity + side-by-side (#158, GPT owns grid)', chart_shape_similarity),
]

# DO_NOT_DRAW rows that are not recipes at all: shown in the picker as disabled static entries
DO_NOT_DRAW_STATIC = [
    ('I076_AUTO_FIB / I078_FIB_SWING', 'ZZ(3ATR) confirmation / freeze rules not bound to one viewport reading; use VIEW_FIB_HHLL_60D'),
    ('I111 / I117 / I202 / I203', 'explicitly vague in #149 wake note'),
    ('cp_* (other tags)', 'draw only when pinned field + viewport_draw are both present'),
    ('question-tree template families', '~10.7k questions lack exact anchors; GPT rewrite pending'),
]

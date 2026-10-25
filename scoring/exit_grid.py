"""Exit-rule grid scoring (METHODOLOGY 0b, 2026-10-24 ~13:30 entry; spec = docs/COMBINING_PREREG.md @ kimi/pre-register 240cc7b, approved).

Grid = take-profit 2-30%% (every integer) x max hold 1-30 sessions (every value) x stop-loss 2-30%% (every integer) or none
= 29 x 30 x 30 = 26,100 rules. For every setup (question + answer) and every rule we report n, win%%, avg win, avg loss,
expected profit after fees, and the same-day benchmark, keeping the 40%% win-rate floor (35/45/50 also derivable).

Trade semantics (identical to scoring/trades.py exit_v1, extended with stops):
  buy at D's open; early sell when the target is hit (intraday touch fills AT the target, gap through fills at the open);
  stop-loss the same way with LOW; stop counts first if both are hit on the same day; otherwise sell at the close of the
  last held session (hold h). Fees 30bp each way: ret = exit*(1-FEE) / (entry*(1+FEE)) - 1.
  NOT_READY per rule: the window must cover the longest hold. Step A's base already requires a bar on every market
  session D..D+29 (OUTCOME=30), so every base trade is ready for every rule with hold <= 30 and the trade set is
  identical across the grid. Rules that never exit early (target/stop not hit within h) sell at the close of day h.

Method (per-trade first-hit-day, so the whole grid is a few passes over the data, not 26k separate runs):
  For each trade, precompute once: for each take-profit m the first hit day and net ret; for each stop s the first hit
  day and net ret; for each hold h the net ret of exiting at the close of day h. A rule (m,h,s) outcome then follows
  analytically: stop if hit within h (stop first on ties), else target if hit within h, else close of day h.
  Aggregation into setups is a float32 matmul of the (question x trade) answer matrix against the (trade x hold)
  outcome matrix, per (m,s) pair - 841 pairs, not 26,100 loops of trade math.

Splits/luck discipline (0b 13:30): tune and pick on 2020-21, check once on 2022, state-to-rule map tested once on
2023-24. The grid is exempt from per-rule luck counting ONLY under that single 2023-24 test; any claim that one
specific rule works counts every rule tried toward the bar.

Discover window only: bars are cut at 2022-12-31 before anything is computed (engine.load_bars already enforces END).
2023-24 (confirm) and 2025-26 (sealed) are never touched here.
"""
import numpy as np

FEE = 0.003
TP_PCTS = np.arange(2, 31, dtype=np.float64) / 100.0     # 29 take-profits, 0.02..0.30
SL_PCTS = np.arange(2, 31, dtype=np.float64) / 100.0     # 29 stop-losses, 0.02..0.30 (rule 'none' handled separately)
HOLDS = np.arange(1, 31)                                  # 30 max holds, 1..30 sessions
MAXH = 30
NTP, NSL, NH = len(TP_PCTS), len(SL_PCTS), len(HOLDS)


def net_ret(entry, exit_):
    return exit_ * (1 - FEE) / (entry * (1 + FEE)) - 1


def first_hits(o, h, l, c, pcts, side):
    """Per-entry first-hit day and net ret for a grid of targets. Entry i buys at o[i]; scans bars i..i+MAXH-1
    (callers guarantee MAXH consecutive bars exist). side '+': target hit when high >= entry*(1+p) (gap: open >= it,
    fills at open; else fills at the target). side '-': stop hit when low <= entry*(1-p) (gap: open <= it, fills at
    open; else fills at the stop). Entry day (offset 0) can be stopped/targeted intraday but cannot gap (we bought at
    its open). Returns (day, ret) each (len(pcts), n_entries); day -1 = never hit within MAXH bars."""
    n = len(o) - MAXH + 1
    if n <= 0:
        z = np.zeros((len(pcts), 0))
        return z.astype(np.int16), z.astype(np.float32)
    from numpy.lib.stride_tricks import sliding_window_view as SW
    O, H, L = SW(o, MAXH)[:n], SW(h, MAXH)[:n], SW(l, MAXH)[:n]
    e = o[:n]
    days = np.full((len(pcts), n), -1, np.int16)
    rets = np.full((len(pcts), n), np.nan, np.float32)
    r = np.arange(n)
    for k, p in enumerate(pcts):
        t = e * (1 + p if side == '+' else 1 - p)
        if side == '+':
            gap = O >= t[:, None]; touch = H >= t[:, None]
        else:
            gap = O <= t[:, None]; touch = L <= t[:, None]
        gap[:, 0] = False                                  # entry day can't gap through its own open
        hit = gap | touch
        any_ = hit.any(1)
        j = np.where(any_, hit.argmax(1), 0)
        px = np.where(gap[r, j], O[r, j], t)               # gap fills at open, touch fills at the target/stop price
        days[k, any_] = j[any_].astype(np.int16)
        rets[k, any_] = net_ret(e[any_], px[any_]).astype(np.float32)
    return days, rets


def close_rets(o, c):
    """(NH, n) net ret of exiting at the close of day h (offset h-1), h = 1..MAXH."""
    n = len(o) - MAXH + 1
    if n <= 0:
        return np.zeros((NH, 0), np.float32)
    from numpy.lib.stride_tricks import sliding_window_view as SW
    Cc = SW(c, MAXH)[:n]
    e = o[:n]
    return net_ret(e[None, :], Cc.T).astype(np.float32)    # (MAXH, n): row h-1 = close of day h


def rule_ret_mat(tp_day, tp_ret, sl_day, sl_ret, clos, sl_none=False):
    """(NH, n) net ret for one (m, s) pair across all holds. tp_day/sl_day are int16 (-1 = not hit within MAXH),
    tp_ret/sl_ret float32 (nan when not hit), clos (NH, n) close_rets. Stop counts first on same-day ties.
    sl_none=True = the 'no stop' rule. Rows are holds 1..MAXH (row index = h-1)."""
    a, ar = tp_day.astype(np.int32), tp_ret
    b, br = (np.full_like(a, -1), np.full_like(ar, np.nan)) if sl_none else (sl_day.astype(np.int32), sl_ret)
    hh = np.arange(1, MAXH + 1, dtype=np.int32)[:, None]   # (NH,1)
    a_hit = (a >= 0) & (a < hh)                            # target hit on/before day h (day index 0-based)
    b_hit = (b >= 0) & (b < hh)
    stop_first = b_hit & (~a_hit | (b <= a))               # stop hit within h and (target not, or stop same/earlier day)
    tgt_first = a_hit & ~stop_first
    out = np.where(stop_first, br[None, :], np.where(tgt_first, ar[None, :], clos))
    return out.astype(np.float32)


def rule_exit_day(tp_day, sl_day, h, sl_none=False):
    """Exit session (1-based, like trades.py exit_day) for one hold h; h when neither hits within the hold."""
    a = tp_day.astype(np.int32)
    b = np.full_like(a, -1) if sl_none else sl_day.astype(np.int32)
    a_hit = (a >= 0) & (a < h)
    b_hit = (b >= 0) & (b < h)
    stop_first = b_hit & (~a_hit | (b <= a))
    return np.where(stop_first, b + 1, np.where(a_hit, a + 1, h)).astype(np.int16)


def aggregate(G, ret_mat, bench_mat, ans_counts):
    """G: (Q, n) float32 answer matrix (1.0 where the trade answers the question with this code, else 0).
    ret_mat: (NH, n) rule net rets. bench_mat: (NH, n) per-trade same-day benchmark for the same rule.
    ans_counts: (Q, n)... not used - counts come from G itself. Returns dict of (Q, NH) matrices:
    n, sum_ret, win_cnt, win_sum, sum_bench. win = ret > 0 (fees already inside ret)."""
    n = np.asarray(G.sum(1))
    sum_ret = G @ ret_mat.T                                 # (Q, NH)
    win = (ret_mat > 0).astype(np.float32)
    win_cnt = G @ win.T
    win_sum = G @ np.where(ret_mat > 0, ret_mat, 0.0).T
    sum_bench = G @ bench_mat.T
    return dict(n=n, sum_ret=sum_ret, win_cnt=win_cnt, win_sum=win_sum, sum_bench=sum_bench)


if __name__ == '__main__':
    # --- synthetic checks -------------------------------------------------
    rng = np.random.default_rng(7)
    T = 400
    o = 100 * np.cumprod(1 + rng.normal(0, 0.02, T))
    h = o * (1 + abs(rng.normal(0, 0.01, T))); l = o * (1 - abs(rng.normal(0, 0.01, T)))
    c = o * (1 + rng.normal(0, 0.005, T))

    # rule (20%, 15d, no stop) must reproduce scoring/trades.py exit_v1 exactly
    from scoring import trades as TR
    rv, ed = TR.exit_v1(o, h, c)
    tpd, tpr = first_hits(o, h, l, c, np.array([0.20]), '+')
    cl = close_rets(o, c)
    rm = rule_ret_mat(tpd[0], tpr[0], None, None, cl, sl_none=True)[14]      # hold 15 -> row 14
    rd = rule_exit_day(tpd[0], None, 15, sl_none=True)
    n = len(rm)        # trades with a full 30-bar window (the grid's universe); exit_v1's first n entries match
    ok = (np.allclose(rm, rv[:n], atol=1e-9, equal_nan=True) and np.array_equal(rd, ed[:n]))
    assert ok, (rm[:n] - rv[:n], rd[:n], ed[:n])
    print('exit_v1 reproduction OK (20% / 15d / no stop)')

    # stop counts first on same-day tie: craft bars where day 3 hits both target and stop
    o2 = np.full(40, 100.0); h2 = o2.copy(); l2 = o2.copy()
    h2[3] = 115.0; l2[3] = 85.0                      # day index 3 (4th session): both +15%% high and -15%% low
    tpd2, tpr2 = first_hits(o2, h2, l2, o2.copy(), np.array([0.15]), '+')
    sld2, slr2 = first_hits(o2, h2, l2, o2.copy(), np.array([0.15]), '-')
    assert tpd2[0, 0] == 3 and sld2[0, 0] == 3
    rm2 = rule_ret_mat(tpd2[0], tpr2[0], sld2[0], slr2[0], close_rets(o2, o2.copy()))[9]   # hold 10
    assert abs(rm2[0] - slr2[0, 0]) < 1e-12 and rm2[0] < 0, 'stop must win the tie'
    rm2b = rule_ret_mat(tpd2[0], tpr2[0], sld2[0], slr2[0], close_rets(o2, o2.copy()), sl_none=True)[9]
    assert abs(rm2b[0] - tpr2[0, 0]) < 1e-12, 'without a stop the target fills'
    print('same-day stop-first tie OK')

    # gap through stop fills at the open: day 1 opens at 90 (-10%%), never trades there intraday... low must also be <= stop;
    # gap through target fills at open
    o3 = np.full(40, 100.0); h3 = o3 * 1.001; l3 = o3 * 0.999
    o3[2] = 130.0                                    # gaps up through +25%%
    tpd3, tpr3 = first_hits(o3, h3, l3, o3.copy(), np.array([0.25]), '+')
    assert tpd3[0, 0] == 2 and abs(tpr3[0, 0] - (130 * .997 / (100 * 1.003) - 1)) < 1e-12
    print('gap-through-target fill at open OK')

    # hold truncation: target beyond the hold exits at the close of day h
    rm4 = rule_ret_mat(tpd2[0], tpr2[0], sld2[0], slr2[0], close_rets(o2, o2.copy()))[2]   # hold 3
    assert abs(rm4[0] - close_rets(o2, o2.copy())[2, 0]) < 1e-12, 'neither hit within 3 -> close of day 3'
    print('hold truncation OK')
    print('exit_grid self-checks OK')

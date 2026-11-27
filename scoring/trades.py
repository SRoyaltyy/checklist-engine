"""Trades + scoring (exit rule v1).  One row per trade:
  ticker, date (entry D), ret, bench, question_id, answer, exit_day, spy_ret, period
Trade = buy at D's open. Sell at +20% (fills at the open if the stock gaps through it), otherwise at the close of day 15
(D = day 1). Fees 30bp each way: ret = exit*(1-0.003) / (entry*(1+0.003)) - 1.
NOT_READY (censoring, same at every boundary): the case is dropped from scoring unless the stock has a bar on every market
session from D through D+29 (15-day exit + 30-day outcome) inside the window it is scored in. Catches end of data, end of the
2022 discover window, gaps and delistings. Discover window = 2020-01-02..2022-12-31; confirm = 2023..2024 (not scored in Step A).
bench = equal-weight mean ret, same day D, same exit rule, over stocks that pass the filter on D and are ready.
Scoring: group by (question_id, answer) and call James's stats/luck_check.score() (commit c2ae4fe, imported unchanged)."""
import os, sys, hashlib, subprocess, importlib.util, numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as SW
FEE = 0.003; TARGET = 0.20; HOLD = 15; OUTCOME = 30
WINDOWS = {'discover': ('2020-01-02', '2022-12-31'), 'confirm': ('2023-01-01', '2024-12-31')}
FLOORS = (0.35, 0.40, 0.45, 0.50); MAIN_FLOOR = 0.40
LUCK_COMMIT = 'c2ae4fe'; HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def luck_check():
    """Import stats/luck_check.py exactly as committed on James's branch (git object c2ae4fe), never edited."""
    p = os.path.join(HERE, 'stats', 'luck_check.py')
    if not os.path.exists(p):
        src = subprocess.run(['git', '-C', HERE, 'show', f'{LUCK_COMMIT}:stats/luck_check.py'], capture_output=True, check=True).stdout
        p = os.path.join(os.environ.get('TMPDIR', '/tmp'), f'luck_check_{LUCK_COMMIT}.py'); open(p, 'wb').write(src)
    s = importlib.util.spec_from_file_location('luck_check', p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def exit_v1(o, h, c):
    """Arrays for one ticker (consecutive sessions). Returns ret (net of fees) and exit_day per entry index (nan if < HOLD bars left)."""
    T = len(o); ret = np.full(T, np.nan); ed = np.full(T, -1, np.int16)
    if T < HOLD: return ret, ed
    n = T - HOLD + 1; O, H, Cc = SW(o, HOLD)[:n], SW(h, HOLD)[:n], SW(c, HOLD)[:n]
    e = o[:n]; tgt = e * (1 + TARGET)
    gap = O >= tgt[:, None]; gap[:, 0] = False                      # entry day can't gap through its own open
    hit = gap | (H >= tgt[:, None]); any_ = hit.any(1); j = np.where(any_, hit.argmax(1), HOLD - 1)
    r = np.arange(n); px = np.where(any_, np.where(gap[r, j], O[r, j], tgt), Cc[:, HOLD - 1])
    ret[:n] = px * (1 - FEE) / (e * (1 + FEE)) - 1; ed[:n] = j + 1
    return ret, ed

def ticker_trades(tk, d, sessions, window):
    """d: bars for one ticker (date, open, high, low, close). Returns per-D frame with ret, exit_day, ready."""
    lo, hi = map(pd.Timestamp, WINDOWS[window]); d = d[(d.date <= hi)].reset_index(drop=True)
    o, h, c = (d[x].to_numpy(float) for x in ('open', 'high', 'low', 'close') if x != 'low')
    ret, ed = exit_v1(o, h, c)
    ss = sessions[(sessions >= np.datetime64('2015-01-01')) & (sessions <= np.datetime64(hi))]
    si = np.searchsorted(ss, d.date.values); T = len(d); ok = np.zeros(T, bool)
    if T >= OUTCOME:
        i = np.arange(T - OUTCOME + 1); ok[i] = (si[i + OUTCOME - 1] - si[i] == OUTCOME - 1) & (si[i + OUTCOME - 1] < len(ss))
        ok[i] &= (ss[np.minimum(si[i], len(ss) - 1)] == d.date.values[i])     # D itself is a real market session
    good = np.isfinite(ret) & (o > 0) & np.isfinite(o)
    ok &= good
    out = pd.DataFrame(dict(ticker=tk, date=d.date.values, ret=ret, exit_day=ed, ready=ok, period=window))
    return out[(out.date >= lo) & (out.date <= hi)]

def add_bench(base, spy_bars, sessions, window):
    """base: all tickers' trades with passes_filter. bench = mean ret of filtered+ready stocks on that D; spy_ret = SPY same rule."""
    m = base.ready & base.passes_filter
    b = base[m].groupby('date').ret.mean().rename('bench')
    s = ticker_trades('SPY', spy_bars, sessions, window).set_index('date').ret.rename('spy_ret')
    return base.join(b, on='date').join(s, on='date')

def trade_rows(base, answers, question_id):
    """base: ready+filtered trades (ticker,date,ret,bench,exit_day,spy_ret,period); answers: Series aligned to base, int codes; -1 = can't answer."""
    a = np.asarray(answers); k = a >= 0
    r = base.loc[k, ['ticker', 'date', 'ret', 'bench', 'exit_day', 'spy_ret', 'period']].copy()
    r.insert(4, 'question_id', question_id); r.insert(5, 'answer', a[k]); return r

def screen_z(r, b, dates, cap=(0.5, 99.5)):
    """Cheap upper bound on luck_check.score()'s z, same clipping. score() divides by the LARGEST of naive, two-way
    clustered and bootstrap SE, and the two-way SE is >= the by-date clustered SE, so z using max(naive, by-date) SE
    can only be >= score()'s z. If this bound is below the bar, score() cannot pass."""
    x = r - b; ex = np.clip(x, *np.percentile(x, cap)); n = len(ex)
    if n < 2: return 0.0
    e = ex - ex.mean(); sn = ex.std(ddof=1) / np.sqrt(n)
    sd = np.sqrt((pd.Series(e).groupby(np.asarray(dates)).sum().to_numpy() ** 2).sum() / n ** 2)
    se = max(sn, sd); return ex.mean() / se if se > 0 else 0.0

def score_question(rows, L, bar=5.4, full_if_screen_z=3.0, min_n=30):
    """rows: trade rows for ONE question. Returns one dict per answer. score() (James) is called whenever the cheap upper-bound z >= full_if_screen_z (default 3, bar is 5.4);
    below that the pass result is already decided (fail) and only cheap stats are kept, flagged full=False."""
    out = []
    for ans, g in rows.groupby('answer'):
        n = len(g); r = g.ret.to_numpy(float); w = (r > 0).mean() if n else np.nan
        base = dict(question_id=g.question_id.iat[0], answer=int(ans), n=n, win=w, mean_ret=r.mean() if n else np.nan,
                    mean_bench=g.bench.mean(), mean_spy=g.spy_ret.mean(), avg_exit_day=g.exit_day.mean())
        if n < min_n: out.append(dict(base, full=False, z=np.nan, **{f'passes_{int(f*100)}': False for f in FLOORS})); continue
        zn = screen_z(r, g.bench.to_numpy(float), g.date.values)
        if zn >= full_if_screen_z:
            s = L.score(g, bar=bar, min_win=MAIN_FLOOR); s.pop('n'); s.pop('win'); base.update(s); base['full'] = True
            for f in FLOORS: base[f'passes_{int(f*100)}'] = bool(s['z'] >= bar and w >= f)
        else:
            base.update(z_upper=zn, z=np.nan, full=False, **{f'passes_{int(f*100)}': False for f in FLOORS})
        out.append(base)
    return out

if __name__ == '__main__':   # self-check on synthetic bars
    o = np.r_[np.full(5, 10.0), 13.0, np.full(30, 10.0)]; h = o * 1.01; c = o.copy()
    r, e = exit_v1(o, h, c); assert e[0] == 6 and abs(r[0] - (13 * .997 / (10 * 1.003) - 1)) < 1e-12, (r[0], e[0])
    o2 = np.full(40, 10.0); h2 = o2.copy(); h2[3] = 12.5; r2, e2 = exit_v1(o2, h2, o2.copy()); assert e2[0] == 4 and abs(r2[0] - (12 * .997 / 10.03 - 1)) < 1e-12
    r3, e3 = exit_v1(o2, o2.copy(), o2.copy()); assert e3[0] == 15 and abs(r3[0] - (.997 / 1.003 - 1)) < 1e-12
    print('exit_v1 self-check OK')

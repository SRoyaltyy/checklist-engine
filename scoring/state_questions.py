"""State questions for the combining model, derived straight from Step A's saved answers
(per COMBINING_PREREG.md §3 and STATE_CHANGE_PREREG.md §5):

- flip counts: how many questions changed answer for this stock since yesterday
  (bullish = 0->1, bearish = 1->0 on binary yes/no questions; any = label changed on any question)
- yesterday's move: up / down / flat from the bars (close-to-close at D-1 vs D-2)

All outputs are int8 yes/no (1 = true, 0 = false, -1 = blank) columns aligned to
trade_base_rows.parquet, so they join the world state as ordinary questions.
Streams chunk by chunk: O(one chunk) RAM.

Usage:
  CHECKLIST_DATA_DIR=... python3 scoring/state_questions.py --chunks-dir OUT/chunks \
      --out state_questions.parquet
"""
import os, sys, glob, argparse
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def col_key(col):
    """'V|f|1d|120' -> 'V|f' (base); 'H|V|hv|1d|120' -> 'V|hv' (history)."""
    p = col.split('|')
    return '|'.join(p[1:3]) if p[0] == 'H' else '|'.join(p[:2])

def binary_yesno_keys():
    """registry keys whose labels are exactly ['yes','no'] (label 1 = yes, 0 = no)."""
    from facets import REG
    return {f"{v}|{f}" for (v, f, labels, fn, lbs) in REG if list(labels) == ['yes', 'no']}

def load_cols(npz_path):
    z = np.load(npz_path)
    return z['M'], [str(c) for c in z['cols']]

def day_flip_stats(M, cols, yesno_keys, tk_sizes):
    """M: (rows, cols) int8 answers, rows sorted by (ticker, date) as in trade_base_rows.
    Counts day-over-day answer changes WITHIN each ticker. Returns int32 (rows,) stats."""
    R = M.shape[1] if M.ndim == 1 else M.shape[0]
    out_any = np.zeros(R, np.int32); out_bull = np.zeros(R, np.int32); out_bear = np.zeros(R, np.int32)
    is_bin = np.array([col_key(c) in yesno_keys for c in cols], bool)
    start = 0
    for n in tk_sizes:
        if n > 1:
            a, b = M[start:start + n - 1], M[start + 1:start + n]
            diff = (a != b) & (a >= 0) & (b >= 0)
            out_any[start + 1:start + n] = diff.sum(1)
            if is_bin.any():
                db = diff[:, is_bin]
                out_bull[start + 1:start + n] = (db & (a[:, is_bin] == 0) & (b[:, is_bin] == 1)).sum(1)
                out_bear[start + 1:start + n] = (db & (a[:, is_bin] == 1) & (b[:, is_bin] == 0)).sum(1)
        start += n
    return dict(q_flips_any=out_any, q_flips_bull=out_bull, q_flips_bear=out_bear,
                q_answered=(M >= 0).sum(1).astype(np.int32))

def yesterday_moves(bars, rows):
    """rows: (ticker,date). Yesterday's move at D = sign(close[D-1] - close[D-2]).
    Returns dict of int8 (rows,) columns: yesterday_up/down/flat (1=yes,0=no,-1=blank if
    fewer than 2 closes before D)."""
    px = bars.sort_values(['ticker', 'date'])
    px['pc'] = px.groupby('ticker').close.shift(1)
    px['ppc'] = px.groupby('ticker').close.shift(2)
    m = rows.merge(px[['ticker', 'date', 'pc', 'ppc']], on=['ticker', 'date'], how='left')
    up = np.full(len(m), -1, np.int8); dn = np.full(len(m), -1, np.int8); fl = np.full(len(m), -1, np.int8)
    ok = m.pc.notna() & m.ppc.notna()
    isup = ok & (m.pc > m.ppc); isdn = ok & (m.pc < m.ppc); isfl = ok & (m.pc == m.ppc)
    up[isup] = 1; up[ok & ~isup] = 0
    dn[isdn] = 1; dn[ok & ~isdn] = 0
    fl[isfl] = 1; fl[ok & ~isfl] = 0
    return dict(yesterday_up=up, yesterday_down=dn, yesterday_flat=fl)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks-dir', required=True); ap.add_argument('--out', default='state_questions.parquet')
    ap.add_argument('--tickers', default=None, help='optional subset smoke, e.g. AAPL,MSFT')
    a = ap.parse_args()
    os.environ.setdefault('GRID_FILE', '/nonexistent')
    import engine as E
    E.H71.load_buckets(); E.load_history(E.HISTF)
    yesno = binary_yesno_keys()
    rows = pd.read_parquet(f'{a.chunks_dir}/trade_base_rows.parquet')
    if a.tickers:
        rows = rows[rows.ticker.isin(a.tickers.split(','))]
    tk_sizes = list(rows.groupby('ticker', sort=False).size())
    acc = None
    for f in sorted(glob.glob(f'{a.chunks_dir}/answers_*.npz')):
        M, cols = load_cols(f)
        st = day_flip_stats(M, cols, yesno, tk_sizes)
        acc = st if acc is None else {k: acc[k] + st[k] for k in acc}
        print('done', os.path.basename(f), M.shape, flush=True)
    R = rows.reset_index(drop=True).copy()
    for k, v in acc.items(): R[k] = v
    bars = E.load_bars(a.tickers.split(',') if a.tickers else None)
    for k, v in yesterday_moves(bars, R[['ticker', 'date']]).items(): R[k] = v
    R.to_parquet(a.out, index=False)
    print('wrote', a.out, len(R), 'rows', R.shape[1], 'cols')

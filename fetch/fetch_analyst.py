"""Fetch analyst actions (Yahoo yfinance upgrades_downgrades) -> data-ext/analyst_actions_2020_26.parquet.

Block L / I197 (0b FULL-DATA FIRST). Actions are public on their timestamp date;
the snapshot uses them strict < D (same convention as every other block).

Per (ticker, date) the file stores COUNTS BY DIRECTION:
  n_up    actions whose Action contains 'upgrad'
  n_down  actions whose Action contains 'downgrad'
  n_init  initiations / coverage starts ('initiat' or 'coverag')
  n_all   everything else counted too (total actions that day)

yfinance on a runner: one HTTP round trip per ticker; Yahoo rate limits apply,
so we pace + retry + resume. A 429 storm is treated as fatal for that ticker
(logged, counted as miss) and the run keeps going; re-dispatch with --resume.

Runner:  python3 fetch/fetch_analyst.py --universe universe_2020_survivors_le2024.parquet \
             --out analyst_actions_2020_26.parquet [--limit N] [--resume]
"""
import argparse, os, sys, time
import pandas as pd


def dir_of(action):
    a = str(action).lower()
    if 'upgrad' in a: return 'n_up'
    if 'downgrad' in a: return 'n_down'
    if 'initiat' in a or 'coverag' in a: return 'n_init'
    return None


def fetch_one(yf, tk):
    import yfinance as yf_mod  # noqa: F401 (ensures module present)
    t = yf.Ticker(tk)
    df = t.upgrades_downgrades
    if df is None or not len(df):
        return []
    df = df.reset_index()
    dcol = 'Date' if 'Date' in df.columns else df.columns[0]
    acol = 'Action' if 'Action' in df.columns else None
    if acol is None:
        return []
    out = []
    for _, r in df.iterrows():
        d = pd.to_datetime(r[dcol])
        if d.tzinfo is not None:
            d = d.tz_localize(None)
        cat = dir_of(r[acol])
        out.append((d.strftime('%Y-%m-%d'), cat or 'n_oth'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--universe', required=True)
    ap.add_argument('--out', default='analyst_actions_2020_26.parquet')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--sleep', type=float, default=0.35)
    ap.add_argument('--start', default='2019-06-01')   # padding: 20d window at 2020-01
    ap.add_argument('--end', default='2026-12-31')
    a = ap.parse_args()

    uni = pd.read_parquet(a.universe, columns=['ticker'])
    tickers = sorted(set(t.upper().strip() for t in uni.ticker.unique()))
    if a.limit:
        tickers = tickers[:a.limit]
    print('universe tickers:', len(tickers), flush=True)

    done = set(); rows = []
    if a.resume and os.path.exists(a.out):
        prev = pd.read_parquet(a.out)
        done = set(prev.ticker)
        rows = prev.to_dict('records')
        print('resume: keeping', len(done), 'tickers,', len(rows), 'rows', flush=True)

    import yfinance as yf
    todo = [t for t in tickers if t not in done]
    print('to fetch:', len(todo), flush=True)
    t0 = time.time(); n_ok = n_miss = n_err = 0
    for i, tk in enumerate(todo):
        try:
            evs = fetch_one(yf, tk)
            day = {}
            for dt, cat in evs:
                if a.start <= dt <= a.end:
                    d0 = day.setdefault(dt, dict(n_up=0, n_down=0, n_init=0, n_oth=0))
                    d0[cat] += 1
            for dt, c in day.items():
                rows.append(dict(ticker=tk, date=dt, n_up=c['n_up'], n_down=c['n_down'],
                                 n_init=c['n_init'], n_oth=c['n_oth']))
            n_ok += 1
        except Exception as e:
            msg = str(e)[:60]
            if '429' in msg or 'Too Many' in msg:
                n_err += 1
                time.sleep(20)          # back off hard on rate limit
            else:
                print('WARN', tk, type(e).__name__, msg, flush=True)
                n_miss += 1
        if (i + 1) % 250 == 0:
            pd.DataFrame(rows).to_parquet(a.out, index=False)
            el = time.time() - t0
            print(f'{i+1}/{len(todo)} ok={n_ok} miss={n_miss} err429={n_err}, {el:.0f}s, '
                  f'eta {el/(i+1)*(len(todo)-i-1):.0f}s', flush=True)
        time.sleep(a.sleep)

    df = pd.DataFrame(rows)
    if len(df):
        df = df.groupby(['ticker', 'date'], as_index=False)[['n_up', 'n_down', 'n_init', 'n_oth']].sum()
    else:
        df = pd.DataFrame(columns=['ticker', 'date', 'n_up', 'n_down', 'n_init', 'n_oth'])
    df.to_parquet(a.out, index=False)
    print(f'wrote {a.out}: {len(df)} ticker-days, {df.ticker.nunique() if len(df) else 0} tickers; '
          f'ok={n_ok} miss={n_miss} err429={n_err}')


if __name__ == '__main__':
    main()

"""Extra Step A questions: New Bot's chart-picture v2 tags (sha 24f97085...), discover 2020-22 only, same scoring as Step A.
8 questions: 7 tag checks (cp_*) + cp_hard_all (all 6 hard checks pass). Blank = fail (0).
The tags use day t's close (windows end at t inclusive), so the tag dated t is used as the answer for the NEXT session
of that stock (trade buys at that day's open) - no peeking. Rows dated after 2022-12-31 are dropped while reading."""
import os, sys, hashlib, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoring import trades as TR
import os
SRC = os.path.join(os.environ.get('CHECKLIST_DATA_DIR', '/workspace/checklist_brainstorm/engine/cp_v2'),
                   'cp_v2_tags_2020_24.csv')
if SRC.endswith('.csv') and not os.path.exists(SRC) and os.path.exists(SRC + '.xz'):
    import lzma, shutil
    with lzma.open(SRC + '.xz', 'rb') as f_in, open(SRC, 'wb') as f_out: shutil.copyfileobj(f_in, f_out)
SHA = '24f970859b4a5d9d69b04bf3bbf9bc81fb1d6ffe885a9b0787a7f6ef0cc30b8e'
Q = ['cp_mid_slope_up', 'cp_gr_body20', 'cp_pctB', 'cp_dip_atr', 'cp_days_since_h20', 'cp_dd_vs_run', 'cp_redgreen_vol10', 'cp_hard_all']
if __name__ == '__main__':
    OUT = os.environ.get('OUT_DIR', '/workspace/step_a_out')
    h = hashlib.sha256(open(SRC, 'rb').read()).hexdigest(); assert h == SHA, f'checksum mismatch {h}'
    parts = []
    for c in pd.read_csv(SRC, usecols=['ticker', 'date'] + Q, chunksize=1_000_000):
        c['date'] = pd.to_datetime(c.date); parts.append(c[c.date <= '2022-12-31'])
    T = pd.concat(parts).sort_values(['ticker', 'date']); T[Q] = (T[Q].fillna(0) == 1).astype(np.int8)
    T[Q] = T.groupby('ticker')[Q].shift(1)            # tag known at close of t -> answer for next session
    base = pd.read_parquet(f'{OUT}/trade_base_discover.parquet')
    k = base[base.ready & base.passes_filter & base.bench.notna()].sort_values(['ticker', 'date']).reset_index(drop=True)
    J = k[['ticker', 'date']].merge(T, on=['ticker', 'date'], how='left'); L = TR.luck_check(); S = []
    for q in Q:
        a = J[q].fillna(-1).to_numpy(np.int8)          # no tag row at all (first day / missing) = can't answer
        S += TR.score_question(TR.trade_rows(k, a, f'cp_v2|{q}'), L)
    R = pd.DataFrame(S); R.to_parquet(f'{OUT}/chunks/scores_cp_v2.parquet', index=False)
    print(R[['question_id', 'answer', 'n', 'win', 'mean_ret', 'mean_bench', 'z', 'full', 'passes_40']].to_string())

"""Unit tests for scoring/state_questions.py on synthetic data (no engine, no release)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, pandas as pd
from scoring.state_questions import day_flip_stats, yesterday_moves, col_key

def test_col_key():
    assert col_key("RSI14|cross|1d|14") == "RSI14|cross"
    assert col_key("H|EMA21|vs_own_past|1d|120") == "EMA21|vs_own_past"

def test_day_flip_stats():
    # 2 tickers x 4 days; 3 questions: q0/q1 binary yes/no, q2 3-label
    # rows sorted by (ticker, date)
    M = np.array([
        [ 1, 0, 2], [ 1, 0, 2], [ 0, 1, 2], [-1, 1, 0],   # AAA: day2 q0 1->0 (bear), q1 0->1 (bull); day3 q0 blank
        [ 0, 0,-1], [ 1, 0,-1], [ 1, 1,-1], [ 1, 1, 0],   # BBB: q2 -1->0 at day3 = 'any' only
    ], np.int8)
    cols = ["Q0|yesno|1d|1", "Q1|yesno|1d|1", "Q2|tri|1d|1"]
    yesno = {"Q0|yesno", "Q1|yesno"}
    st = day_flip_stats(M, cols, yesno, [4, 4])
    # AAA day1 (idx1): no change; day2 (idx2): any=2, bull=1 (q1), bear=1 (q0); day3 (idx3): q2 2->0 any, q0 blank
    assert st['q_flips_any'][1] == 0
    assert st['q_flips_any'][2] == 2 and st['q_flips_bull'][2] == 1 and st['q_flips_bear'][2] == 1
    assert st['q_flips_any'][3] == 1 and st['q_flips_bull'][3] == 0 and st['q_flips_bear'][3] == 0
    # BBB: changes at idx5 (q0 0->1 bull), idx6 (q0 same, q1 0->1 bull); idx7 q2 is blank->0, NOT a flip
    assert st['q_flips_any'][5] == 1 and st['q_flips_bull'][5] == 1
    assert st['q_flips_any'][6] == 1 and st['q_flips_bull'][6] == 1
    assert st['q_flips_any'][7] == 0 and st['q_flips_bull'][7] == 0 and st['q_flips_bear'][7] == 0
    # first day of each ticker: zeros (no within-ticker yesterday)
    assert st['q_flips_any'][0] == 0 and st['q_flips_any'][4] == 0
    # answered count
    assert list(st['q_answered']) == [3, 3, 3, 2, 2, 2, 2, 3]

def test_yesterday_moves():
    bars = pd.DataFrame({
        'ticker': ['A'] * 5 + ['B'] * 3,
        'date': pd.to_datetime(['2020-01-02', '2020-01-03', '2020-01-06', '2020-01-07', '2020-01-08',
                                '2020-01-03', '2020-01-06', '2020-01-07']),
        'close':  [10., 11., 11., 10., 12.,  5., 5., 6.]})
    rows = pd.DataFrame({'ticker': ['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B'],
                         'date': pd.to_datetime(['2020-01-02', '2020-01-03', '2020-01-06', '2020-01-07', '2020-01-08',
                                                 '2020-01-03', '2020-01-06', '2020-01-07'])})
    mv = yesterday_moves(bars, rows)
    # A: D=01-02, 01-03 blank (need 2 closes before D); 01-06 up; 01-07 flat; 01-08 down
    assert list(mv['yesterday_up'][:5]) == [-1, -1, 1, 0, 0]
    assert list(mv['yesterday_down'][:5]) == [-1, -1, 0, 0, 1]
    assert list(mv['yesterday_flat'][:5]) == [-1, -1, 0, 1, 0]
    # B: 01-03, 01-06 blank; 01-07 flat (5==5)
    assert list(mv['yesterday_up'][5:]) == [-1, -1, 0]
    assert list(mv['yesterday_flat'][5:]) == [-1, -1, 1]

if __name__ == '__main__':
    test_col_key(); test_day_flip_stats(); test_yesterday_moves()
    print('ALL STATE-QUESTION TESTS PASS')

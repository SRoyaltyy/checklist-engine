"""Structural ticker-dependence: a row is DEP if, while the reader evaluates it, any data loader is
called with the ticker (or anything ticker-derived: SPDR via universe, analyst ratings)."""
import sys, json, pandas as pd, build_preburn_matrix as B
from build_preburn_fast import memo, CELL_MEMO
R = dict(B.load_readers()); J, G = R['james'], R['grok']
T = None; hit = [False]
def spy(fn, test):
    def w(*a):
        if test(a): hit[0] = True
        return fn(*a)
    return w
J.series = spy(J.series, lambda a: a[0] == T or (isinstance(a[0], str) and a[0] in J.SECTOR_TO_SPDR.values()))
J.spdr_for = spy(J.spdr_for, lambda a: True); J._tr_universe = spy(J._tr_universe, lambda a: True)
for f in ('stock_but','sector_eval','sector_row_measure'): setattr(J, f, spy(getattr(J, f), lambda a: True))
G.yahoo = spy(G.yahoo, lambda a: a[0] == T); G.ratings = spy(G.ratings, lambda a: True); G.stock_but = spy(G.stock_but, lambda a: True)
jr = J._rows(); gr = G.grok_rows(); dep = set()
for T, D in [('AAPL','2024-03-04'), ('NVDA','2024-08-02'), ('MSFT','2024-11-12')]:
    for _, r in jr.iterrows():
        hit[0] = False; J._rows = lambda r=r: r.to_frame().T; J.answer(T, D)
        if hit[0]: dep.add(r.id)
    for r in gr:
        hit[0] = False; G.grok_rows = lambda r=r: [r]; G.answer(T, D)
        if hit[0]: dep.add(r['id'])
    print(T, D, len(dep), flush=True)
allids = list(jr.id) + [r['id'] for r in gr]
json.dump({'ticker_dependent': sorted(dep), 'ticker_independent': sorted(set(allids) - dep)},
          open('out/pilot_matrix/preburn/ticker_dependence.json', 'w'))
print('dep', len(dep), 'indep', len(set(allids) - dep))

"""Classify James's 489 sector rows: SECTOR_ONLY (reader never loads the stock's own series once sector is known) vs STOCK_SECTOR.
_tr_universe is patched to the CURRENT Theme Radar snapshot for every date (sector_map=current_backfilled)."""
import sys, json, importlib.util, pandas as pd
sys.path.insert(0, 'universe'); import engine_year as E
sp = importlib.util.spec_from_file_location("jr", "readers/james.py"); J = importlib.util.module_from_spec(sp); sp.loader.exec_module(J)
U = pd.read_csv(E.SECT, dtype=str).set_index("Ticker")
J._tr_universe = lambda d: U
ids = [r[0] for r in E.dep_rules() if r[1] == "j_base"]; rows = J._rows(); rows = rows[rows.id.isin(ids)]
T = None; hit = [False]; s0 = J.series
def spy(sym):
    if sym == T: hit[0] = True
    return s0(sym)
J.series = spy; out = {}
for T, D in [("AAPL", "2024-03-04"), ("JPM", "2023-06-01"), ("XOM", "2021-09-15")]:
    for _, r in rows.iterrows():
        hit[0] = False; J._rows = lambda r=r: r.to_frame().T; res = J.answer(T, D)
        if hit[0]: out[r.id] = "STOCK_SECTOR"
        else: out.setdefault(r.id, "SECTOR_ONLY")
    print(T, D, pd.Series(out).value_counts().to_dict(), flush=True)
json.dump(out, open("universe/sector_row_class.json", "w"), indent=0)

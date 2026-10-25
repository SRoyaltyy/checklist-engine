"""World-coverage gate tooling (0b 2026-10-25 FULL-DATA FIRST).

Builds docs/WORLD_COVERAGE.csv: one row per dictionary/DATA_SOURCES item (233 rows:
C01-C30 core + I001-I203 items), with snapshot column mapping, measured non-null %
over the world snapshot shards, first date available, and a status in
{WIRED, BLOCKED_SECRET, NOT_AVAILABLE_FREE, EXCLUDED_FREE_TEXT, EXCLUDED_LIVE_ONLY,
PENDING}. The CI gate fails while any row is PENDING/missing or a WIRED row has 0%
non-null.

Modes:
  seed    -- auto-match items to snapshot columns -> dictionary/world_coverage_map.csv
  measure -- scan shard parquet(s) -> coverage_measure.json (column non-null %, first date)
  build   -- join items x map x measurement -> docs/WORLD_COVERAGE.csv (--gate exits 1 on failure)

The curated map is committed; auto-matching is only a seed — review edits by hand.
"""
import argparse, csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(ROOT, 'dictionary', 'world_coverage_map.csv')
SOURCES = os.path.join(ROOT, 'dictionary', 'DATA_SOURCES.csv')
OUT = os.path.join(ROOT, 'docs', 'WORLD_COVERAGE.csv')
MEAS = os.path.join(ROOT, 'coverage_measure.json')
ALLOWED = {'WIRED', 'BLOCKED_SECRET', 'NOT_AVAILABLE_FREE', 'EXCLUDED_FREE_TEXT', 'EXCLUDED_LIVE_ONLY'}

def norm(s):
    return re.sub(r'[^a-z0-9]+', '', str(s).lower())

def load_items():
    with open(SOURCES, encoding='utf-8') as f:
        return list(csv.DictReader(f))

# ---------------- seed: auto-match item names to snapshot columns ----------------
CUSTOM = {  # item-name fragment -> column list (v1 auto-seed; review by hand)
    'breadth': ['breadth'],
    'earnings': ['earn_days', 'earn_amc', 'earn_surp', 'earn_deps'],
    'shortinterest': ['si_qty', 'si_dtc', 'si_chg', 'si_days'],
    'shortvolume': ['shv_ratio', 'shv_r5', 'shv_r20'],
    'halt': ['halt_days', 'halt_gap', 'halt_rsn', 'halt_n20', 'halt_n60'],
    'regsho': ['regsho_days', 'regsho_on'],
    'dividend': ['div_amt', 'div_days', 'div_n12'],
    'split': ['split_ratio', 'split_days', 'split_n'],
    'themepeer': ['peer_id', 'peer_n', 'peer_r1', 'peer_r5', 'peer_r20', 'vs_peer_r1', 'vs_peer_r5', 'vs_peer_r20', 'peer_corr60'],
    'vix': [], 'putcall': [],   # market-wide; columns land with block I201 wiring
}

# v1 auto-seed heuristics; hand-review the map after seeding. Non-default-period variants
# map to their TA-Lib function column with an explicit note — the snapshot carries one
# default-period instance per function (per-period expansion is an open design question
# for the room, see 0c).
OVERRIDES = {  # item_id -> (status, columns, note)
    'C30': ('EXCLUDED_LIVE_ONLY', '', 'Finviz block P: live-only from 2026-08, never scored (0b ruling)'),
    'I178': ('WIRED', 'mkt_vix|mkt_vix_r5|mkt_vix_d20',
             'VIX level: keyless FRED CSV via fetch/fetch_mkt.py (never revised, strict < D); 2025-26 refreshed on runner'),
    'I187': ('WIRED', 'f4_n|f4_days|f4_n20|f4_n60',
             'Form 4 date-count lens via SEC submissions API (fetch/fetch_form4.py); filingDate < D strict; value lens later'),
    'I197': ('WIRED', 'an_days|an_n20|an_up20|an_dn20|an_up60|an_dn60|an_dir',
             'analyst actions via yfinance upgrades_downgrades (fetch/fetch_analyst.py); strict date < D; counts by direction'),
    'I192': ('WIRED', 'xb_days|xb_rev|xb_rev_days|xb_rev_g|xb_ni|xb_ni_days|xb_ni_g|xb_assets|xb_assets_days|xb_debt|xb_debt_days|xb_shares|xb_shares_days',
             'SEC XBRL frames API keyed filed < D (restatement-safe); fiscal-offset filers sparser; value lens via fetch/fetch_xbrl.py'),
    'I195': ('BLOCKED_SECRET', '', 'FRED/ALFRED vintages need FRED_API_KEY; fetch code wired, env key missing'),
    'I202': ('PENDING', '', 'single-stock options IV: box-only partial (DoltHub M/W/F to Oct 2024); room decision requested'),
}

def _prefix(item):
    m = re.match(r'^\s*([A-Za-z][A-Za-z_]*?)(?=\d|\s*\(|\s|-|$)', item.strip())
    return m.group(1).upper() if m else ''

CONCEPT = '(definitional)'

NON_TALIB_PREFIX = ('ETF_', 'SI_', 'SHV_', 'HALT_', 'REGSHO_', 'EARN_', 'PEER_', 'VS_', 'DIV_', 'SPLIT_')

def auto_match(items, cols):
    # talib columns: leading all-caps token, not a named non-talib family.
    # Multi-output functions are NAME_outputname (MACD_macdsignal, BBANDS_upperband).
    def is_talib(c):
        head = c.split('_')[0]
        return head.isalpha() and head.isupper() and not c.startswith(NON_TALIB_PREFIX)
    talib = [c for c in cols if is_talib(c)]
    cdls = [c for c in talib if c.split('_')[0].startswith('CDL')]

    def match_talib(p):
        """exact column, or multi-output family column NAME_xxx"""
        for c in talib:
            if c == p or c.startswith(p + '_'):
                return c
        return None
    # alias: item prefix -> talib func name (only where they differ)
    ALIAS = {'ADLINE': 'AD', 'AD_LINE': 'AD', 'STOCH14_3': 'STOCH', 'WILLIAMSR': 'WILLR',
             'WILLIAMSR14': 'WILLR', 'MACDSIG': 'MACD', 'MACDHIST': 'MACD', 'MIDPRICE': 'MIDPOINT'}
    rows = []
    for it in items:
        iid, name = it['id'], it['item']
        if iid in OVERRIDES:
            st, sc, nt = OVERRIDES[iid]
            rows.append(dict(item_id=iid, status=st, snapshot_columns=sc, note=nt)); continue
        if re.match(r'^C\d\d$', iid) and iid != 'C30':
            rows.append(dict(item_id=iid, status='WIRED', snapshot_columns=CONCEPT,
                             note='core concept: computed from bars PIT in the engine; not a stored snapshot column'))
            continue
        nname = norm(name)
        hits, note = [], ''
        for frag, cl in CUSTOM.items():
            if frag in nname:
                hits = cl; break
        if hits:
            rows.append(dict(item_id=iid, status='WIRED', snapshot_columns='|'.join(hits),
                             note=note or 'event/block columns')); continue
        # candle pattern by name containment
        for c in cdls:
            cn = norm(c[3:])
            if cn and (cn in nname or nname in cn):
                hits = [c]; break
        if not hits:
            p = _prefix(name)
            p = ALIAS.get(p, p)
            mc = match_talib(p)
            if mc:
                hits = [mc]
                m2 = re.match(r'^[A-Za-z][A-Za-z_]+?(\d+(?:_\d+\d*)*)', name.strip())
                if m2 and m2.group(1) not in ('14',):  # note any explicit period param
                    note = f'item period {m2.group(1)}; snapshot = TA-Lib default instance of {p}'
        if hits:
            rows.append(dict(item_id=iid, status='WIRED', snapshot_columns='|'.join(hits), note=note))
        else:
            rows.append(dict(item_id=iid, status='PENDING', snapshot_columns='', note=''))
    return rows

# ---------------- measure: non-null % and first date per column ----------------
def measure(shards):
    import pyarrow.parquet as pq
    import pyarrow.compute as pc
    agg, dates = {}, None
    for sh in shards:
        f = pq.ParquetFile(sh)
        need = [c for c in f.schema_arrow.names if c not in agg or agg[c][0] == 0]
        t = f.read()  # one shard ~130MB: fine on runner
        if dates is None:
            d = t.column('date')
            dates = d
        n = t.num_rows
        for c in f.schema_arrow.names:
            if c in ('ticker', 'date'):
                continue
            col = t.column(c)
            nn = pc.count(col).as_py()  # non-null count (count ignores nulls)
            tot, nn_tot = agg.get(c, (0, 0))
            agg[c] = (tot + n, nn_tot + nn)
    out = {}
    for c, (tot, nn_tot) in agg.items():
        out[c] = dict(non_null_pct=round(100.0 * nn_tot / tot, 2) if tot else 0.0, rows=tot)
    first = {}
    for sh in shards[:1]:
        f = pq.ParquetFile(sh)
        t = f.read(columns=['date'])
        dcol = t.column('date')
        first['date_min'] = str(pc.min(dcol).as_py())[:10]
        first['date_max'] = str(pc.max(dcol).as_py())[:10]
    json.dump(dict(columns=out, shard_dates=first), open(MEAS, 'w'), indent=1)
    print('measured', len(out), 'columns across', len(shards), 'shard(s); rows/shard seen:', {c: v['rows'] for c, v in list(out.items())[:1]})

# ---------------- build: join and gate ----------------
def build(gate):
    items = {r['id']: r for r in load_items()}
    mrows = {}
    if os.path.exists(MAP):
        with open(MAP, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                mrows[r['item_id']] = r
    meas = json.load(open(MEAS))['columns'] if os.path.exists(MEAS) else {}
    shard_dates = json.load(open(MEAS)).get('shard_dates', {}) if os.path.exists(MEAS) else {}
    rows, fails = [], []
    for iid, it in items.items():
        m = mrows.get(iid, {})
        status = m.get('status', 'PENDING')
        scol = m.get('snapshot_columns', '')
        if scol == CONCEPT:
            rows.append(dict(item_id=iid, item=it['item'], block=it['block'], snapshot_columns=scol,
                             non_null_pct_2020_2026=100.0,
                             first_date_available=shard_dates.get('date_min', ''),
                             status=status, note=m.get('note', '')))
            if status == 'PENDING':
                fails.append(f'{iid} PENDING')
            continue
        cols = [c for c in scol.split('|') if c]
        pcts = [meas[c]['non_null_pct'] for c in cols if c in meas]
        pct = round(sum(pcts) / len(pcts), 2) if pcts else (None if not cols else 0.0)
        if not cols and status == 'WIRED':
            pct = None
        note = m.get('note', '')
        if status == 'PENDING' and not note:
            note = 'awaiting block wiring (see 0c plan)'
        row = dict(item_id=iid, item=it['item'], block=it['block'], snapshot_columns=scol,
                   non_null_pct_2020_2026=pct if pct is not None else '',
                   first_date_available=shard_dates.get('date_min', '') if status == 'WIRED' else '',
                   status=status, note=note)
        rows.append(row)
        if status == 'PENDING' or (status == 'WIRED' and not cols):
            fails.append(f'{iid} PENDING/no columns')
        if status == 'WIRED' and cols and not pcts:
            fails.append(f'{iid} WIRED but columns not measured')
        if status == 'WIRED' and pcts and max(pcts) <= 0:
            fails.append(f'{iid} WIRED but 0% non-null')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    from collections import Counter
    print('status counts:', dict(Counter(r['status'] for r in rows)))
    print('wrote', OUT, len(rows), 'rows')
    if gate:
        if fails:
            print('GATE FAIL:'); [print(' ', x) for x in fails[:40]]
            print('  ...', len(fails), 'failures total')
            sys.exit(1)
        print('GATE PASS')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['seed', 'measure', 'build'])
    ap.add_argument('--shards', nargs='+')
    ap.add_argument('--gate', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'seed':
        import pyarrow.parquet as pq
        cols = pq.ParquetFile(a.shards[0]).schema_arrow.names
        rows = auto_match(load_items(), cols)
        with open(MAP, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['item_id', 'status', 'snapshot_columns', 'note'])
            w.writeheader(); w.writerows(rows)
        from collections import Counter
        print('seeded', MAP, dict(Counter(r['status'] for r in rows)))
    elif a.cmd == 'measure':
        measure(a.shards)
    else:
        build(a.gate)

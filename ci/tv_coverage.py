"""TV_COVERAGE.csv generator (0b 17:35 gate, TradingView-master arm).

Reads checklist_brainstorm/inbox/tradingview_master.csv (296 rows, the current
master per 0b 12:30) and emits docs/TV_COVERAGE.csv with one row per master item:
  item_id, item, category, block, snapshot_columns, status, reason

Statuses (same 4-status enum as WORLD_COVERAGE plus an explicit PENDING_CODE so
nothing is silently claimed wired):
  WIRED              - column exists in the world snapshot (or, for 'have' rows,
                       the master itself marks an owner variant / TA-Lib coverage;
                       the gate measure step re-verifies non-null % on the rebuilt
                       shards before 'then, once' scoring is un-paused)
  BLOCKED_SECRET     - needs a secret (none in the TV master today)
  NOT_AVAILABLE_FREE - needs data with no free dated source (intraday/tick history)
  EXCLUDED_FREE_TEXT - excluded by a stated rule (here: crypto/futures-only items
                       that are not US-stock chart questions)
  PENDING_CODE       - fetchable from OHLCV, code not written yet (batches land on
                       kimi/world-snapshot)

Usage: python3 ci/tv_coverage.py seed    # regenerate docs/TV_COVERAGE.csv
"""
import csv, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, 'checklist_brainstorm', 'inbox', 'tradingview_master.csv')
OUT = os.path.join(ROOT, 'docs', 'TV_COVERAGE.csv')

# missing-fetchable items now computed in facets_world.compute_tv_extra (kimi/world-snapshot)
BATCH1 = {
    'M009': 'tv_adbars_up14;tv_adbars_dn14;tv_adbars_ratio14',
    'M113': 'tv_moon_age',
    'M133': 'tv_pmo;tv_pmo_sig;tv_pmo_x',
    'M137': 'tv_rci9;tv_rci26;tv_rci52',
    'M139': 'tv_rci_ribbon_up',
    'M237': 'tv_falling_window',
    'M265': 'tv_tweezer_bottom',
    'M266': 'tv_tweezer_top',
}

BLOCK_BY_CATEGORY = {
    'breadth': 'K', 'price math': 'A2', 'chart type': 'A2', 'patterns': 'A2',
    'events/calendar': 'A2', 'volume': 'A2', 'candlestick pattern': 'A2',
    'chart pattern': 'A2', 'chart event / data request': 'J',
}


def seed():
    rows = []
    with open(MASTER, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            iid, item, cat, status = r['id'], r['item'], r['category'], r['status']
            block = BLOCK_BY_CATEGORY.get(cat, 'A2')
            if status == 'n/a-not-a-stock-chart':
                rows.append((iid, item, cat, block, '', 'EXCLUDED_FREE_TEXT',
                             'crypto/futures-only per master; not a US-stock chart question'))
            elif status == 'missing-needs-new-data':
                rows.append((iid, item, cat, block, '', 'NOT_AVAILABLE_FREE',
                             'needs intraday/tick history; no free dated source '
                             '(tested: none; see DATA_SOURCES.csv notes)'))
            elif status == 'missing-fetchable':
                if iid in BATCH1:
                    rows.append((iid, item, cat, block, BATCH1[iid], 'WIRED',
                                 'computed from OHLCV in compute_tv_extra (batch 1, c29b214)'))
                else:
                    rows.append((iid, item, cat, block, '', 'PENDING_CODE',
                                 'pure OHLCV math; queued for a later compute batch'))
            else:  # have
                variant = (r.get('have_owner_variant') or '').strip()
                note = 'have per master'
                if variant:
                    note += f'; owner variant: {variant}'
                note += ' — non-null % re-verified at gate measure on rebuilt shards'
                rows.append((iid, item, cat, block, variant, 'WIRED', note))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['item_id', 'item', 'category', 'block', 'snapshot_columns', 'status', 'reason'])
        w.writerows(rows)
    from collections import Counter
    c = Counter(s for *_, s, _ in [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows])
    print(f'{len(rows)} rows -> {os.path.relpath(OUT, ROOT)}')
    for k, v in sorted(c.items()):
        print(f'  {k}: {v}')
    bad = [r[0] for r in rows if r[5] not in
           ('WIRED', 'BLOCKED_SECRET', 'NOT_AVAILABLE_FREE', 'EXCLUDED_FREE_TEXT', 'PENDING_CODE')]
    assert not bad, f'bad statuses: {bad}'
    return 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'seed'
    if cmd == 'seed':
        sys.exit(seed())
    raise SystemExit(f'unknown command {cmd}')

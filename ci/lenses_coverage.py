"""Generate per-item lens coverage for the 258 inventory items (I001-I228 + C01-C30).

Reads dictionary/DATA_SOURCES.csv, classifies each item into a declared
measurement class, applies the class applicability rule table from
docs/LENSES_V1.md (14 lenses), and writes docs/LENSES_COVERAGE_V1.csv plus the
inventory-coverage section of docs/LENSES_V1.md (between fixed markers, so
reruns are idempotent). Every inapplicable lens carries a reason code; the
absolute/threshold alias is counted once; conditional lenses name their missing
prerequisite. Deterministic: no floats, fixed ordering.
"""
import csv
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / 'dictionary' / 'DATA_SOURCES.csv'
LENSES_MD = ROOT / 'docs' / 'LENSES_V1.md'
COVERAGE_CSV = ROOT / 'docs' / 'LENSES_COVERAGE_V1.csv'

LENSES = ('absolute', 'relative', 'position', 'threshold', 'divergence', 'outlier',
          'path', 'streak', 'cross', 'change_since_last', 'rank',
          'percentile', 'extreme_vs_own_history', 'timeframe')

# Reason codes for inapplicable lenses (kept short for the table).
REASONS = {
    'RANK_GLOBAL': 'market-global series: identical across stocks, no cross-stock rank',
    'POS_CAT': 'categorical/boolean has no ordered magnitude; use the declared share reading',
    'ABS_CAT': 'raw state code has no units; use a named-state indicator or declared share',
    'REL_NAMED': 'needs a named PIT benchmark/peer set before it certifies',
    'DIV_PAIR': 'needs a declared numeric pairing (e.g. vs price) before it certifies',
    'ONTOLOGY': 'ontology/rule control, not a measurement: no lens readings',
    'DROPPED': 'item dropped (GDELT news stays dropped, 2026-10-28): no lens readings',
}

# Measurement classes. Each rule: applicable lenses, inapplicable {lens: reason},
# flags (named missing prerequisites / conditions). absolute==threshold is one
# predicate (alias counted once); cross/streak/path/change stay separate lenses.
CLASS_RULES = {
    'STOCK_SCALAR': dict(
        applicable=set(LENSES), inapplicable={}, alias=('absolute', 'threshold'),
        flags=('rank: named PIT peer set required (default = filtered universe)',)),
    'SPARSE_NUMERIC': dict(
        applicable=set(LENSES), inapplicable={}, alias=('absolute', 'threshold'),
        flags=('timeframe: registered native resolutions only (q vs y), never daily-relabel',
               'streak/cross: consecutive native observations (quarterly), not sessions')),
    'EVENT_COUNT': dict(
        applicable=set(LENSES), inapplicable={}, alias=('absolute', 'threshold'),
        flags=('rank: named PIT peer set required',)),
    'EVENT_FACT': dict(
        applicable=set(LENSES) - {'divergence', 'relative'},
        inapplicable={'divergence': 'DIV_PAIR', 'relative': 'REL_NAMED'},
        alias=('absolute', 'threshold'),
        flags=('CONCRETE fields per 0b 00:40: event_date + days_since + direction + change',)),
    'BOOLEAN_STATE': dict(
        applicable=set(LENSES) - {'position', 'relative', 'divergence'},
        inapplicable={'position': 'POS_CAT', 'relative': 'REL_NAMED',
                      'divergence': 'DIV_PAIR'},
        alias=('absolute', 'threshold'),
        flags=('readings use the declared share/count of TRUE, never the raw code',
               'rank: CONDITIONAL - cross-stock on the declared share')),
    'CATEGORICAL_STATE': dict(
        applicable=set(LENSES) - {'absolute', 'position', 'relative'},
        inapplicable={'absolute': 'ABS_CAT', 'position': 'POS_CAT', 'relative': 'REL_NAMED'},
        alias=None,
        flags=('readings use named-state indicators or declared shares, never mean/rank of codes',
               'divergence: CONDITIONAL - native declared pairings only (e.g. stage vs price)',
               'rank: CONDITIONAL - cross-stock on the declared share')),
    'MARKET_GLOBAL': dict(
        applicable=set(LENSES) - {'rank'}, inapplicable={'rank': 'RANK_GLOBAL'},
        alias=('absolute', 'threshold'),
        flags=('own-history readings use vintage-corrected history (ALFRED for FRED)',)),
    'MIXED_SNAPSHOT': dict(
        applicable=set(LENSES), inapplicable={}, alias=('absolute', 'threshold'),
        flags=('per-field split: numeric fields -> STOCK_SCALAR set, categorical -> CATEGORICAL_STATE set',
               'PIT_MISSING: snapshot publication-time proof required before any reading certifies')),
    'NO_QUESTIONS': dict(applicable=set(), inapplicable={l: 'ONTOLOGY' for l in LENSES},
                         alias=None, flags=()),
    'NO_QUESTIONS_DROPPED': dict(applicable=set(),
                                 inapplicable={l: 'DROPPED' for l in LENSES},
                                 alias=None, flags=()),
}

# Explicit per-item classification. Items not listed here take their block default.
BLOCK_DEFAULT = {'A': 'STOCK_SCALAR', 'B': 'STOCK_SCALAR', 'C': 'STOCK_SCALAR',
                 'D': 'EVENT_FACT', 'E': 'EVENT_COUNT', 'F': 'SPARSE_NUMERIC',
                 'G': 'BOOLEAN_STATE', 'H': 'SPARSE_NUMERIC', 'I': 'MARKET_GLOBAL',
                 'J': 'EVENT_FACT', 'K': 'MARKET_GLOBAL', 'L': 'EVENT_FACT',
                 'M': 'SPARSE_NUMERIC', 'N': 'STOCK_SCALAR', 'O': 'NO_QUESTIONS_DROPPED',
                 'P': 'MIXED_SNAPSHOT'}

OVERRIDE = {
    # block A: bar statistics and structural items
    'C16': 'EVENT_COUNT', 'C17': 'EVENT_COUNT', 'C18': 'EVENT_COUNT', 'C19': 'EVENT_COUNT',
    'C20': 'EVENT_COUNT', 'C21': 'EVENT_COUNT', 'C22': 'EVENT_COUNT',
    'C26': 'CATEGORICAL_STATE', 'C27': 'BOOLEAN_STATE',
    'C28': 'NO_QUESTIONS', 'C29': 'NO_QUESTIONS', 'C30': 'MIXED_SNAPSHOT',
    # pivot/zigzag event items, bar-sequence booleans
    'I066': 'EVENT_COUNT', 'I067': 'EVENT_COUNT', 'I107': 'EVENT_COUNT',
    'I108': 'EVENT_COUNT', 'I109': 'EVENT_COUNT', 'I110': 'EVENT_COUNT',
    'I111': 'CATEGORICAL_STATE', 'I112': 'CATEGORICAL_STATE',
    'I114': 'EVENT_COUNT', 'I115': 'EVENT_COUNT',
    # all 44 single candle-pattern booleans (I118-I161) + doji/spinning variants
    'I121': 'EVENT_COUNT', 'I153': 'EVENT_COUNT', 'I154': 'EVENT_COUNT',
    # volume: daily short volume is a daily scalar; SI is sparse
    'I188': 'SPARSE_NUMERIC', 'I189': 'STOCK_SCALAR',
    # event facts
    'I184': 'EVENT_FACT', 'I185': 'SPARSE_NUMERIC', 'I186': 'SPARSE_NUMERIC',
    'I191': 'EVENT_FACT', 'I196': 'EVENT_FACT', 'I197': 'EVENT_FACT',
    # options: scalar readings where a source exists (hunt: no free full-universe OI yet)
    'I201': 'MARKET_GLOBAL', 'I202': 'STOCK_SCALAR',
    # misc
    'I183': 'EVENT_COUNT', 'I203': 'EVENT_COUNT', 'I208': 'EVENT_COUNT',
    'I221': 'CATEGORICAL_STATE', 'I227': 'EVENT_COUNT',
}
for _i in range(118, 162):   # I118..I161 candle pattern booleans
    OVERRIDE[f'I{_i:03d}'] = 'EVENT_COUNT'

ITEM_FLAGS = {
    'I176': ('PIT_MISSING: theme membership history (dated theme map) required for peer sets',),
    'I177': ('PIT_MISSING: PIT sector peer set required (SEC SIC as filed + dated ETF map)',),
    'I202': ('SOURCE_MISSING: no free full-universe single-stock options source confirmed (hunt V1: DoltHub IV/chain partial, no OI)',),
    'I198': ('PIT_MISSING: Finviz snapshot publication-time proof required',),
    'C30': ('PIT_MISSING: Finviz snapshot publication-time proof required',),
    'I117': ('timeframe lens = comparison across registered native bar definitions (HA/Renko/Kagi/P&F/...), never daily-relabel',),
    'I225': ('PIT_MISSING: named peer set required',),
    'I228': ('REL_NAMED: literal benchmark or PIT peer must be named per reading',),
}

BEGIN = '<!-- INVENTORY_COVERAGE:BEGIN -->'
END = '<!-- INVENTORY_COVERAGE:END -->'


def classify(row):
    iid = row['id']
    cls = OVERRIDE.get(iid, BLOCK_DEFAULT[row['block']])
    return cls, CLASS_RULES[cls]


def unique_count(rule):
    n = len(rule['applicable'])
    if rule.get('alias') and set(rule['alias']) <= rule['applicable']:
        n -= 1
    return n


def build():
    rows = list(csv.DictReader(SOURCES.open(encoding='utf-8-sig', newline='')))
    assert len(rows) == 258, 'inventory must have 258 items'
    out = []
    class_counts = {}
    for row in sorted(rows, key=lambda r: r['id']):
        iid = row['id']
        cls, rule = classify(row)
        class_counts[cls] = class_counts.get(cls, 0) + 1
        n_unique = unique_count(rule)
        flags = list(rule['flags']) + list(ITEM_FLAGS.get(iid, ()))
        out.append(dict(id=iid, item=row['item'], block=row['block'], cls=cls,
                        applicable='|'.join(l for l in LENSES if l in rule['applicable']),
                        n_unique=str(n_unique),
                        inapplicable=inapplicable_text(cls, rule),
                        flags='; '.join(flags)))
        if not cls.startswith('NO_QUESTIONS'):
            assert n_unique >= 6, f'{iid} has fewer than 6 lenses'

    with COVERAGE_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'item', 'block', 'cls', 'applicable',
                                          'n_unique', 'inapplicable', 'flags'], lineterminator='\n')
        w.writeheader()
        w.writerows(out)

    md = render_md(out, class_counts)
    text = LENSES_MD.read_text(encoding='utf-8')
    if BEGIN in text:
        text = text[:text.index(BEGIN)] + md + text[text.index(END) + len(END):]
    else:
        text = text.rstrip() + '\n\n' + md + '\n'
    LENSES_MD.write_text(text, encoding='utf-8', newline='\n')
    return out, class_counts


def inapplicable_text(cls, rule):
    if cls.startswith('NO_QUESTIONS'):
        return REASONS[rule['inapplicable']['absolute']]
    return '; '.join(f'{lens}={REASONS[why]}' for lens, why in sorted(rule['inapplicable'].items()))


def render_md(out, class_counts):
    lines = [BEGIN,
             '## Inventory coverage — 258 items (generated by ci/lenses_coverage.py)',
             '',
             'Kimi, 2026-10-30 (22:45 assignment item 3). One row per inventory item from',
             '`dictionary/DATA_SOURCES.csv`. Applicability follows the measurement-class',
             'rule table below; every inapplicable lens names its reason code, conditional',
             'readings name their prerequisite, and `absolute`/`threshold` count as one',
             'predicate (`n_unique`). Full table: `docs/LENSES_COVERAGE_V1.csv`.',
             '',
             '### Measurement-class rule table',
             '',
             '| Class | Items | Applicable lenses | Inapplicable (reason) |',
             '|---|---:|---|---|']
    for cls in sorted(CLASS_RULES, key=lambda c: -class_counts.get(c, 0)):
        rule = CLASS_RULES[cls]
        if cls == 'NO_QUESTIONS':
            inapp = 'all 14 (ONTOLOGY: rule control, not a measurement)'
        elif cls == 'NO_QUESTIONS_DROPPED':
            inapp = 'all 14 (DROPPED: GDELT news stays dropped, 2026-10-28)'
        else:
            inapp = ', '.join(f'{l} ({REASONS[w].split(";")[0]})' for l, w in
                              sorted(rule['inapplicable'].items())) or '—'
        lines.append(f'| {cls} | {class_counts.get(cls, 0)} | '
                     f'{len(rule["applicable"])} of 14 | {inapp} |')
    lines += ['', 'Reason codes: ' + '; '.join(f'{k}: {v}' for k, v in REASONS.items()),
              '',
              '### Per-item coverage (258 rows)',
              '',
              '| id | item | class | unique lenses | inapplicable | flags |',
              '|---|---|---|---:|---|---|']
    for r in out:
        inapp = r['inapplicable'] or '—'
        flags = r['flags'] or '—'
        item = r['item'].replace('|', '/')
        lines.append(f"| {r['id']} | {item} | {r['cls']} | {r['n_unique']} | {inapp} | {flags} |")
    lines.append(END)
    return '\n'.join(lines)


if __name__ == '__main__':
    out, counts = build()
    print('items:', len(out))
    print('classes:', dict(sorted(counts.items())))

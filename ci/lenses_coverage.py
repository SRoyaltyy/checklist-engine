"""Generate per-item lens coverage for the 258 inventory items (I001-I228 + C01-C30).

Reads dictionary/DATA_SOURCES.csv, classifies each item into a declared
measurement class, applies the class applicability rule table from
docs/LENSES_V1.md (14 lenses), and writes docs/LENSES_COVERAGE_V1.csv plus the
inventory-coverage section of docs/LENSES_V1.md (between fixed markers, so
reruns are idempotent). Every inapplicable lens carries a reason code; the
absolute/threshold candidate alias is counted once for planning only;
conditional lenses name their missing prerequisite. This does not measure
implemented predicates or certify the minimum-six gate. Deterministic output.
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

# Reasons distinguish semantic inapplicability from missing prerequisites.
REASONS = {
    'RANK_GLOBAL': 'market-global series: identical across stocks, no cross-stock rank',
    'POS_CAT': 'categorical/boolean has no ordered magnitude; use the declared share reading',
    'ABS_CAT': 'raw state code has no units; use a named-state indicator or declared share',
    'REL_NAMED': 'needs a named PIT benchmark/peer set before it certifies',
    'DIV_PAIR': 'needs a declared numeric pairing (e.g. vs price) before it certifies',
    'ONTOLOGY': 'ontology/rule control, not a measurement: no lens readings',
    'DROPPED': 'item dropped (GDELT news stays dropped, 2026-10-28): no lens readings',
}

# Measurement classes describe planning eligibility, not implemented predicates.
# Missing prerequisites become conditional below; semantic exclusions stay
# separate. Candidate aliases affect the planning count only, never the gate.
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

# A missing reference/pair is pending work, not semantic inapplicability
# (LENSES_V1 authority). Keep these labels in the potential plan and expose
# their prerequisites separately. No implementation is inferred from a class.
for _class, _rule in CLASS_RULES.items():
    _rule['conditional'] = {lens: why for lens, why in _rule['inapplicable'].items()
                            if why in ('REL_NAMED', 'DIV_PAIR')}
    _rule['inapplicable'] = {lens: why for lens, why in _rule['inapplicable'].items()
                             if why not in ('REL_NAMED', 'DIV_PAIR')}
    if _class == 'CATEGORICAL_STATE':
        _rule['applicable'].remove('divergence')
        _rule['conditional']['divergence'] = 'DIV_PAIR'

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


def potential_count(rule):
    """Planning labels after declared candidate aliases, not predicate proof."""
    labels = rule['applicable'] | set(rule['conditional'])
    n = len(labels)
    if rule.get('alias') and set(rule['alias']) <= labels:
        n -= 1
    return n


def build():
    with SOURCES.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 258, 'inventory must have 258 items'
    out = []
    class_counts = {}
    for row in sorted(rows, key=lambda r: r['id']):
        iid = row['id']
        cls, rule = classify(row)
        class_counts[cls] = class_counts.get(cls, 0) + 1
        excluded = cls.startswith('NO_QUESTIONS')
        flags = list(rule['flags']) + list(ITEM_FLAGS.get(iid, ()))
        out.append(dict(id=iid, item=row['item'], block=row['block'], cls=cls,
                        coverage_scope='CLASS_APPLICABILITY_ONLY',
                        applicable='|'.join(l for l in LENSES if l in rule['applicable']),
                        conditional='; '.join(f'{lens}={REASONS[why]}' for lens, why
                                              in sorted(rule['conditional'].items())),
                        potential_lens_count=str(potential_count(rule)),
                        candidate_alias='|'.join(rule.get('alias') or ()),
                        implemented_lens_count='0' if excluded else '',
                        implementation_status='NOT_APPLICABLE' if excluded else 'UNMEASURED',
                        minimum_6_status='NOT_APPLICABLE' if excluded else 'NOT_PROVEN',
                        inapplicable=inapplicable_text(cls, rule),
                        flags='; '.join(flags)))

    with COVERAGE_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'item', 'block', 'cls', 'applicable',
                                          'conditional', 'potential_lens_count', 'candidate_alias',
                                          'coverage_scope', 'implemented_lens_count',
                                          'implementation_status', 'minimum_6_status',
                                          'inapplicable', 'flags'], lineterminator='\n')
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
             'rule table below. This is **CLASS_APPLICABILITY_ONLY**, not measured',
             'implemented coverage. Missing named references/pairings are CONDITIONAL,',
             'not semantic inapplicability. Every exclusion still names its reason.',
             '`potential_lens_count` counts planning labels after the declared candidate',
             '`absolute`/`threshold` alias; actual expanded-predicate equality is unmeasured.',
             'For every measurable item, implemented count is unknown, implementation is',
             '**UNMEASURED**, and the minimum-six gate is **NOT_PROVEN**. Ontology/dropped',
             'items are NOT_APPLICABLE. No YES/NO rows or completed lens readings are',
             'certified here. Full table: `docs/LENSES_COVERAGE_V1.csv`.',
             '',
             '### Measurement-class rule table',
             '',
             '| Class | Items | Eligible labels | Conditional (prerequisite) | Inapplicable (reason) |',
             '|---|---:|---|---|---|']
    for cls in sorted(CLASS_RULES, key=lambda c: -class_counts.get(c, 0)):
        rule = CLASS_RULES[cls]
        if cls == 'NO_QUESTIONS':
            inapp = 'all 14 (ONTOLOGY: rule control, not a measurement)'
        elif cls == 'NO_QUESTIONS_DROPPED':
            inapp = 'all 14 (DROPPED: GDELT news stays dropped, 2026-10-28)'
        else:
            inapp = ', '.join(f'{l} ({REASONS[w].split(";")[0]})' for l, w in
                              sorted(rule['inapplicable'].items())) or '—'
        conditional = ', '.join(f'{lens} ({REASONS[why]})' for lens, why
                                 in sorted(rule['conditional'].items())) or '—'
        lines.append(f'| {cls} | {class_counts.get(cls, 0)} | '
                     f'{len(rule["applicable"])} of 14 | {conditional} | {inapp} |')
    lines += ['', 'Reason codes: ' + '; '.join(f'{k}: {v}' for k, v in REASONS.items()),
              '',
              '### Per-item coverage (258 rows)',
              '',
              '| id | item | class | potential lenses | implementation | minimum 6 | conditional | inapplicable | flags |',
              '|---|---|---|---:|---|---|---|---|---|']
    for r in out:
        inapp = r['inapplicable'] or '—'
        flags = r['flags'] or '—'
        item = r['item'].replace('|', '/')
        conditional = r['conditional'] or '—'
        lines.append(f"| {r['id']} | {item} | {r['cls']} | {r['potential_lens_count']} | "
                     f"{r['implementation_status']} | {r['minimum_6_status']} | {conditional} | {inapp} | {flags} |")
    lines.append(END)
    return '\n'.join(lines)


if __name__ == '__main__':
    out, counts = build()
    print('items:', len(out))
    print('classes:', dict(sorted(counts.items())))

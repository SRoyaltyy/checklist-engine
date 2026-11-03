"""Reviewed ladder equivalences; never dedupe by an item name.

Only explicitly reviewed dictionary scalars have spelling aliases. Every
other declaration is retained and unreviewed. The source CSV and all original
IDs remain recoverable through the review map.
"""
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

LADDERS = 'docs/BINARY_LADDERS_V1.csv'
ALIASES = 'BINARY_MASTER_LADDER_ALIASES_V1.csv'
REVIEW = 'BINARY_MASTER_LADDER_REVIEW_V1.csv'
RULE = 'DEFAULT_RSI_VALUE_DECLARATION_V1'
RSI_ITEMS = {'I024': 6, 'I025': 12, 'I026': 14, 'I027': 24}
SCALAR_PROOF = 'docs/LADDER_SCALAR_REVIEW_V2.json'
SCALAR_RULE = 'DEFAULT_SELECTED_SCALAR_DECLARATION_V2'
DICTIONARY = 'dictionary/WORLD_SNAPSHOT_DICTIONARY.csv'
SETTINGS = 'dictionary/INDICATOR_SETTINGS.json'
_PROOF_ROOT = Path(__file__).resolve().parent.parent
SCALAR_REVIEW = json.loads((_PROOF_ROOT / SCALAR_PROOF).read_bytes())
SCALAR_ITEMS = {r['item_id']: r for r in SCALAR_REVIEW['items']}
FIELDS = ('source_question_id', 'canonical_question_id', 'item_id', 'decision',
          'equivalence_rule', 'semantic_signature', 'reason')


def reviewed_signature(row):
    """Full reviewed predicate identity, or None for pending work.

    Both spellings name the same dictionary-default scalar/native endpoint.
    Comparator, threshold, missingness and availability remain verbatim.
    """
    period = RSI_ITEMS.get(row['item_id'])
    if period is None:
        return _scalar_signature(row)
    if period is None or row['item_name'] != f'RSI({period})':
        return None
    accepted = {f'RSI({period}) [{setting}] value on D-1 1d candle'
                for setting in ('default', 'default: dictionary default')}
    if row['feature'] not in accepted:
        return None
    if row['comparator'] not in ('<', '<=', '>', '>=', '=', '=='):
        return None
    try:
        if not Decimal(row['threshold']).is_finite():
            return None
    except InvalidOperation:
        return None
    meaning = dict(item_id=row['item_id'], field='RSI', period=period,
        setting='dictionary_default', candle_days=1, lookback_bars=1,
        endpoint='last_completed_before_setup_open', transform='identity',
        unit='RSI_points', comparator=row['comparator'], threshold=row['threshold'],
        missingness=row['not_evaluable_condition'], available=row['knowable_at_setup_open'])
    return json.dumps(meaning, sort_keys=True, separators=(',', ':'))


def _scalar_signature(row):
    proof = SCALAR_ITEMS.get(row['item_id'])
    if proof is None or row['item_name'] != proof['item_name']:
        return None
    accepted = {proof['item_name'] + ' [' + setting + '] value on D-1 1d candle'
                for setting in ('default', 'default: ' + proof['default_annotation'])}
    if row['feature'] not in accepted or row['comparator'] not in ('<', '<=', '>', '>=', '=', '=='):
        return None
    try:
        if not Decimal(row['threshold']).is_finite():
            return None
    except InvalidOperation:
        return None
    meaning = dict(item_id=row['item_id'], field=proof['selected_scalar'],
        parameters=proof['parameters'], dictionary_definition_sha256=proof['definition_sha256'],
        setting='dictionary_default', candle_days=1, lookback_bars=1,
        endpoint='last_completed_before_setup_open', transform='identity',
        unit=proof['unit'], comparator=row['comparator'], threshold=row['threshold'],
        missingness=row['not_evaluable_condition'], available=row['knowable_at_setup_open'])
    return json.dumps(meaning, sort_keys=True, separators=(',', ':'))


def _validate_scalar_proof(root, source):
    needed = {r['item_id'] for r in source} & SCALAR_ITEMS.keys()
    if not needed:
        return
    if json.loads((Path(root) / SCALAR_PROOF).read_bytes()) != SCALAR_REVIEW:
        raise ValueError('build-root scalar review differs from the reviewed code input')
    # A future dictionary/default change must be reviewed explicitly before
    # these equivalences can be reused. Same item names are insufficient.
    with (Path(root) / DICTIONARY).open(encoding='utf-8-sig', newline='') as stream:
        dictionary = {r['id']: r for r in csv.DictReader(stream)}
    registry = json.loads((Path(root) / SETTINGS).read_bytes())['items']
    for item in needed:
        proof, actual = SCALAR_ITEMS[item], dictionary[item]
        defaults = [s for s in registry[item]['settings'] if s['name'] == 'default']
        if (actual['item'] != proof['item_name'] or
                actual['definition'] != proof['dictionary_definition'] or
                hashlib.sha256(actual['definition'].encode()).hexdigest() != proof['definition_sha256'] or
                len(defaults) != 1 or defaults[0]['kind'] != 'native' or
                defaults[0]['parameters'] != proof['parameters']):
            raise ValueError('reviewed scalar dictionary/default changed: ' + item)


def review_ladders(root):
    with (Path(root) / LADDERS).open(encoding='utf-8-sig', newline='') as stream:
        source = list(csv.DictReader(stream))
    ids = [r['question_id'] for r in source]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate ladder source question ID')
    _validate_scalar_proof(root, source)
    seen, retained, review = {}, [], []
    for row in source:
        signature = reviewed_signature(row)
        if signature is not None:
            qid = row['question_id']
            seen[signature] = min(seen.get(signature, qid), qid)
    for row in source:
        qid = row['question_id']
        signature = reviewed_signature(row)
        canonical = seen[signature] if signature is not None else qid
        alias = canonical != qid
        if not alias:
            retained.append(row)
        review.append(dict(source_question_id=qid, canonical_question_id=canonical,
            item_id=row['item_id'], decision='ALIAS_VERIFIED' if alias else
                'KEEP_REVIEWED' if signature is not None else 'KEEP_UNREVIEWED',
            equivalence_rule=(RULE if row['item_id'] in RSI_ITEMS else SCALAR_RULE)
                if signature is not None else '',
            semantic_signature=signature or '',
            reason='Same reviewed default scalar, endpoint, comparator, threshold and NI/PIT policy; '
                   'only the default annotation differs.' if signature is not None else
                   'No reviewed normalized meaning yet; preserve the source row.'))
    aliases = [r for r in review if r['decision'] == 'ALIAS_VERIFIED']
    raw = Counter((r['item_id'], r['feature'], r['comparator'], r['threshold']) for r in source)
    return dict(source=source, retained=retained, review=review, aliases=aliases,
                reviewed_source_rows=sum(r['decision'] != 'KEEP_UNREVIEWED' for r in review),
                raw_text_duplicate_pairs=sum(n - 1 for n in raw.values()))


def write_review(root, result):
    for name, rows in ((ALIASES, result['aliases']), (REVIEW, result['review'])):
        with (Path(root) / 'docs' / name).open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

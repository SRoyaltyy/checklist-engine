"""Reviewed ladder equivalences; never dedupe by an item name.

Only an atomic default RSI value has a reviewed spelling alias. Every other
declaration is retained and unreviewed. The source CSV and all original IDs
remain recoverable through the review map.
"""
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

LADDERS = 'docs/BINARY_LADDERS_V1.csv'
ALIASES = 'BINARY_MASTER_LADDER_ALIASES_V1.csv'
REVIEW = 'BINARY_MASTER_LADDER_REVIEW_V1.csv'
RULE = 'DEFAULT_RSI_VALUE_DECLARATION_V1'
RSI_ITEMS = {'I024': 6, 'I025': 12, 'I026': 14, 'I027': 24}
FIELDS = ('source_question_id', 'canonical_question_id', 'item_id', 'decision',
          'equivalence_rule', 'semantic_signature', 'reason')


def reviewed_signature(row):
    """Full reviewed predicate identity, or None for pending work.

    Both spellings name the same dictionary-default scalar/native endpoint.
    Comparator, threshold, missingness and availability remain verbatim.
    """
    period = RSI_ITEMS.get(row['item_id'])
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


def review_ladders(root):
    with (Path(root) / LADDERS).open(encoding='utf-8-sig', newline='') as stream:
        source = list(csv.DictReader(stream))
    ids = [r['question_id'] for r in source]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate ladder source question ID')
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
            equivalence_rule=RULE if signature is not None else '',
            semantic_signature=signature or '',
            reason='Same default RSI scalar, endpoint, comparator, threshold and NI/PIT policy; '
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

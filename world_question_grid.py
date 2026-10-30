"""Lossless canonical v2.7.2.2 definition grid; not an answer evaluator.

The canonical question IDs and every registered cutoff value are retained.
One-at-a-time expansion includes the default vector once, not once per cutoff.
Semantic deduplication belongs to the bound feature/predicate layer.
"""
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
GRID = 'dials/v2.7.2.2/CUTOFF_GRID_v2.7.2.2.csv'
QUESTIONS = 'dials/v2.7.2.2/QUESTION_CUTOFFS_v2.7.2.2.csv'
TREE = 'dials/v2.7.1/tree/QUESTION_TREE_v2.7.1.csv'


def number(text):
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError):
        raise ValueError('non-numeric cutoff: '+str(text)) from None
    if not value.is_finite():
        raise ValueError('non-finite cutoff')
    return value


def canonical_number(text):
    value = number(text)
    if value == 0:
        return '0'
    # No binary float conversion, epsilon or decimal-context rounding.
    result = format(value, 'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


def identity(value):
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def unique(rows, key):
    result = {}
    for row in rows:
        if not row.get(key) or row[key] in result:
            raise ValueError('empty/duplicate '+key)
        result[row[key]] = row
    return result


@dataclass(frozen=True)
class Variant:
    source_question_id: str
    settings: tuple
    changed_cutoff: str = ''
    changed_value: str = ''

    @property
    def variant_id(self):
        return 'CV1-'+identity([self.source_question_id, self.settings])


class CanonicalGrid:
    def __init__(self, root=ROOT):
        root = Path(root)
        self.grid = unique(read_csv(root/GRID), 'cutoff_id')
        self.questions = unique(read_csv(root/QUESTIONS), 'question_id')
        self.tree = unique(read_csv(root/TREE), 'question_id')
        if self.questions.keys() != self.tree.keys():
            raise ValueError('canonical tree/cutoff question membership differs')
        self.values = {}
        for cid, row in self.grid.items():
            values = tuple(canonical_number(v) for v in row['grid_values'].split('|'))
            if len(values) != len(set(values)) or len(values) != int(row['grid_size']):
                raise ValueError('duplicate/mismatched registered values: '+cid)
            default = canonical_number(row['current_default'])
            if default not in values:
                raise ValueError('registered default absent: '+cid)
            self.values[cid] = values
        self.defaults = {}
        for qid, row in self.questions.items():
            defaults = {}
            for tag in filter(None, row['default_tags'].split(';')):
                cid, value = tag.split('=', 1)
                if cid in defaults or cid not in self.grid:
                    raise ValueError('duplicate/unregistered question cutoff: '+qid+' '+cid)
                value = canonical_number(value)
                if value != canonical_number(self.grid[cid]['current_default']):
                    raise ValueError('question/registry default differs: '+qid+' '+cid)
                defaults[cid] = value
            if len(defaults) != int(row['n_cutoffs']):
                raise ValueError('question cutoff count differs: '+qid)
            oat = 1+sum(len(self.values[cid])-1 for cid in defaults)
            cross = 1
            for cid in defaults:
                cross *= len(self.values[cid])
            if oat != int(row['versions_one_at_a_time']) or cross != int(row['versions_full_cross']):
                raise ValueError('declared variant count differs: '+qid)
            tree = self.tree[qid]
            prefix = {'base': 'B', 'history': 'H'}.get(tree['part'])
            expected = '|'.join([str(prefix), tree['L1_type'], tree['L3_derivative'], tree['L4_analysis'], tree['L2_timeframe']])
            if qid != expected or not re.fullmatch(r'[1-9][0-9]*x[1-9][0-9]*', tree['L2_timeframe']):
                raise ValueError('tree identity/timeframe differs: '+qid)
            self.defaults[qid] = tuple(sorted(defaults.items()))

    def variants(self, qid):
        defaults = self.defaults[qid]
        yield Variant(qid, defaults)
        for cid, default in defaults:
            for value in self.values[cid]:
                if value == default:
                    continue
                settings = dict(defaults);settings[cid] = value
                yield Variant(qid, tuple(sorted(settings.items())), cid, value)

    def all_variants(self):
        for qid in sorted(self.questions):
            yield from self.variants(qid)

    def audit(self):
        total = 0;digest = hashlib.sha256()
        for variant in self.all_variants():
            total += 1
            digest.update((variant.variant_id+'\n').encode())
        return dict(source_questions=len(self.questions), registered_cutoffs=len(self.grid),
                    cutoff_associations=sum(len(v) for v in self.defaults.values()),
                    oat_variants=total, ordered_variant_ids_sha256=digest.hexdigest(),
                    status='CANONICAL_GRID_ONLY_NOT_BINARY_MASTER_OR_ANSWER_PROOF')

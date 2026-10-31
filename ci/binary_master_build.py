"""Emit docs/BINARY_MASTER_V1.csv from all bound canonical binary definitions.

Runs the full 15,093-question / 154,667-OAT-variant canonical grid through
world_binary_master.bind_master_question, dedupes by computed semantic identity,
merges docs/BINARY_LADDERS_V1.csv as the add-on, and writes the master CSV plus
a JSON report with exact counts and fingerprints. Unbound families are counted
in the report, never silently skipped.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from world_question_grid import CanonicalGrid, GRID, QUESTIONS, TREE, ROOT
from world_binary_master import (FACETS, NOT_EVALUABLE, KNOWABLE, VIEWPORT,
                                 bind_master_question)

LADDERS = 'docs/BINARY_LADDERS_V1.csv'
MASTER_CSV = 'BINARY_MASTER_V1.csv'
REPORT = 'BINARY_MASTER_V1_REPORT.json'

CSV_COLUMNS = ['question_id', 'feature_id', 'definition_status', 'data_group', 'block', 'facet',
               'source_question_id', 'source_variant_id', 'source_outcome',
               'timeframe_days', 'lookback_bars', 'feature_recipe', 'feature_expression',
               'feature_kind', 'feature_unit', 'transform', 'comparator',
               'comparison_threshold', 'formula', 'yes_condition', 'not_evaluable_condition',
               'viewport_drawing', 'knowable_at_setup_open', 'expression', 'missing',
               'feature_json']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Compact per-row condition text: the full prose lives in the world_binary_master
# module constants and is copied verbatim into BINARY_MASTER_V1_REPORT.json by
# build(); repeating it on every CSV row pushed docs/BINARY_MASTER_V1.csv past
# GitHub's 100 MB file limit at 125 MB (batch 10). The reference keeps every
# row self-describing without the megabyte-scale duplication.
NOT_EVALUABLE_CSV = ('NOT_EVALUABLE (excluded, never NO): evidence bars insufficient or missing '
                     '(short history, missing/late native bar, non-positive/non-finite price), or '
                     'a documented definitional undefined (0/0 ratio, zero baseline or median, '
                     'zero range, non-contiguous baked-dial pairing). Full per-facet list: '
                     'world_binary_master.NOT_EVALUABLE')
KNOWABLE_CSV = ('All evidence bars end < setup date D with available_from <= D; the D open is '
                'execution only; no day-D candle. Full text: world_binary_master.KNOWABLE')
VIEWPORT_CSV = ('Purple recolour of the D-1 native candle if YES; measured value printed on the '
                'item pane header; no circles. Full text: world_binary_master.VIEWPORT')


def master_row(definition, tree_row):
    feature = definition['feature']
    return {'question_id': definition['question_id'],
            'feature_id': definition['feature_id'],
            'definition_status': definition['definition_status'],
            'data_group': tree_row['L1_type'], 'block': tree_row['L3_derivative'],
            'facet': tree_row['L4_analysis'],
            'source_question_id': definition['source_question_id'],
            'source_variant_id': definition['source_variant_id'],
            'source_outcome': definition['source_outcome'],
            'timeframe_days': feature.get('candle_days', ''),
            'lookback_bars': feature.get('lookback', ''),
            'feature_recipe': feature.get('recipe', ''),
            'feature_expression': definition['feature_expression'],
            'feature_kind': definition['feature_kind'],
            'feature_unit': definition['feature_unit'],
            'transform': feature.get('transform', ''),
            'comparator': definition['comparator'],
            'comparison_threshold': definition['comparison_threshold'],
            'formula': definition['formula'],
            'yes_condition': definition['formula'] + ' is TRUE',
            'not_evaluable_condition': NOT_EVALUABLE_CSV,
            'viewport_drawing': VIEWPORT_CSV, 'knowable_at_setup_open': KNOWABLE_CSV,
            'expression': definition['expression'], 'missing': definition['missing'],
            'feature_json': json.dumps(feature, sort_keys=True, separators=(',', ':'))}


def ladder_rows(root):
    path = root / LADDERS
    rows = []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            item = row['item_id']
            rows.append({'question_id': row['question_id'], 'feature_id': '', 'definition_status': 'LADDER_ADDON',
                         'data_group': 'ladders', 'block': item, 'facet': row['item_name'],
                         'source_question_id': '', 'source_variant_id': '', 'source_outcome': '',
                         'timeframe_days': '', 'lookback_bars': '',
                         'feature_recipe': 'ladder:' + item,
                         'feature_expression': row['feature'][:400], 'feature_kind': '',
                         'feature_unit': '', 'transform': '', 'comparator': row['comparator'],
                         'comparison_threshold': row['threshold'],
                         'formula': row['feature'][:400] + ' | ' + row['comparator'] + ' ' + row['threshold'],
                         'yes_condition': row['yes_condition'],
                         'not_evaluable_condition': row['not_evaluable_condition'],
                         'viewport_drawing': row['viewport_drawing'],
                         'knowable_at_setup_open': row['knowable_at_setup_open'],
                         'expression': 'PENDING_CLASSIFICATION', 'missing': 'ladder_add_on_pending_expression_lens_dedupe',
                         'feature_json': ''})
    return rows


def build(root):
    root = Path(root)
    source = CanonicalGrid(root)
    bound = {}
    aliases = []
    unbound = {}
    bound_sources = set()
    for variant in source.all_variants():
        row = source.tree[variant.source_question_id]
        try:
            questions = bind_master_question(row, variant)
        except NotImplementedError:
            key = (row['part'], row['L3_derivative'], row['L4_analysis'])
            unbound[key] = unbound.get(key, 0) + 1
            continue
        bound_sources.add(variant.source_question_id)
        for question in questions:
            qid = question['question_id']
            if qid not in bound:
                bound[qid] = (question, row)
            aliases.append(dict(question_id=qid, source_question_id=variant.source_question_id,
                                source_variant_id=variant.variant_id,
                                source_outcome=question['source_outcome']))

    ladder = ladder_rows(root)
    csv_path = root / 'docs' / MASTER_CSV
    with csv_path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator='\n')
        writer.writeheader()
        for qid in sorted(bound):
            writer.writerow(master_row(bound[qid][0], bound[qid][1]))
        writer.writerows(ladder)

    canonical_rows = len(bound)
    report = dict(
        canonical_questions=len(source.questions), oat_variants=sum(
            int(r['versions_one_at_a_time']) for r in source.questions.values()),
        bound_source_questions=len(bound_sources),
        bound_unique_binary_definitions=canonical_rows,
        bound_source_aliases=len(aliases),
        bound_families=sorted({k[2] for k in unbound} | set(FACETS)),
        batch1_bound_facets=sorted(FACETS),
        gpt_bound_fallback='world_binary_price.bind_price_question',
        unbound_family_variant_count=len(unbound),
        unbound_oat_variants=sum(unbound.values()),
        ladder_add_on_rows=len(ladder),
        dedupe_by_computed_meaning='PENDING_LADDER_VS_MASTER_AND_WITHIN_MASTER',
        master_total_rows=canonical_rows + len(ladder),
        csv_sha256=digest(csv_path),
        source_fingerprints={p: digest(root / p) for p in (GRID, QUESTIONS, TREE, LADDERS)},
        code_fingerprints={p: digest(Path(__file__).resolve().parent.parent / p) for p in
                           ('world_binary_master.py', 'world_binary_price.py',
                            'world_binary_questions.py', 'ci/binary_master_build.py')},
        answer_generation='NOT_RUN', chart_gate='NOT_PASSED', mining='NOT_RUN',
        condition_docs={'not_evaluable_condition': NOT_EVALUABLE,
                        'knowable_at_setup_open': KNOWABLE,
                        'viewport_drawing': VIEWPORT,
                        'csv_note': 'CSV rows carry compact condition text with a reference to '
                                    'world_binary_master; full prose is this report field and '
                                    'the module constants.'})
    report_path = root / 'docs' / REPORT
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(build(args.root), indent=2))

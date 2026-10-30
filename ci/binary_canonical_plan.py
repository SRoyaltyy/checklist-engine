"""Enumerate the entire canonical grid and emit explicitly bound definitions.

This is a source-definition plan, not BINARY_MASTER completion or a real-data
answer producer. Unbound canonical families are counted, never silently skipped.
"""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
from world_question_grid import CanonicalGrid, GRID, QUESTIONS, TREE, ROOT
from world_binary_price import bind_price_question

LENSES=('absolute','relative','position','threshold','divergence','outlier','path','streak','cross',
        'change_since_last','rank_vs_market_or_sector','percentile','extreme_vs_own_history','timeframe')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(root, out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=CanonicalGrid(root);bound={};aliases=[];unbound=Counter();bound_sources=set()
    plan=out/'CANONICAL_VARIANT_PLAN_V1.csv.gz'
    with plan.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as compressed:
            import io
            with io.TextIOWrapper(compressed,encoding='utf-8',newline='') as stream:
                writer=csv.writer(stream,lineterminator='\n')
                writer.writerow(['source_question_id','variant_id','changed_cutoff','changed_value','settings_json'])
                for variant in source.all_variants():
                    writer.writerow([variant.source_question_id,variant.variant_id,variant.changed_cutoff,
                                     variant.changed_value,json.dumps(dict(variant.settings),sort_keys=True,separators=(',',':'))])
                    row=source.tree[variant.source_question_id]
                    try:
                        questions=bind_price_question(row,variant)
                    except NotImplementedError:
                        unbound[(row['part'],row['L3_derivative'],row['L4_analysis'])]+=1
                        continue
                    bound_sources.add(variant.source_question_id)
                    for question in questions:
                        qid=question['question_id']
                        if qid not in bound:
                            bound[qid]=question
                        aliases.append(dict(question_id=qid,source_question_id=variant.source_question_id,
                                            source_variant_id=variant.variant_id,source_outcome=question['source_outcome']))
    definitions=out/'BOUND_PRICE_DEFINITIONS_V1.jsonl'
    with definitions.open('w',encoding='utf-8',newline='') as stream:
        for qid in sorted(bound):
            stream.write(json.dumps(bound[qid],sort_keys=True,separators=(',',':'))+'\n')
    alias_file=out/'BOUND_PRICE_SOURCE_ALIASES_V1.csv'
    with alias_file.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['question_id','source_question_id','source_variant_id','source_outcome'],lineterminator='\n')
        writer.writeheader();writer.writerows(aliases)
    missing=out/'UNBOUND_CANONICAL_FAMILIES_V1.csv'
    with missing.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['part','variant','facet','oat_versions','missing'])
        writer.writerows([*key,value,'exact_feature_and_cutoff_binding'] for key,value in sorted(unbound.items()))
    lenses=out/'CANONICAL_LENS_COVERAGE_V1.csv'
    with lenses.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n')
        writer.writerow(['source_question_id','implemented_lenses','implemented_count','fewer_than_six',
                         'pending_lenses_json','applicability_review','missing'])
        for qid in sorted(source.questions):
            implemented='absolute|threshold' if qid in bound_sources else ''
            pending=[name for name in LENSES if not implemented or name not in ('absolute','threshold')]
            writer.writerow([qid,implemented,int(bool(implemented)),'YES',
                json.dumps(pending,separators=(',',':')),'PENDING_NO_INAPPLICABILITY_INFERRED_FROM_MISSING_CODE',
                'remaining_applicable_lens_bindings_and_applicability_review'])
    report=source.audit()
    report.update(bound_source_questions=len(bound_sources),bound_unique_binary_definitions=len(bound),
                  bound_source_aliases=len(aliases),unbound_oat_variants=sum(unbound.values()),
                  canonical_questions_flagged_fewer_than_six_lenses=len(source.questions),
                  requested_lenses=list(LENSES),absolute_threshold_alias_credit='COUNT_ONCE_FOR_IDENTICAL_FIXED_LEVEL_PREDICATE',
                  full_binary_master='INCOMPLETE',real_answer_generation='NOT_RUN',chart_gate='NOT_PASSED',mining='NOT_RUN',
                  native_bar_definition='FIXED_SHARED_SESSION_CALENDAR_V1; legacy rolling-offset artifacts unchanged',
                  source_fingerprints={p:dict(raw_sha256=digest(root/p),
                      lf_sha256=hashlib.sha256((root/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()) for p in (GRID,QUESTIONS,TREE)},
                  code_fingerprints={p:digest(root/p) for p in ('world_question_grid.py','world_binary_price.py','ci/binary_canonical_plan.py')},
                  artifact_fingerprints={p.name:digest(p) for p in (plan,definitions,alias_file,missing,lenses)})
    (out/'BINARY_CANONICAL_PLAN_V1.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(generate(args.root,args.out)))

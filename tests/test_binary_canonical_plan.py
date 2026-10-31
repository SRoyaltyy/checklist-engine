import csv
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import pytest
from world_question_grid import CanonicalGrid, GRID, QUESTIONS, TREE, canonical_number
from world_binary_price import NativeCandle,bind_price_question,evaluate_price,measurement


@pytest.fixture(scope='module')
def catalog():
    return CanonicalGrid()


def test_entire_canonical_grid_retains_every_question_cutoff_and_oat_version(catalog):
    report=catalog.audit()
    assert (report['source_questions'],report['registered_cutoffs'],report['cutoff_associations'],report['oat_variants'])==(15093,232,35647,154667)
    assert report['ordered_variant_ids_sha256']=='5d01e4094af9dab4f5016690458fbded66e0eadfdee5ffbd8170ad29045ccdc5'


def test_oat_changes_only_one_cutoff_and_contains_every_registered_rung(catalog):
    qid='H|candles|OHLC|divergence_sync|1x10'
    variants=list(catalog.variants(qid));default=dict(variants[0].settings)
    assert len(variants)==13 and len({v.variant_id for v in variants})==13
    for variant in variants[1:]:
        differences=[k for k,v in variant.settings if v!=default[k]]
        assert differences==[variant.changed_cutoff]
    for cid in default:
        assert {dict(v.settings)[cid] for v in variants}==set(catalog.values[cid])


def test_missing_canonical_rung_cannot_be_hidden_by_editing_declared_counts(tmp_path):
    source=Path(__file__).resolve().parents[1]
    for name in (GRID,QUESTIONS,TREE):
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((source/name).read_bytes())
    file=tmp_path/GRID
    rows=list(csv.DictReader(file.open(encoding='utf-8-sig')))
    row=next(r for r in rows if r['cutoff_id']=='C001_intraday_change__pct1')
    row['grid_values']='|'.join(row['grid_values'].split('|')[:-1]);row['grid_size']=str(int(row['grid_size'])-1)
    with file.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='variant count differs'):CanonicalGrid(tmp_path)


def definitions(catalog,kind='intraday_change'):
    timeframe='1x3' if kind=='intraday_change' else '1x10'
    qid=next(q for q,r in catalog.tree.items() if r['L4_analysis']==kind and r['L2_timeframe']==timeframe and r['L3_derivative']=='OHLC' and r['part']=='base')
    return [bind_price_question(catalog.tree[qid],v) for v in catalog.variants(qid)]


def bars(opened=(100.,200.,50.),close=(102.,202.,50.)):
    return {i:NativeCandle(date(2024,1,i+2),date(2024,1,i+3),o,c) for i,(o,c) in enumerate(zip(opened,close))}


def answers(definitions,b):
    return {q['source_outcome']:evaluate_price(q,b,date(2024,1,5),2).answer for q in definitions}


def test_intraday_uses_mean_of_bar_returns_not_return_of_aggregate_price(catalog):
    result=answers(definitions(catalog)[0],bars())
    assert result=={'up':'NO','down':'NO','flat':'YES'}
    assert answers(definitions(catalog)[0],bars((100.,100.,100.),(102.,102.,102.)))['up']=='YES'


def test_every_registered_price_cutoff_is_bound_not_only_default(catalog):
    groups=definitions(catalog)
    assert len(groups)==5
    b=bars((100.,100.,100.),(101.2,101.2,101.2))
    truths=[answers(group,b)['up'] for group in groups]
    assert set(truths)=={'YES','NO'}
    assert len({q['comparison_threshold'] for group in groups for q in group if q['source_outcome']=='up'})==5


def test_interday_uses_first_and_last_close_and_preserves_bucket_meaning(catalog):
    group=definitions(catalog,'interday_change')[0]
    def result(closes):
        b=bars((100.,)*10,closes)
        return {q['source_outcome']:evaluate_price(q,b,date(2024,1,12),9).answer for q in group}
    assert result((100.,500.)+(100.,)*8)=={'up':'NO','flat':'YES','down':'NO'}
    assert result((100.,)*9+(110.,))['up']=='YES'
    assert result((100.,)*9+(90.,))['down']=='YES'


@pytest.mark.parametrize('bad',['missing_slot','missing_price','missing_availability','future_availability','setup_candle','zero_open'])
def test_missing_or_not_yet_known_input_never_becomes_no(catalog,bad):
    b=bars()
    if bad=='missing_slot':del b[1]
    elif bad=='missing_price':b[1]=replace(b[1],close=None)
    elif bad=='missing_availability':b[1]=replace(b[1],available_from=None)
    elif bad=='future_availability':b[1]=replace(b[1],available_from=date(2024,1,8))
    elif bad=='setup_candle':b[1]=replace(b[1],end=date(2024,1,5),available_from=date(2024,1,8))
    else:b[1]=replace(b[1],open=0.)
    assert set(answers(definitions(catalog)[0],b).values())=={'NOT_EVALUABLE'}


def test_setup_and_future_prices_are_never_read(catalog):
    class Forbidden:
        def __getattribute__(self,key):raise AssertionError('future price accessed')
    b=bars();b[3]=Forbidden();b[999]=Forbidden()
    assert answers(definitions(catalog)[0],b)=={'up':'NO','down':'NO','flat':'YES'}


def test_slot_order_cannot_hide_duplicate_or_reversed_native_ends(catalog):
    b=bars();b[1]=replace(b[1],end=b[0].end)
    with pytest.raises(ValueError,match='increase strictly'):answers(definitions(catalog)[0],b)


def test_price_definition_cannot_ignore_extra_cutoffs_or_change_source_identity(catalog):
    qid='B|candles|OHLC|intraday_change|1x3';variant=next(catalog.variants(qid));row=catalog.tree[qid]
    with pytest.raises(ValueError,match='ignore a cutoff'):
        bind_price_question(row,replace(variant,settings=variant.settings+(('unbound','1'),)))
    with pytest.raises(ValueError,match='question differ'):
        bind_price_question(row,replace(variant,source_question_id='other'))
    with pytest.raises(NotImplementedError):measurement('unknown',{},date(2024,1,5),2,3)


def test_numerical_spelling_and_large_decimal_precision_are_not_rounded():
    assert canonical_number('1.00')==canonical_number('1e0')=='1'
    assert canonical_number('-0.00')=='0'
    assert canonical_number('123456789012345678901234567890.125')=='123456789012345678901234567890.125'


@pytest.mark.parametrize('close,outcome',[
    ((100.,101.,102.,101.),'green_longer'),((100.,99.,98.,99.),'red_longer'),
    ((100.,101.,100.,101.),'equal'),((100.,100.,100.,100.),'equal')])
def test_close_streaks_use_n_changes_not_body_colours_and_keep_signed_integer_difference(catalog,close,outcome):
    qid='B|candles|OHLC|run_structure|1x3';variant=next(catalog.variants(qid))
    assert not variant.settings
    definitions=bind_price_question(catalog.tree[qid],variant)
    b=bars((200.,)*4,close)
    answer={q['source_outcome']:evaluate_price(q,b,date(2024,1,6),3).answer for q in definitions}
    assert answer[outcome]=='YES' and list(answer.values()).count('YES')==1
    assert type(measurement('run_structure',b,date(2024,1,6),3,3)) is int
    assert all(q['feature_kind']=='signed_integer' and q['comparison_threshold']=='0' for q in definitions)
    from world_binary_questions import evaluate_binary
    value=measurement('run_structure',b,date(2024,1,6),3,3)
    assert {q['source_outcome']:evaluate_binary(value,q['comparator'],q['comparison_threshold'],
            feature_kind=q['feature_kind']).answer for q in definitions}==answer
    b={k:replace(v,open=None) for k,v in b.items()}
    assert evaluate_price(next(q for q in definitions if q['source_outcome']==outcome),b,date(2024,1,6),3).answer=='YES'
    del b[0]
    assert {evaluate_price(q,b,date(2024,1,6),3).answer for q in definitions}=={'NOT_EVALUABLE'}


def test_plan_keeps_pending_stages_and_unbound_families_visible(tmp_path):
    from ci.binary_canonical_plan import generate
    report=generate(Path(__file__).resolve().parents[1],tmp_path)
    assert report['oat_variants']==154667 and report['unbound_oat_variants']>0
    assert report['full_binary_master']=='INCOMPLETE' and report['mining']=='NOT_RUN'
    assert report['canonical_questions_flagged_fewer_than_six_lenses']==15093
    values=[json.loads(line) for line in (tmp_path/'BOUND_PRICE_DEFINITIONS_V1.jsonl').read_text().splitlines()]
    assert len(values)==report['bound_unique_binary_definitions']>0
    assert all(q['expression']=='NOT_YET' and q['chart_status']=='PENDING' for q in values)
    assert len(report['requested_lenses'])==14
    coverage=list(csv.DictReader((tmp_path/'CANONICAL_LENS_COVERAGE_V1.csv').open(encoding='utf-8')))
    bound=next(r for r in coverage if r['implemented_lenses'])
    assert bound['implemented_lenses']=='absolute|threshold' and bound['implemented_count']=='1'
    assert len(json.loads(bound['pending_lenses_json']))==12


def test_price_adapter_enforces_the_declared_measurement_type(catalog):
    definition=definitions(catalog)[0][0]
    definition=dict(definition,feature_kind='integer_count')
    with pytest.raises(ValueError,match='discrete feature must be an integer'):
        evaluate_price(definition,bars(),date(2024,1,6),2)

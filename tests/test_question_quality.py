import csv,json
from pathlib import Path
import pytest,subprocess,sys
from ci.question_quality import evaluate,tree_digest,variable_digest,outcome_keys,CORE_FACETS,BINARY_CODE_PATH


def fixture(tmp_path):
    tree=tmp_path/'tree.csv';tallies=tmp_path/'tallies.csv'
    fields=['question_id','item_id','block','derivative','facet','candle_days','lookback','threshold','direction','formula','inputs','pit_rule','answer_set',
            'feature_id','feature_expression','feature_kind','feature_unit','comparator','comparison_threshold','feature_categories']
    count=0
    with tree.open('w',newline='') as stream,tallies.open('w',newline='') as answer:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        aw=csv.DictWriter(answer,fieldnames=['question_id','n_total','n_evaluable','n_not_evaluable','answer_counts']);aw.writeheader()
        for iid,block in [('PRICE','A'),('INSIDER','E')]:
            for facet in CORE_FACETS:
                for k in range(1,22):
                    for window in (10,20,60):
                        for threshold in (1,2,3):
                            for direction in ('above','below'):
                                qid=f'{iid}:{facet}:{k}:{window}:{threshold}:{direction}'
                                fid=f'{iid}:{facet}:{k}:{window}:{threshold}'
                                expression=f'synthetic_feature({fid})';comparator='>' if direction=='above' else '<'
                                writer.writerow(dict(question_id=qid,item_id=iid,block=block,derivative='raw',facet=facet,candle_days=k,lookback=window,
                                    threshold=threshold,direction=direction,formula=f'({expression}) {comparator} 0',inputs=iid+'__'+str(k)+'d',
                                    pit_rule='available_from < D',answer_set='["NO","YES"]',feature_id=fid,feature_expression=expression,
                                    feature_kind='continuous',feature_unit='synthetic_units',comparator=comparator,comparison_threshold='0',feature_categories=''))
                                aw.writerow(dict(question_id=qid,n_total=600,n_evaluable=600,n_not_evaluable=0,
                                                 answer_counts=json.dumps({'"NO"':240,'"YES"':360})))
                                count+=1
    catalog=[dict(item_id='PRICE',block='A',is_price_volume=True),dict(item_id='INSIDER',block='E',is_price_volume=False)]
    variables=[dict(item_id=item['item_id'],facet=facet,derivative='raw',lookbacks=[10,20,60],
                    thresholds=['1','2','3'],directions=['above','below'],binary_predicates={
                        'above':[dict(comparator='>',comparison_threshold='0')],
                        'below':[dict(comparator='<',comparison_threshold='0')]}) for item in catalog for facet in CORE_FACETS]
    ledger=tmp_path/'sample_rows.csv'
    with ledger.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['ticker','date']);writer.writeheader()
        writer.writerows(dict(ticker=f'S{i}',date=f'{year}-01-04') for i in range(200) for year in (2020,2021,2022))
    sample=dict(tickers=[f'S{i}' for i in range(200)],years=[2020,2021,2022],rows=600,input_manifest_sha256='a'*64,
                question_tree_sha256=tree_digest([tree]),tallies_sha256=tree_digest([tallies]),
                variable_grid_sha256=variable_digest(variables),sample_rows_sha256=tree_digest([ledger]),answer_semantics='STRICT_BINARY_V1',
                binary_predicate_code_sha256=tree_digest([BINARY_CODE_PATH]))
    return catalog,tree,tallies,sample,count,variables,ledger


def test_complete_grid_with_bound_measured_tallies_passes(tmp_path):
    catalog,tree,tallies,sample,count,variables,ledger=fixture(tmp_path)
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert not errors
    assert sum(r['question_count'] for r in report)==count
    assert all(r['status']=='PASS' for r in report)


def test_claimed_count_without_measured_answers_cannot_pass(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    report,_,_=evaluate(catalog,[tree],[],sample,variables=variables,sample_rows=ledger)
    assert all(r['status']=='FAIL' for r in report)
    assert 'missing measured answer tally' in report[0]['reasons']


def test_insufficient_sample_and_tree_version_fail(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    sample['tickers']=sample['tickers'][:199];sample['question_tree_sha256']='different'
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert len(errors)>=2
    assert all(r['status']=='FAIL' for r in report)


def test_constant_question_fails(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    records=list(csv.DictReader(tallies.open()))
    records[0]['answer_counts']=json.dumps({'"YES"':600})
    with tallies.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    sample['tallies_sha256']=tree_digest([tallies])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert report[0]['status']=='FAIL'
    assert 'constant question' in report[0]['reasons']


def rewrite(file,records):
    with file.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)


def test_three_marginal_axis_counts_do_not_prove_the_full_cross_product(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    questions=list(csv.DictReader(tree.open()));answers=list(csv.DictReader(tallies.open()))
    removed=questions.pop(0)['question_id'];answers=[r for r in answers if r['question_id']!=removed]
    rewrite(tree,questions);rewrite(tallies,answers)
    sample.update(question_tree_sha256=tree_digest([tree]),tallies_sha256=tree_digest([tallies]))
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert not errors and report[0]['status']=='FAIL'
    assert 'incomplete declared variable cross-product' in report[0]['reasons']


def test_registered_fourth_threshold_cannot_be_omitted_even_when_three_are_present(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    variables[0]['thresholds'].append('4');sample['variable_grid_sha256']=variable_digest(variables)
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert report[0]['status']=='FAIL' and 'incomplete declared variable cross-product' in report[0]['reasons']


@pytest.mark.parametrize('field',['tallies_sha256','variable_grid_sha256','sample_rows_sha256','input_manifest_sha256','binary_predicate_code_sha256'])
def test_unbound_evidence_cannot_pass(tmp_path,field):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    sample[field]='unbound'
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert errors and all(r['status']=='FAIL' for r in report)


@pytest.mark.parametrize('bad',['{"9":240,"1":360}','{"0":true,"1":599}','{"0":0.5,"1":599.5}',
                               '{"0":240,"0":200,"1":360}','not-json'])
def test_invalid_or_undeclared_outcomes_never_pass_as_measured_answers(tmp_path,bad):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    answers=list(csv.DictReader(tallies.open()));answers[0]['answer_counts']=bad;rewrite(tallies,answers)
    sample['tallies_sha256']=tree_digest([tallies])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert report[0]['status']=='FAIL'


def test_orphan_tally_is_not_ignored(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    answers=list(csv.DictReader(tallies.open()));answers.append(dict(answers[0],question_id='not-in-tree'));rewrite(tallies,answers)
    sample['tallies_sha256']=tree_digest([tallies])
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert 'tallies contain unknown question IDs' in errors and all(r['status']=='FAIL' for r in report)


def test_declared_stock_count_cannot_replace_actual_stock_day_evidence(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    records=list(csv.DictReader(ledger.open()));records[-1]=records[0];rewrite(ledger,records)
    sample['sample_rows_sha256']=tree_digest([ledger])
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert 'duplicate sample stock-day' in errors and all(r['status']=='FAIL' for r in report)


def test_missing_declared_grid_or_stock_day_file_never_gets_legacy_pass(tmp_path):
    catalog,tree,tallies,sample,_,_,_=fixture(tmp_path)
    report,_,errors=evaluate(catalog,[tree],[tallies],sample)
    assert 'declared variable grid missing' in errors and 'sample stock-day evidence missing' in errors
    assert all(r['status']=='FAIL' for r in report)


@pytest.mark.parametrize('corruption',['block','answer_set','duplicate_combination','outside_grid'])
def test_tree_metadata_does_not_bypass_declared_catalog_and_grid(tmp_path,corruption):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    questions=list(csv.DictReader(tree.open()))
    if corruption=='block':questions[0]['block']='FAKE'
    elif corruption=='answer_set':questions[0]['answer_set']='[0,0]'
    elif corruption=='outside_grid':questions[0]['threshold']='99'
    else:
        # Keep ID/formula unique while trying to count the same parameter combination twice.
        questions[1].update({key:questions[0][key] for key in ('lookback','threshold','direction')})
    rewrite(tree,questions);sample['question_tree_sha256']=tree_digest([tree])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert report[0]['status']=='FAIL'


def test_string_thresholds_are_not_a_valid_axis_list(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    variables[0]['thresholds']='123';sample['variable_grid_sha256']=variable_digest(variables)
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert errors and all(r['status']=='FAIL' for r in report)


def test_cli_requires_bound_artifacts_and_writes_failure_evidence_for_empty_catalog(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    paths={name:tmp_path/(name+'.json') for name in ('catalog','variables','sample')}
    for name,value in [('catalog',catalog),('variables',variables),('sample',sample)]:paths[name].write_text(json.dumps(value),encoding='utf-8')
    output=tmp_path/'quality'
    command=[sys.executable,'-m','ci.question_quality','--catalog',str(paths['catalog']),'--tree',str(tree),
             '--tallies',str(tallies),'--sample',str(paths['sample']),'--variables',str(paths['variables']),
             '--sample-rows',str(ledger),'--out',str(output)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    measured=json.loads((output/'QUESTION_QUALITY_SUMMARY.json').read_text())
    assert measured['status']=='PASS'
    assert measured['evidence']['sample_rows_sha256']==tree_digest([ledger])
    assert measured['evidence']['tallies_sha256']==tree_digest([tallies])
    paths['catalog'].write_text('[]')
    failed=subprocess.run(command,capture_output=True,text=True)
    assert failed.returncode==1
    assert json.loads((output/'QUESTION_QUALITY_SUMMARY.json').read_text())['status']=='FAIL'
    assert (output/'QUESTION_QUALITY.csv').read_text().startswith('item_id,block,status,reasons')


@pytest.mark.parametrize('answers',['[0,0.0]','[0,-0.0]'])
def test_numeric_spellings_of_the_same_outcome_cannot_fake_variability(answers):
    with pytest.raises(ValueError,match='duplicate numeric'):outcome_keys(answers)


@pytest.mark.parametrize('field,value,reason',[
    ('answer_set','[0,1,2]','invalid fixed answer set'),
    ('comparator','above','invalid binary definition'),
    ('comparison_threshold','ATR * 0.5','literal number'),
    ('comparison_threshold','NaN','literal number'),
    ('formula','A categorical answer, not a binary predicate','explicit binary predicate'),
    ('feature_kind','untyped','unknown feature kind'),
    ('feature_unit','','blank metadata'),
])
def test_binary_definition_is_required_not_just_balanced_tallies(tmp_path,field,value,reason):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    questions=list(csv.DictReader(tree.open()));questions[0][field]=value;rewrite(tree,questions)
    sample['question_tree_sha256']=tree_digest([tree])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert report[0]['status']=='FAIL' and reason in report[0]['reasons']


def test_unknown_rows_are_excluded_and_denominators_reconcile(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    answers=list(csv.DictReader(tallies.open()))
    answers[0].update(n_evaluable=590,n_not_evaluable=10,answer_counts=json.dumps({'"NO"':230,'"YES"':360}))
    rewrite(tallies,answers);sample['tallies_sha256']=tree_digest([tallies])
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert not errors and all(r['status']=='PASS' for r in report)
    answers[0]['n_not_evaluable']=0;rewrite(tallies,answers);sample['tallies_sha256']=tree_digest([tallies])
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert any('evaluable/excluded counts do not reconcile' in e for e in errors)
    assert all(r['status']=='FAIL' for r in report)


def test_not_evaluable_is_not_an_answer_outcome(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    answers=list(csv.DictReader(tallies.open()))
    answers[0].update(n_evaluable=600,n_not_evaluable=0,
                      answer_counts=json.dumps({'"NO"':230,'"YES"':360,'"NOT_EVALUABLE"':10}))
    rewrite(tallies,answers);sample['tallies_sha256']=tree_digest([tallies])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert report[0]['status']=='FAIL' and 'measured outcome outside fixed answer set' in report[0]['reasons']


def test_legacy_sample_cannot_inherit_binary_acceptance(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    sample.pop('answer_semantics')
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert 'strict binary sample semantics missing' in errors and all(r['status']=='FAIL' for r in report)


def test_different_measurements_cannot_reuse_a_feature_id(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    questions=list(csv.DictReader(tree.open()));questions[2]['feature_id']=questions[0]['feature_id'];rewrite(tree,questions)
    sample['question_tree_sha256']=tree_digest([tree])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert 'feature ID reused for different measurements' in report[0]['reasons']


def test_alternative_numeric_spelling_cannot_inflate_binary_question_depth(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    questions=list(csv.DictReader(tree.open()))
    questions[1].update(comparator='>',comparison_threshold='0.0',formula=f"({questions[0]['feature_expression']}) > 0.0")
    rewrite(tree,questions);sample['question_tree_sha256']=tree_digest([tree])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert 'duplicate binary predicate under different question IDs' in report[0]['reasons']


def test_registered_binary_ladder_is_expanded_and_no_rung_can_disappear(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    variables[0]['binary_predicates']['above'].append(dict(comparator='>=',comparison_threshold='1'))
    questions=list(csv.DictReader(tree.open()));answers=list(csv.DictReader(tallies.open()));extra=[]
    for row in questions:
        if row['item_id']=='PRICE' and row['facet']=='absolute' and row['direction']=='above':
            extra.append(dict(row,question_id=row['question_id']+':ladder',comparator='>=',comparison_threshold='1',
                              formula=f"({row['feature_expression']}) >= 1"))
    questions+=extra
    answers.extend(dict(answers[0],question_id=row['question_id']) for row in extra)
    rewrite(tree,questions);rewrite(tallies,answers)
    sample.update(question_tree_sha256=tree_digest([tree]),tallies_sha256=tree_digest([tallies]),
                  variable_grid_sha256=variable_digest(variables))
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert not errors and all(r['status']=='PASS' for r in report)
    removed=questions.pop()['question_id'];answers=[r for r in answers if r['question_id']!=removed]
    rewrite(tree,questions);rewrite(tallies,answers)
    sample.update(question_tree_sha256=tree_digest([tree]),tallies_sha256=tree_digest([tallies]))
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert not errors and 'incomplete declared variable cross-product' in report[0]['reasons']


def test_same_numeric_ladder_rung_cannot_be_registered_twice(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    variables[0]['binary_predicates']['above'].append(dict(comparator='>',comparison_threshold='0.0'))
    sample['variable_grid_sha256']=variable_digest(variables)
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert any('duplicate numeric predicate' in e for e in errors) and all(r['status']=='FAIL' for r in report)


def test_category_code_features_require_named_codes_and_equality_predicates(tmp_path):
    catalog,tree,tallies,sample,_,variables,ledger=fixture(tmp_path)
    questions=list(csv.DictReader(tree.open()))
    for row in questions:
        row.update(feature_kind='category_code',feature_categories='{"0":"none","1":"event"}',
                   comparator='=' if row['direction']=='above' else '!=',comparison_threshold='1')
        row['formula']=f"({row['feature_expression']}) {row['comparator']} 1"
    for spec in variables:
        spec['binary_predicates']={d:[dict(comparator='=' if d=='above' else '!=',comparison_threshold='1')]
                                   for d in spec['directions']}
    rewrite(tree,questions)
    sample.update(question_tree_sha256=tree_digest([tree]),variable_grid_sha256=variable_digest(variables))
    report,_,errors=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert not errors and all(r['status']=='PASS' for r in report)
    questions[0]['feature_categories']='{"0":"none","0":"event"}';rewrite(tree,questions)
    sample['question_tree_sha256']=tree_digest([tree])
    report,_,_=evaluate(catalog,[tree],[tallies],sample,variables=variables,sample_rows=ledger)
    assert 'duplicate category code' in report[0]['reasons']

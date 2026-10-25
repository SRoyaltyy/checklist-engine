import csv,json
from pathlib import Path
from ci.question_quality import evaluate,tree_digest,CORE_FACETS


def fixture(tmp_path):
    tree=tmp_path/'tree.csv';tallies=tmp_path/'tallies.csv'
    fields=['question_id','item_id','block','derivative','facet','candle_days','lookback','threshold','direction','formula','inputs','pit_rule','answer_set']
    count=0
    with tree.open('w',newline='') as stream,tallies.open('w',newline='') as answer:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        aw=csv.DictWriter(answer,fieldnames=['question_id','n_total','answer_counts']);aw.writeheader()
        for iid,block in [('PRICE','A'),('INSIDER','E')]:
            for facet in CORE_FACETS:
                for k in range(1,22):
                    for window in (10,20,60):
                        for threshold in (1,2,3):
                            for direction in ('above','below'):
                                qid=f'{iid}:{facet}:{k}:{window}:{threshold}:{direction}'
                                writer.writerow(dict(question_id=qid,item_id=iid,block=block,derivative='raw',facet=facet,candle_days=k,lookback=window,
                                    threshold=threshold,direction=direction,formula=qid+' defined expression',inputs=iid+'__'+str(k)+'d',
                                    pit_rule='available_from < D',answer_set='[0,1]'))
                                aw.writerow(dict(question_id=qid,n_total=100,answer_counts=json.dumps({'0':40,'1':60})))
                                count+=1
    catalog=[dict(item_id='PRICE',block='A',is_price_volume=True),dict(item_id='INSIDER',block='E',is_price_volume=False)]
    sample=dict(tickers=[f'S{i}' for i in range(200)],years=[2020,2021,2022],rows=100,input_manifest_sha256='fixture',question_tree_sha256=tree_digest([tree]))
    return catalog,tree,tallies,sample,count


def test_complete_grid_with_bound_measured_tallies_passes(tmp_path):
    catalog,tree,tallies,sample,count=fixture(tmp_path)
    report,_,errors=evaluate(catalog,[tree],[tallies],sample)
    assert not errors
    assert sum(r['question_count'] for r in report)==count
    assert all(r['status']=='PASS' for r in report)


def test_claimed_count_without_measured_answers_cannot_pass(tmp_path):
    catalog,tree,tallies,sample,_=fixture(tmp_path)
    report,_,_=evaluate(catalog,[tree],[],sample)
    assert all(r['status']=='FAIL' for r in report)
    assert 'missing measured answer tally' in report[0]['reasons']


def test_insufficient_sample_and_tree_version_fail(tmp_path):
    catalog,tree,tallies,sample,_=fixture(tmp_path)
    sample['tickers']=sample['tickers'][:199];sample['question_tree_sha256']='different'
    report,_,errors=evaluate(catalog,[tree],[tallies],sample)
    assert len(errors)>=2
    assert all(r['status']=='FAIL' for r in report)


def test_constant_question_fails(tmp_path):
    catalog,tree,tallies,sample,_=fixture(tmp_path)
    records=list(csv.DictReader(tallies.open()))
    records[0]['answer_counts']='{"1":100}'
    with tallies.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    report,_,_=evaluate(catalog,[tree],[tallies],sample)
    assert report[0]['status']=='FAIL'
    assert 'constant question' in report[0]['reasons']

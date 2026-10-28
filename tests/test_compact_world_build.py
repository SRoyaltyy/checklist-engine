import json
from pathlib import Path
import sys
import pytest
from ci.compact_world_build import limited_process,validate_shard,REQUEST


def test_hung_stock_is_killed_and_next_stock_can_complete(tmp_path):
    first=limited_process([sys.executable,'-c','import time;time.sleep(60)'],tmp_path/'hung',.1)
    second=limited_process([sys.executable,'-c','print("NEXT_STOCK_COMPLETED")'],tmp_path/'next',10)
    assert first['reason']=='STOCK_TIMEOUT' and first['returncode']!=0
    assert second['reason'] is None and 'NEXT_STOCK_COMPLETED' in second['log_tail']


def test_process_error_remains_an_explicit_exclusion(tmp_path):
    result=limited_process([sys.executable,'-c','raise ValueError("bad stock")'],tmp_path,10)
    assert result['reason']=='STOCK_PROCESS_ERROR' and 'bad stock' in result['log_tail']


@pytest.mark.parametrize('done,excluded',[(['a','a'],[]),(['a'],[]),(['a'],['a']),(['a'],['foreign'])])
def test_exclusion_ledger_cannot_hide_missing_duplicate_or_foreign_stock(done,excluded):
    part={'tickers':['a','b']}
    with pytest.raises(ValueError,match='membership'):
        validate_shard({'source_part':part,'completed':[{'ticker':t} for t in done],
                        'excluded':[{'ticker':t} for t in excluded]},part)


def test_good_and_excluded_stock_partition_the_source_exactly():
    part={'tickers':['a','b']}
    assert validate_shard({'source_part':part,'completed':[{'ticker':'a'}],
                           'excluded':[{'ticker':'b','reason':'STOCK_TIMEOUT'}]},part)==['a']


def test_production_limits_preserve_owner_cap_and_process_timeout():
    request=json.loads(REQUEST.read_text())
    assert request['max_parallel']<=20
    assert 0<request['stock_timeout_seconds']<request['shard_budget_seconds']<300*60
    assert request['answer_budget_bytes']+request['raw_source_budget_bytes']<request['hard_world_cap_bytes']==100000000000

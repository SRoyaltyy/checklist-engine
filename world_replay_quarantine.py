"""Owner-approved whole-name exclusion; never coerce unknown PIT eligibility."""
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
POLICY_PATH='dictionary/REPLAY_QUARANTINE_V1.json'
POLICY_SHA256='2046c1358d56a36c4bada671329e21d701d16b8497b3f7e5f707889e11e23bf5'
REASON='EXCLUDED_REPLAY_MISMATCH'


def load_policy(path=None,expected_sha256=POLICY_SHA256):
    file=Path(path) if path else ROOT/POLICY_PATH
    raw=file.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('owner quarantine policy digest differs')
    policy=json.loads(raw);records=policy['records'];names=[r['ticker'] for r in records]
    if (policy['format']!='OWNER_REPLAY_QUARANTINE_V1' or policy['authority_commit']!='91a593a'
        or len(names)!=len(set(names)) or len(names)!=policy['quarantined_names']
        or any(r['reason_code']!=REASON or not r['affected_predicates'] for r in records)
        or sum(r['mismatched_cells'] for r in records)!=166
        or sum(r['source_query_stock_days'] for r in records)!=policy['quarantined_stock_days']
        or policy['raw_source_names']-len(names)!=policy['v1_names']
        or policy['raw_source_stock_days']-policy['quarantined_stock_days']!=policy['v1_stock_days']):
        raise ValueError('owner quarantine accounting differs')
    return policy


@lru_cache(maxsize=1)
def excluded_names():
    return frozenset(r['ticker'] for r in load_policy()['records'])


def v1_eligible(ticker,pit_eligible):
    if not isinstance(ticker,str):raise TypeError('literal ticker required')
    if pit_eligible is not None and type(pit_eligible) is not bool:
        raise TypeError('PIT eligibility must be explicitly True,False or unknown')
    if ticker in excluded_names():return False
    return pit_eligible


def filter_parts(parts,policy):
    """Keep raw archive bindings; alter only the new selected-name work list."""
    names=[t for p in parts for t in p['tickers']];quarantined={r['ticker'] for r in policy['records']}
    if len(names)!=len(set(names)) or not quarantined<=set(names):
        raise ValueError('quarantine source universe differs')
    active=[]
    for source in parts:
        part=copy.deepcopy(source);part['tickers']=[t for t in source['tickers'] if t not in quarantined]
        if part['tickers']:active.append(part)
    selected=[t for p in active for t in p['tickers']]
    if set(selected)!=set(names)-quarantined or len(selected)!=len(names)-len(quarantined):
        raise ValueError('quarantine work partition differs')
    return active,copy.deepcopy(policy['records'])

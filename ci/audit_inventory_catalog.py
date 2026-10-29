"""Require every inventory ID in sources, mappings and all native coverage rows.

Catalog integrity only. PENDING remains PENDING; this never opens world_gate.
"""
import argparse
import csv
import json
from pathlib import Path


def read(file):
    with file.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def audit(root):
    items=read(root/'dictionary/WORLD_SNAPSHOT_DICTIONARY.csv')
    sources=read(root/'dictionary/DATA_SOURCES.csv')
    mappings=read(root/'dictionary/world_coverage_map.csv')
    coverage=read(root/'docs/WORLD_COVERAGE.csv')
    def unique(rows,key):
        keys=[r[key] for r in rows]
        if not all(keys) or len(keys)!=len(set(keys)):raise ValueError('empty or duplicated catalog identity: '+key)
        return set(keys)
    ids=unique(items,'id');source_ids=unique(sources,'id');mapping_ids=unique(mappings,'item_id')
    if ids-source_ids or ids-mapping_ids:raise ValueError('inventory missing from source/field catalog: '+str(sorted((ids-source_ids)|(ids-mapping_ids))))
    dictionary=[r for r in coverage if r['namespace']=='dictionary']
    keys=[(r['item_id'],r['timeframe']) for r in dictionary]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate dictionary coverage key')
    frames=[str(k)+'d' for k in range(1,22)]+['monthly']
    wanted={(ident,tf) for ident in ids for tf in frames}
    if wanted-set(keys):raise ValueError('inventory/timeframe omitted from WORLD_COVERAGE: '+str(sorted(wanted-set(keys))))
    registered={r['id'] for r in sources if r['fetch_test']=='REGISTERED_DERIVED_SOURCE_NOT_MEASURED'}
    unstated=[(r['item_id'],r['timeframe']) for r in dictionary
              if r['item_id'] in ids and r['status']=='PENDING' and not r['reason'].strip()]
    if any(ident in registered for ident,_ in unstated):raise ValueError('new derived registration lacks a PENDING reason')
    return dict(status='CATALOG_COMPLETE_NOT_WORLD_COVERAGE',inventory_items=len(ids),
                source_items=len(source_ids),mapping_items=len(mapping_ids),required_inventory_timeframe_rows=len(wanted),
                pending_inventory_timeframe_rows=sum(r['item_id'] in ids and r['status']=='PENDING' for r in dictionary),
                legacy_pending_rows_without_reason=len(unstated),
                full_world_gate='NOT_PROVEN',scoring_gate='CLOSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();print(json.dumps(audit(args.root),indent=2))

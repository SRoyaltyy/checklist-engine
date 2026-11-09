#!/usr/bin/env python3
'Audit matrix builder: deterministic, offline, authority-file only.'
import csv
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WSD_P = ROOT / 'dictionary/WORLD_SNAPSHOT_DICTIONARY.csv'
DS_P = ROOT / 'dictionary/DATA_SOURCES.csv'
LENS_P = ROOT / 'docs/LENSES_COVERAGE_V1.csv'
WC_P = ROOT / 'docs/WORLD_COVERAGE.csv'
OUT_CSV = HERE / 'DATA_REQUIREMENTS.csv'
OUT_MAN = HERE / 'SOURCE_MANIFEST.json'
COLS = ['inventory_id', 'item', 'required_or_excluded', 'authority_ref', 'source_urls', 'source_link_verification', 'required_fields', 'required_universe', 'required_period', 'timeframes', 'availability_or_publication_rule', 'identity_join_requirements', 'existing_assets', 'coverage_evidence', 'measured_scope', 'missing_scope', 'next_acquisition_or_build_step', 'owner_lane', 'status']
URL_RE = re.compile(r'https?://[A-Za-z0-9._~:/?#@!$&()*+,;=%-]+')


def load(path):
    with path.open(newline='', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def val(row, key):
    return (row.get(key) or '').strip()


def blob(path):
    try:
        return subprocess.check_output(['git', 'hash-object', str(path)], cwd=str(ROOT), text=True).strip()
    except Exception:
        return 'UNKNOWN'


def lane(group, block):
    text = (group + ' ' + block).lower()
    if 'chart shape' in text:
        return 'CHART-SHAPE/VIEWPORT lane'
    if 'expanded bar statistics' in text or 'indicator' in text:
        return 'INDICATOR lane'
    if 'bar' in text or 'price' in text or block.upper() == 'A':
        return 'PRICE/DATA lane'
    return 'UNASSIGNED - confirm with James'


def urls(text):
    found = set()
    for raw in URL_RE.findall(text):
        found.add(raw.rstrip('.,;)'))
    return sorted(found)


def main():
    wsd = load(WSD_P)
    ds = load(DS_P)
    lens = load(LENS_P)
    wc = load(WC_P)
    ds_by = {}
    for row in ds:
        ds_by.setdefault(val(row, 'id'), row)
    lens_by = {}
    for row in lens:
        lens_by.setdefault(val(row, 'id'), row)
    wc_by = {}
    for row in wc:
        wc_by.setdefault(val(row, 'item_id'), []).append(row)
    order = []
    for row in wsd + ds + lens:
        key = val(row, 'id')
        if key and key not in order:
            order.append(key)
    shas = {}
    for path in (WSD_P, DS_P, LENS_P, WC_P):
        shas[str(path.relative_to(ROOT))] = blob(path)
    out = []
    for key in order:
        w = next((r for r in wsd if val(r, 'id') == key), {})
        d = ds_by.get(key, {})
        l = lens_by.get(key, {})
        cands = wc_by.get(key, [])
        pick = [r for r in cands if val(r, 'namespace') == 'dictionary'] or cands
        pick.sort(key=lambda r: (0 if val(r, 'timeframe') == '1d' else 1, val(r, 'timeframe')))
        c = pick[0] if pick else {}
        group = val(w, 'group') or val(l, 'block')
        block = val(d, 'block') or val(l, 'block')
        item = val(w, 'item') or val(d, 'item') or val(l, 'item')
        cls = val(l, 'cls')
        excluded = cls in ('NO_QUESTIONS', 'NOT_APPLICABLE') or val(l, 'applicable') == 'NOT_APPLICABLE'
        src = val(d, 'source')
        derived = src.lower().startswith('derived')
        fields = val(w, 'inputs') or val(w, 'definition') or 'UNKNOWN'
        probe = (fields + ' ' + src + ' ' + val(w, 'definition')).lower()
        universe = 'UNKNOWN - full-universe coverage not proven in this audit'
        if 'peer' in probe:
            universe += '; named PIT peer set required'
        if 'benchmark' in probe:
            universe += '; named benchmark intervals required'
        period = val(d, 'pit_start') or 'UNKNOWN'
        if 'release' in val(d, 'in_repo'):
            period += ' ; engine file 2015-2024'
        tf = ' ; '.join(x for x in (val(w, 'window'), val(w, 'rolling_or_fixed')) if x) or 'UNKNOWN'
        if 'stack with all 22 native timeframes' in val(w, 'parameters'):
            tf += ' ; stack with all 22 native timeframes'
        evidence = 'no docs/WORLD_COVERAGE.csv row for this id'
        if c:
            evidence = 'docs/WORLD_COVERAGE.csv@' + shas['docs/WORLD_COVERAGE.csv'] + ' namespace=' + val(c, 'namespace') + ' timeframe=' + val(c, 'timeframe') + ' status=' + val(c, 'status')
        measured = 'UNMEASURED - no coverage row'
        if c:
            measured = 'non_null_pct_2020_2026=' + (val(c, 'non_null_pct_2020_2026') or 'blank') + '; universe_scope=' + (val(c, 'universe_scope') or 'blank') + '; timeframe=' + val(c, 'timeframe')
        missing = (val(c, 'reason') or 'no reason recorded') + '; lens_flags=' + (val(l, 'flags') or 'none')
        if excluded:
            step = 'Excluded control - no acquisition required'
        elif derived:
            step = 'Verify derivation against the parent-series measurement'
        else:
            step = 'Map produced columns to the required world columns, then measure'
        status = 'EXCLUDED_CONTROL'
        if not excluded:
            status = 'wc=' + (val(c, 'status') or 'NO_WC_ROW') + ';lens=' + (val(l, 'implementation_status') or 'UNKNOWN') + ';min6=' + (val(l, 'minimum_6_status') or 'UNKNOWN')
        out.append({'inventory_id': key, 'item': item, 'required_or_excluded': 'excluded_control' if excluded else 'required', 'authority_ref': 'dictionary/WORLD_SNAPSHOT_DICTIONARY.csv@' + shas['dictionary/WORLD_SNAPSHOT_DICTIONARY.csv'] + ':' + key + ';dictionary/DATA_SOURCES.csv@' + shas['dictionary/DATA_SOURCES.csv'] + ':' + key + ';docs/LENSES_COVERAGE_V1.csv@' + shas['docs/LENSES_COVERAGE_V1.csv'] + ':' + key, 'source_urls': ' ; '.join(urls(src)) or ('derived - no external download' if derived else 'UNKNOWN - no URL declared'), 'source_link_verification': 'declared_only: ' + (val(d, 'fetch_test') or 'no fetch test declared'), 'required_fields': fields, 'required_universe': universe, 'required_period': period, 'timeframes': tf, 'availability_or_publication_rule': val(w, 'pit_rule') or 'UNKNOWN - no availability rule declared', 'identity_join_requirements': 'derived from the parent series - no separate download' if derived else 'PIT ticker/CIK to entity; no current-map backfill', 'existing_assets': val(d, 'in_repo') or 'UNKNOWN', 'coverage_evidence': evidence, 'measured_scope': measured, 'missing_scope': missing, 'next_acquisition_or_build_step': step, 'owner_lane': lane(group, block), 'status': status})
    with OUT_CSV.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLS, lineterminator=chr(10))
        writer.writeheader()
        writer.writerows(out)
    manifest = {'generated_by': 'docs/venice-audit-v1/build_matrices.py', 'authority_blob_shas': shas, 'row_count': len(out), 'columns': COLS, 'ids_first': order[:3], 'ids_last': order[-3:]}
    OUT_MAN.write_text(json.dumps(manifest, indent=2) + chr(10), encoding='utf-8')
    print(json.dumps({'rows': len(out), 'excluded': sum(1 for r in out if r['required_or_excluded'] == 'excluded_control'), 'unique_ids': len(order)}))


def run_extras():
    import build_extra
    build_extra.main()


if __name__ == '__main__':
    main()
    run_extras()

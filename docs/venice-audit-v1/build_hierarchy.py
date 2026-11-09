#!/usr/bin/env python3
'v2 nested audit hierarchy: STAGES.csv and the 8-status REQUIREMENTS.csv. Offline and deterministic.'
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

# v2 status vocabulary.
NS, IP, PART, COMP, BLK, UNV, NA = ('NOT_STARTED', 'IN_PROGRESS', 'PARTIAL', 'COMPLETE', 'BLOCKED', 'UNVERIFIED', 'NOT_APPLICABLE')
STATES = {NS, IP, PART, COMP, BLK, UNV, NA}

STAGE_COLS = ['node_id', 'parent_id', 'node_type', 'title', 'status', 'substage_percent', 'percent_numerator', 'percent_denominator', 'percent_basis', 'blockers', 'next_action', 'evidence_refs', 'details_path']
REQ_COLS_V2 = [
    'requirement_id', 'parent_substage_id', 'subject_id',
    'scope_definition_status', 'data_acquisition_status', 'strict_data_definition_status',
    'implementation_status', 'question_design_status', 'answer_generation_status',
    'verification_status', 'main_acceptance_status', 'status_explanation',
    'authority_path', 'authority_anchor_or_lines', 'requirement', 'gantt_group', 'owner_lane',
    'dependencies', 'acceptance_condition', 'scope', 'evidence_refs', 'missing_work', 'remaining_action',
]

# stage_id -> title
STAGES = [
    ('S0', 'Stage 0: blockers and gates'),
    ('S1', 'Stage 1: data and world state'),
    ('S2', 'Stage 2: definitions'),
    ('S3', 'Stage 3: chart viewport'),
    ('S4', 'Stage 4: question framework'),
    ('S5', 'Stage 5: answer generation'),
    ('S5B', 'Stage 5b: v2 ladders and aliases'),
    ('S6', 'Stage 6: mining and exit rules'),
    ('S7', 'Stage 7: evaluation and reporting'),
    ('S8', 'Stage 8: shadow and live gates'),
]

# substage_id, parent stage, title, gantt_group, allowed owner_lanes (None = any), scope note
SUBSTAGES = [
    ('S0.1', 'S0', 'Legacy replay and quarantine closure', '0 Blockers', ['OPS'], 'Replay mismatch reconciliation'),
    ('S0.2', 'S0', 'Price sample, available_from and join identity contracts', '0 Blockers', ['PRICE/DATA'], 'Sample-scope and contract proofs'),
    ('S0.3', 'S0', 'Full world gate and PIT packet replay', '0 Blockers', ['WORLD-STATE'], 'Measured coverage gate for every canonical id'),
    ('S0.4', 'S0', 'SEC runner access', '0 Blockers', ['SEC'], 'Access proof distinguished from acquisition'),
    ('S1.1', 'S1', 'Price history and corporate actions', '1 Data', ['PRICE/DATA'], 'Daily OHLCV, dividends and splits'),
    ('S1.2', 'S1', 'World-state reference and event feeds', '1 Data', ['WORLD-STATE'], 'Macro vintages, earnings, estimates, short interest/volume, halts, membership, breadth, tradeability, context'),
    ('S1.3', 'S1', 'SEC filings panels', '1 Data', ['SEC'], 'Bulk submissions, Form 4, Form 13F'),
    ('S1.4', 'S1', 'Options chains and open interest', '1 Data', ['OPTIONS'], 'Full-history chains and OI'),
    ('S1.5', 'S1', 'Money flow and imbalance feeds', '1 Data', ['MONEYFLOW'], 'Signed money flow, block/dark-pool, ETF flows, Webull snapshots'),
    ('S1.6', 'S1', 'Pipeline documentation', '1 Data', ['OPS'], 'No-AI pipeline summary with real run results'),
    ('S2.1', 'S2', 'Lens design and strict indicator definitions', '2 Definitions', ['QUESTIONS'], '14-lens design, 114 strict definitions, measured per-id lens counts'),
    ('S3.1', 'S3', 'Chart viewport feature', '3 Viewport', ['VIEWPORT'], 'Viewport feature merged to main'),
    ('S4.1', 'S4', 'Complete question framework and batches', '4 Questions', ['QUESTIONS'], 'Registered questions bound to ids with parameters, timeframe and history lever'),
    ('S5.1', 'S5', 'Computed historical answers for the full question set', '5 Answers', ['ANSWERS'], 'Stored answers per bound question'),
    ('S5B.1', 'S5B', 'V2 ladder and alias semantic completion', '5b V2', ['QUESTIONS'], 'Ladders and aliases semantically complete'),
    ('S6.1', 'S6', 'Combination coverage and interaction orders', '6 Mining', ['MINING'], 'Searched interaction orders and remaining coverage'),
    ('S6.2', 'S6', 'Exit-rule registry applied per setup', '6 Mining', ['EXECUTION'], 'Every registered exit rule evaluated per setup'),
    ('S6.3', 'S6', 'Luck correction and same-day benchmark', '6 Mining', ['EVAL'], 'Benchmark and luck correction per result'),
    ('S7.1', 'S7', 'Per-setup and exit-tuple statistics', '7 Evaluation', ['EVAL'], 'Required statistics with sample size and significance'),
    ('S8.1', 'S8', 'Shadow and live gate status', '8 Shadow and live', ['OPS'], 'Shadow and live gates stay closed by design; the audit never opens them'),
]

# Which status dimensions apply to which stage family.
QUESTION_STAGES = {'S4', 'S5', 'S5B'}


def read_v1(path):
    with path.open(newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def match_substage(row):
    group = row.get('gantt_group', '')
    lane = row.get('owner_lane', '')
    for sid, parent, title, sgroup, lanes, note in SUBSTAGES:
        if group == sgroup and lane in lanes:
            return sid
    for sid, parent, title, sgroup, lanes, note in SUBSTAGES:
        if group == sgroup:
            return sid
    return None


def statuses(row, stage_id):
    v1 = row.get('current_status', 'NOT_PROVEN')
    asks = stage_id in QUESTION_STAGES
    if v1 == 'VERIFIED':
        base = dict(scope_definition_status=COMP, data_acquisition_status=COMP, strict_data_definition_status=COMP, implementation_status=COMP, verification_status=COMP, main_acceptance_status=COMP)
        expl = 'v1 evidence marks this requirement VERIFIED on main.'
    elif v1 == 'VERIFIED_PARTIAL':
        base = dict(scope_definition_status=COMP, data_acquisition_status=PART, strict_data_definition_status=PART, implementation_status=PART, verification_status=PART, main_acceptance_status=PART)
        expl = 'v1 evidence marks this requirement VERIFIED_PARTIAL: scope is defined but acquisition/verification/main acceptance are not complete.'
    elif v1 == 'VERIFIED_ACCESS_ONLY':
        base = dict(scope_definition_status=COMP, data_acquisition_status=PART, strict_data_definition_status=UNV, implementation_status=PART, verification_status=PART, main_acceptance_status=UNV)
        expl = 'v1 evidence proves access only, not acquisition or acceptance.'
    elif v1 == 'EXCLUDED_PENDING_RULING':
        base = dict(scope_definition_status=BLK, data_acquisition_status=BLK, strict_data_definition_status=BLK, implementation_status=BLK, verification_status=BLK, main_acceptance_status=BLK)
        expl = 'Excluded pending an owner ruling; no ruling is cited as accepted evidence.'
    else:
        base = dict(scope_definition_status=NS, data_acquisition_status=NS, strict_data_definition_status=NS, implementation_status=NS, verification_status=UNV, main_acceptance_status=UNV)
        expl = 'v1 evidence marks this NOT_PROVEN; no main artifact proves this requirement.'
    base['question_design_status'] = NS if asks else NA
    base['answer_generation_status'] = NS if asks else NA
    if not asks:
        base['status_explanation'] = expl + ' Question design and answer generation are not applicable to this requirement.'
    else:
        base['status_explanation'] = expl
    return base


def summarize_substage(rows, sid):
    n = len(rows)
    done = sum(1 for r in rows if r['main_acceptance_status'] == COMP)
    pct = 'UNKNOWN' if n == 0 else str(round(100.0 * done / n, 1))
    basis = 'numerator = child requirements with main_acceptance_status COMPLETE; denominator = child requirements in this substage; scope = this substage only'
    return str(done), str(n), pct, basis


def main():
    src = HERE / 'REQUIREMENTS.csv'
    rows = read_v1(src)
    by_sub = {sid: [] for sid, *_ in SUBSTAGES}
    out = []
    for row in rows:
        sid = match_substage(row)
        if sid is None:
            raise SystemExit('unmapped requirement %r (group %r lane %r)' % (row.get('requirement_id'), row.get('gantt_group'), row.get('owner_lane')))
        stage_id = sid.split('.')[0]
        st = statuses(row, stage_id)
        new = {
            'requirement_id': row.get('requirement_id', ''),
            'parent_substage_id': sid,
            'subject_id': row.get('requirement_id', ''),
            'authority_path': row.get('authority_path', ''),
            'authority_anchor_or_lines': row.get('authority_anchor_or_lines', ''),
            'requirement': row.get('requirement', ''),
            'gantt_group': row.get('gantt_group', ''),
            'owner_lane': row.get('owner_lane', ''),
            'dependencies': row.get('dependencies', ''),
            'acceptance_condition': row.get('acceptance_condition', ''),
            'scope': row.get('gantt_group', ''),
            'evidence_refs': row.get('evidence_refs', ''),
            'missing_work': row.get('remaining_action', ''),
            'remaining_action': row.get('remaining_action', ''),
        }
        new.update(st)
        out.append(new)
        by_sub[sid].append(new)

    with src.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=REQ_COLS_V2, lineterminator='\n')
        writer.writeheader()
        writer.writerows(out)

    stage_rows = []
    for node_id, title in STAGES:
        children = [r for s in SUBSTAGES if s[1] == node_id for r in by_sub[s[0]]]
        done = sum(1 for r in children if r['main_acceptance_status'] == COMP)
        total = len(children)
        if total and done == total:
            status = 'COMPLETE'
        elif done:
            status = 'IN_PROGRESS'
        else:
            status = 'UNVERIFIED'
        stage_rows.append({
            'node_id': node_id, 'parent_id': '', 'node_type': 'stage', 'title': title,
            'status': status, 'substage_percent': '', 'percent_numerator': '',
            'percent_denominator': '', 'percent_basis': 'blank by contract: percentages only on substage rows',
            'blockers': '', 'next_action': 'See substage rows and details pages',
            'evidence_refs': '', 'details_path': '',
        })
    for sid, parent, title, group, lanes, note in SUBSTAGES:
        num, den, pct, basis = summarize_substage(by_sub[sid], sid)
        children = by_sub[sid]
        blockers = '; '.join(r['requirement_id'] for r in children if r['main_acceptance_status'] == BLK)
        if int(den) and int(num) == int(den):
            status = 'COMPLETE'
        elif int(num):
            status = 'IN_PROGRESS'
        else:
            status = 'UNVERIFIED'
        stage_rows.append({
            'node_id': sid, 'parent_id': parent, 'node_type': 'substage', 'title': title,
            'status': status, 'substage_percent': pct, 'percent_numerator': num,
            'percent_denominator': den, 'percent_basis': basis, 'blockers': blockers,
            'next_action': note, 'evidence_refs': ';'.join(sorted({r['evidence_refs'] for r in children if r['evidence_refs']})),
            'details_path': 'details/%s.md' % sid,
        })
    with (HERE / 'STAGES.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=STAGE_COLS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(stage_rows)
    print({'requirements': len(out), 'stages': len(STAGES), 'substages': len(SUBSTAGES)})


if __name__ == '__main__':
    main()

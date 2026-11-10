#!/usr/bin/env python3
"""Generate the reporting layers from the generated matrices.

Writes details/<substage-id>.md for every substage, GANTT.md as the nested
stage > substage overview, and README.md as the entrypoint. Percentages are
copied verbatim from the STAGES.csv substage rows and never appear on stage
rows or on the overview aggregates. Charts are linked, not recomputed.
Offline, deterministic, no network.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGES = HERE / 'STAGES.csv'
REQS = HERE / 'REQUIREMENTS.csv'
INDEX = HERE / 'charts' / 'CHART_INDEX.csv'
DETAILS = HERE / 'details'
GANTT_MD = HERE / 'GANTT.md'
README = HERE / 'README.md'

DIMS = [
    ('scope_definition_status', 'Scope'),
    ('data_acquisition_status', 'Data'),
    ('strict_data_definition_status', 'Strict data'),
    ('implementation_status', 'Impl'),
    ('question_design_status', 'Design'),
    ('answer_generation_status', 'Answer'),
    ('verification_status', 'Verify'),
    ('main_acceptance_status', 'Main'),
]
DIM_NOTE = {
    'scope_definition_status': 'is the requirement written down precisely enough to act on',
    'data_acquisition_status': 'is the required data actually present in the repo or a linked source',
    'strict_data_definition_status': 'are universe, period and field contracts pinned',
    'implementation_status': 'does code that uses the data exist',
    'question_design_status': 'is a yes/no question with a literal predicate written',
    'answer_generation_status': 'has the question been evaluated over the data',
    'verification_status': 'has the answer been checked against evidence',
    'main_acceptance_status': 'is the result merged and accepted on main',
}


def load(path):
    with path.open(encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def sort_key(node_id):
    parts = []
    for chunk in str(node_id or '').replace('-', '.').split('.'):
        parts.append((0, int(chunk)) if chunk.isdigit() else (1, chunk))
    return parts


def cell(value, limit=None):
    text = ' '.join(str(value or '').split()).replace('|', '\\|')
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + '\u2026'
    return text or '\u2014'


def rel(from_dir, target):
    return target


def stage_index(stage_rows):
    out = {}
    for row in stage_rows:
        out[row['node_id']] = row
    return out


def write_detail(sub, children, charts):
    sid = sub['node_id']
    lines = []
    add = lines.append
    add('# %s \u2014 %s' % (sid, sub.get('title', '')))
    add('')
    add('Parent stage: **%s**. Substage status: **%s**.' % (sub.get('parent_id', ''), sub.get('status', '')))
    add('')
    pct = sub.get('substage_percent') or ''
    if pct:
        add('**Substage percent: %s%%** (%s of %s child requirements main-accepted).'
            % (pct, sub.get('percent_numerator') or '0', sub.get('percent_denominator') or '0'))
    else:
        add('**Substage percent: UNKNOWN** \u2014 no percentage is carried by this row.')
    add('')
    add('Percent basis: %s' % cell(sub.get('percent_basis'), 400))
    add('')
    add('Blockers: %s' % cell(sub.get('blockers'), 400))
    add('')
    add('Next action: %s' % cell(sub.get('next_action'), 400))
    add('')
    if charts.get(sid):
        chart_href = '../' + charts[sid]
        add('Visual Gantt for this substage, one lane per child requirement and one cell per lifecycle status: [%s](%s)' % (charts[sid], chart_href))
    else:
        add('No chart row was published for this substage.')
    add('')
    add('Percentages below are scoped to this substage only. Stage rows carry none, and no percentage is aggregated upward.')
    add('')
    add('## Child requirements (%d)' % len(children))
    add('')
    if not children:
        add('No child requirement rows are mapped to this substage.')
        add('')
    else:
        header = ['Requirement', 'Text', 'Lane'] + [label for _key, label in DIMS]
        header += ['Evidence', 'Missing work', 'Next action']
        add('| ' + ' | '.join(header) + ' |')
        add('|' + '|'.join(['---'] * len(header)) + '|')
        for row in sorted(children, key=lambda r: sort_key(r.get('requirement_id'))):
            cells = [cell(row.get('requirement_id')), cell(row.get('requirement'), 160), cell(row.get('owner_lane'))]
            for key, _label in DIMS:
                cells.append(cell(row.get(key)))
            cells += [cell(row.get('evidence_refs'), 200), cell(row.get('missing_work'), 200), cell(row.get('remaining_action'), 200)]
            add('| ' + ' | '.join(cells) + ' |')
        add('')
        add('### Status explanations')
        add('')
        for row in sorted(children, key=lambda r: sort_key(r.get('requirement_id'))):
            add('- **%s** \u2014 %s' % (row.get('requirement_id'), cell(row.get('status_explanation'), 400)))
        add('')
        add('### Authority')
        add('')
        for row in sorted(children, key=lambda r: sort_key(r.get('requirement_id'))):
            anchor = row.get('authority_anchor_or_lines') or ''
            add('- **%s** \u2014 `%s`%s' % (row.get('requirement_id'), row.get('authority_path'), (' lines %s' % anchor) if anchor else ''))
        add('')
        add('Acceptance conditions are recorded per requirement in REQUIREMENTS.csv; dependencies are listed there too.')
        add('')
    DETAILS.mkdir(parents=True, exist_ok=True)
    (DETAILS / ('%s.md' % sid)).write_text('\n'.join(lines), encoding='utf-8')


def write_gantt(stage_rows, by_parent, charts, totals):
    lines = []
    add = lines.append
    add('# Audit Gantt \u2014 stages, substages and granular items')
    add('')
    add('Nested overview of the audit hierarchy. Percentages appear **only** on substage rows and are scoped to that substage; large stages and the overall audit carry no computed percentage. Each substage links to its own visual Gantt and to its granular detail page.')
    add('')
    add('Totals: %d stages, %d substages, %d child requirements, %d main-accepted children.'
        % (totals['stages'], totals['substages'], totals['children'], totals['accepted']))
    add('')
    for stage in sorted((r for r in stage_rows if r.get('node_type') == 'stage'), key=lambda r: sort_key(r['node_id'])):
        add('## Stage %s \u2014 %s' % (stage['node_id'], stage.get('title', '')))
        add('')
        add('Stage status: **%s**. Substages: %d.' % (stage.get('status', ''), len(by_parent.get(stage['node_id'], []))))
        add('')
        subs = sorted(by_parent.get(stage['node_id'], []), key=lambda r: sort_key(r['node_id']))
        if not subs:
            add('No substage rows are mapped to this stage.')
            add('')
            continue
        add('| Substage | Title | Status | Percent (this substage only) | Children | Chart | Detail |')
        add('|---|---|---|---|---|---|---|')
        for sub in subs:
            sid = sub['node_id']
            pct = sub.get('substage_percent') or ''
            pct_cell = ('%s%% (%s/%s)' % (pct, sub.get('percent_numerator') or '0', sub.get('percent_denominator') or '0')) if pct else 'UNKNOWN'
            chart = ('[chart](charts/%s.svg)' % sid) if charts.get(sid) else '\u2014'
            add('| %s | %s | %s | %s | %d | %s | [detail](details/%s.md) |'
                % (sid, cell(sub.get('title'), 90), cell(sub.get('status')), pct_cell,
                   len(by_parent.get(sid, [])), chart, sid))
        add('')
    add('Percent basis used on every substage row: numerator = child requirements with main_acceptance_status COMPLETE; denominator = child requirements in that substage; scope = that substage only.')
    add('')
    GANTT_MD.write_text('\n'.join(lines), encoding='utf-8')


def write_readme(totals):
    lines = []
    add = lines.append
    add('# Repository requirements audit v2')
    add('')
    add('Evidence-only audit of every project stage, substage and granular requirement in this repository, including the yes/no questions the scanner needs and where each item stands in its lifecycle. It is a reporting layer: it changes no production pipeline, inventory, receipt or sealed record, and completing the audit opens no world, scoring or live gate.')
    add('')
    add('## Read in this order')
    add('')
    add('1. `GANTT.md` \u2014 nested overview: every large stage, its substages and their granular detail pages.')
    add('2. `details/<substage-id>.md` \u2014 one page per substage, listing every child requirement with its eight separate lifecycle statuses, authority path and remaining action.')
    add('3. `charts/<substage-id>.svg` \u2014 one actual visual Gantt per substage, one lane per child requirement and one cell per lifecycle status. Indexed in `charts/CHART_INDEX.csv`.')
    add('4. The matrices: `REQUIREMENTS.csv` (granular requirements and statuses), `DATA_REQUIREMENTS.csv` (fields, universe, periods, source links), `STAGES.csv` (stage and substage rows), `GANTT_COMPARISON.csv` (v16 and v20 chart claims against main evidence), `QUESTION_INDEX.csv` and `questions/` (the concrete yes/no questions), `EVIDENCE.json` (evidence ledger), `SOURCE_MANIFEST.json` (provenance).')
    add('')
    add('## Percentage scope')
    add('')
    add('A percentage exists only on an individual substage row. It is numerator = child requirements whose main_acceptance_status is COMPLETE over denominator = child requirements in that substage. Large stages, the whole audit and every granular item carry no computed percentage, and nothing is aggregated upward.')
    add('')
    add('## The eight status dimensions')
    add('')
    for key, label in DIMS:
        add('- **%s** (`%s`) \u2014 %s.' % (label, key, DIM_NOTE[key]))
    add('')
    add('A single item can be fully scoped and still unimplemented, or implemented and unverified; the dimensions are recorded separately on purpose so a green step cannot be read as completion.')
    add('')
    add('## Structure')
    add('')
    add('%d large stages > %d substages > %d granular requirements. %d requirements are main-accepted.' % (totals['stages'], totals['substages'], totals['children'], totals['accepted']))
    add('')
    add('## Provenance and regeneration')
    add('')
    add('Every artifact here is generated offline from authority files under `docs/`, `agent/tasks/` and the inventories, in this order: `build_extra.py`, `build_gantt.py`, `build_hierarchy.py`, `build_questions.py`, `build_charts.py`, `build_report.py`. The CI workflow `.github/workflows/venice-repo-requirements-audit.yml` runs the same order on the audit branch, runs the source-matched tests, and commits any drift. Hand-editing a generated file is therefore temporary.')
    add('')
    add('Statuses are read from evidence: a catalog row or a green job alone is not treated as completion. Where evidence was absent the status is UNVERIFIED and the gap is named in `missing_work`.')
    add('')
    add('## Limits')
    add('')
    add('This is a v2 revision of the published v1 audit and reuses its findings; it adds the requested hierarchy, the per-item status separation and the per-substage visuals. Percentages are descriptive of main-acceptance only, not an estimate of remaining effort.')
    add('')
    README.write_text('\n'.join(lines), encoding='utf-8')


def main():
    stage_rows = load(STAGES)
    req_rows = load(REQS)
    stages = [r for r in stage_rows if (r.get('node_type') or '') == 'stage']
    substages = [r for r in stage_rows if (r.get('node_type') or '') == 'substage']
    if not stages or not substages:
        raise SystemExit('STAGES.csv must carry both stage and substage rows')
    stage_by_id = stage_index(stages)
    subs_by_stage = {}
    for sub in substages:
        if sub.get('parent_id') not in stage_by_id:
            raise SystemExit('substage %s has unknown parent %s' % (sub['node_id'], sub.get('parent_id')))
        subs_by_stage.setdefault(sub['parent_id'], []).append(sub)
    known = {r['node_id'] for r in substages}
    by_parent = {}
    for row in req_rows:
        parent = row.get('parent_substage_id', '')
        if parent not in known:
            raise SystemExit('requirement %s has unknown parent substage %s' % (row.get('requirement_id'), parent))
        by_parent.setdefault(parent, []).append(row)
    charts = {}
    if INDEX.is_file():
        for row in load(INDEX):
            if row.get('svg_path'):
                charts[row['substage_id']] = row['svg_path']
    totals = {
        'stages': len(stages),
        'substages': len(substages),
        'children': len(req_rows),
        'accepted': sum(1 for r in req_rows if (r.get('main_acceptance_status') or '').upper() == 'COMPLETE'),
    }
    DETAILS.mkdir(parents=True, exist_ok=True)
    for sub in substages:
        write_detail(sub, by_parent.get(sub['node_id'], []), charts)
    write_gantt(stage_rows, {**subs_by_stage, **by_parent}, charts, totals)
    write_readme(totals)
    print(json.dumps({'details': len(substages), 'charts_linked': len(charts), 'children': totals['children']}))


if __name__ == '__main__':
    main()

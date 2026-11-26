#!/usr/bin/env python3
"""Offline validator for the docs/venice-audit-v1 reporting layers.

Checks that the published audit actually carries, for every substage row in
STAGES.csv, all three reporting layers the assignment requires: one chart index
row, one real SVG Gantt showing every child requirement and every lifecycle
status dimension, and one granular detail page listing those same children.
Percentages are only ever compared, never recomputed: whatever STAGES.csv says
must appear unchanged in CHART_INDEX.csv.

Deterministic, no network. Exit code 0 means no issues; 1 prints the issues.
"""
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DIMS = [
    ('scope_definition_status', 'Scope defined'),
    ('data_acquisition_status', 'Data acquired'),
    ('strict_data_definition_status', 'Strict data defined'),
    ('implementation_status', 'Implemented'),
    ('question_design_status', 'Question designed'),
    ('answer_generation_status', 'Answer generated'),
    ('verification_status', 'Verified'),
    ('main_acceptance_status', 'Main accepted'),
]
STATUS_VALUES = {
    'COMPLETE', 'PARTIAL', 'IN_PROGRESS', 'BLOCKED', 'NOT_STARTED',
    'UNVERIFIED', 'NOT_APPLICABLE',
}
INDEX_COLS = [
    'chart_id', 'substage_id', 'parent_stage_id', 'substage_title', 'substage_status',
    'substage_percent', 'percent_numerator', 'percent_denominator', 'percent_basis',
    'child_count', 'svg_path', 'details_path', 'chart_kind',
]


def load_csv(path):
    with path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def collect_issues(root):
    """Return a list of human-readable problems found under `root`."""
    root = Path(root)
    issues = []
    stages_path = root / 'STAGES.csv'
    reqs_path = root / 'REQUIREMENTS.csv'
    index_path = root / 'charts' / 'CHART_INDEX.csv'
    gantt_path = root / 'GANTT.md'
    readme_path = root / 'README.md'
    for path in (stages_path, reqs_path, index_path, gantt_path, readme_path):
        if not path.is_file():
            issues.append('missing required file: %s' % path.relative_to(root))
    if issues:
        return issues

    _, stage_rows = load_csv(stages_path)
    _, req_rows = load_csv(reqs_path)
    index_fields, index_rows = load_csv(index_path)
    if index_fields != INDEX_COLS:
        issues.append('CHART_INDEX.csv header differs: %s' % index_fields)

    substages = [r for r in stage_rows if (r.get('node_type') or '') == 'substage']
    if not substages:
        issues.append('STAGES.csv carries no substage rows')
    substage_ids = {r['node_id'] for r in substages}
    stage_ids = {r['node_id'] for r in stage_rows if (r.get('node_type') or '') == 'stage'}

    children = {}
    for row in req_rows:
        children.setdefault((row.get('parent_substage_id') or '').strip(), []).append(row)
    for parent in children:
        if parent and parent not in substage_ids:
            issues.append('requirement parent substage %s is not in STAGES.csv' % parent)

    by_substage = {}
    for row in index_rows:
        sid = (row.get('substage_id') or '').strip()
        if sid in by_substage:
            issues.append('duplicate CHART_INDEX row for substage %s' % sid)
        by_substage[sid] = row
        if sid and sid not in substage_ids:
            issues.append('CHART_INDEX row for unknown substage %s' % sid)

    gantt_text = gantt_path.read_text(encoding='utf-8')
    readme_text = readme_path.read_text(encoding='utf-8')
    details_dir = root / 'details'

    for sub in sorted(substages, key=lambda r: r['node_id']):
        sid = sub['node_id']
        kids = children.get(sid, [])
        if not kids:
            issues.append('substage %s has no child requirements' % sid)
        parent = sub.get('parent_id') or ''
        if parent not in stage_ids:
            issues.append('substage %s parent %s is not a stage row' % (sid, parent))

        row = by_substage.get(sid)
        if row is None:
            issues.append('substage %s has no CHART_INDEX row' % sid)
            continue

        for key, stage_key in (('substage_percent', 'substage_percent'),
                               ('percent_numerator', 'percent_numerator'),
                               ('percent_denominator', 'percent_denominator'),
                               ('percent_basis', 'percent_basis'),
                               ('substage_status', 'status'),
                               ('substage_title', 'title')):
            if (row.get(key) or '').strip() != (sub.get(stage_key) or '').strip():
                issues.append('%s mismatch on %s for %s' % (key, row.get(key), sid))
        if (row.get('parent_stage_id') or '').strip() != parent:
            issues.append('parent_stage_id mismatch for %s' % sid)
        if (row.get('chart_id') or '').strip() != 'CH-%s' % sid:
            issues.append('chart_id is not CH-%s: %s' % (sid, row.get('chart_id')))
        if (row.get('substage_status') or '').strip() not in STATUS_VALUES:
            issues.append('chart row status off vocabulary for %s' % sid)
        try:
            declared = int((row.get('child_count') or '').strip())
        except ValueError:
            issues.append('child_count not an integer for %s' % sid)
            declared = None
        if declared is not None and declared != len(kids):
            issues.append('child_count %d != %d child rows for %s'
                          % (declared, len(kids), sid))

        svg_rel = (row.get('svg_path') or '').strip()
        svg_path = root / svg_rel
        if not svg_rel or not svg_path.is_file():
            issues.append('missing chart SVG for %s: %s' % (sid, svg_rel))
            continue
        try:
            svg_root = ET.parse(svg_path).getroot()
        except ET.ParseError as exc:
            issues.append('chart SVG is not well-formed for %s: %s' % (sid, exc))
            continue
        svg_text = svg_path.read_text(encoding='utf-8')
        if svg_root.tag.split('}')[-1] != 'svg':
            issues.append('chart root element is not svg for %s' % sid)
        for _key, label in DIMS:
            if label not in svg_text:
                issues.append('chart %s is missing the "%s" status column' % (sid, label))
        for kid in kids:
            rid = (kid.get('requirement_id') or '').strip()
            if rid and rid not in svg_text:
                issues.append('chart %s has no lane for %s' % (sid, rid))
            for key, _label in DIMS:
                status = (kid.get(key) or '').strip()
                if status not in STATUS_VALUES:
                    issues.append('%s %s off status vocabulary: %s' % (rid, key, status))

        det_rel = (row.get('details_path') or '').strip()
        det_path = root / det_rel
        if not det_rel or not det_path.is_file():
            issues.append('missing detail page for %s: %s' % (sid, det_rel))
        else:
            det_text = det_path.read_text(encoding='utf-8')
            if 'Parent stage' not in det_text:
                issues.append('detail page %s does not name its parent stage' % sid)
            if parent not in det_text:
                issues.append('detail page %s omits parent stage %s' % (sid, parent))
            for kid in kids:
                rid = (kid.get('requirement_id') or '').strip()
                if rid and rid not in det_text:
                    issues.append('detail page %s omits child %s' % (sid, rid))

        if det_rel and det_rel not in gantt_text:
            issues.append('GANTT.md does not link detail page %s' % det_rel)
        if svg_rel and svg_rel not in gantt_text:
            issues.append('GANTT.md does not link chart %s' % svg_rel)

    if details_dir.is_dir():
        for page in sorted(details_dir.glob('*.md')):
            if page.stem not in substage_ids:
                issues.append('orphan detail page: %s' % page.name)

    for needle in ('GANTT.md', 'details/', 'charts/', 'substage'):
        if needle not in readme_text:
            issues.append('README.md does not mention %s' % needle)
    return issues


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(argv[0]) if argv else Path(__file__).resolve().parents[1] / 'docs' / 'venice-audit-v1'
    issues = collect_issues(root)
    print(json.dumps({'root': str(root), 'issues': len(issues), 'details': issues[:40]}, indent=2))
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())

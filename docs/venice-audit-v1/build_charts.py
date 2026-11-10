#!/usr/bin/env python3
"""Render one SVG Gantt per substage from STAGES.csv and REQUIREMENTS.csv.

Every substage row in STAGES.csv gets its own chart; every child requirement of
that substage gets its own lane, and the lane is divided into one cell per
lifecycle status dimension. A percentage is never recomputed here: the value and
its basis are copied verbatim from STAGES.csv, and UNKNOWN is printed when the
substage row carries none. Offline, deterministic, no network.
"""
import csv
import json
import xml.sax.saxutils as sx
from pathlib import Path

HERE = Path(__file__).resolve().parent
STAGES = HERE / 'STAGES.csv'
REQS = HERE / 'REQUIREMENTS.csv'
OUTDIR = HERE / 'charts'
INDEX = OUTDIR / 'CHART_INDEX.csv'

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
FILL = {
    'COMPLETE': '#1a7f37',
    'PARTIAL': '#bf8700',
    'IN_PROGRESS': '#0969da',
    'BLOCKED': '#cf222e',
    'NOT_STARTED': '#afb8c1',
    'UNVERIFIED': '#8250df',
    'NOT_APPLICABLE': '#eaeef2',
}
SHORT = {
    'COMPLETE': 'C', 'PARTIAL': 'P', 'IN_PROGRESS': 'IP', 'BLOCKED': 'B',
    'NOT_STARTED': 'NS', 'UNVERIFIED': 'U', 'NOT_APPLICABLE': 'NA',
}

LABEL_W = 430
COL_W = 78
ROW_H = 24
HEAD_H = 168
WIDTH = LABEL_W + COL_W * len(DIMS)
INDEX_COLS = [
    'chart_id', 'substage_id', 'parent_stage_id', 'substage_title', 'substage_status',
    'substage_percent', 'percent_numerator', 'percent_denominator', 'percent_basis',
    'child_count', 'svg_path', 'details_path', 'chart_kind',
]


def esc(value):
    return sx.escape(str(value or ''), {'"': '&quot;'})


def clip(text, limit):
    text = ' '.join(str(text or '').split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + '\u2026'


def sort_key(requirement_id):
    parts = []
    for chunk in str(requirement_id or '').replace('-', '.').split('.'):
        parts.append((0, int(chunk)) if chunk.isdigit() else (1, chunk))
    return parts


def cell_colour(status):
    return FILL.get(str(status or '').upper(), '#eaeef2')


def legend(out, x, y):
    out.append('<g font-family="sans-serif" font-size="10">')
    out.append('<text x="%d" y="%d" fill="#57606a">Cell legend:</text>' % (x, y))
    cx = x + 78
    for state in ['COMPLETE', 'PARTIAL', 'IN_PROGRESS', 'BLOCKED', 'NOT_STARTED', 'UNVERIFIED', 'NOT_APPLICABLE']:
        out.append('<rect x="%d" y="%d" width="14" height="10" fill="%s" stroke="#8c959f" stroke-width="0.5"/>' % (cx, y - 9, cell_colour(state)))
        out.append('<text x="%d" y="%d" fill="#24292f">%s</text>' % (cx + 18, y, esc(SHORT[state])))
        cx += 18 + 8 * len(SHORT[state]) + 16
    out.append('</g>')


def render(sub, children):
    sid = sub['node_id']
    rows = max(len(children), 1)
    height = HEAD_H + rows * ROW_H + 84
    out = []
    add = out.append
    add('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
        % (WIDTH, height, WIDTH, height, esc('Gantt for substage %s' % sid)))
    add('<rect width="%d" height="%d" fill="#ffffff"/>' % (WIDTH, height))
    add('<text x="16" y="28" font-family="sans-serif" font-size="17" font-weight="700" fill="#1b1f23">%s \u2014 %s</text>'
        % (esc(sid), esc(sub.get('title'))))
    add('<text x="16" y="48" font-family="sans-serif" font-size="11.5" fill="#57606a">Parent stage %s \u00b7 substage status %s \u00b7 %s of %s child requirements main-accepted</text>'
        % (esc(sub.get('parent_id')), esc(sub.get('status')),
           esc(sub.get('percent_numerator') or '0'), esc(sub.get('percent_denominator') or '0')))
    pct = sub.get('substage_percent') or 'UNKNOWN'
    add('<text x="16" y="70" font-family="sans-serif" font-size="13" font-weight="700" fill="#1b1f23">Substage percent: %s</text>'
        % esc(pct if pct not in ('', None) else 'UNKNOWN'))
    if pct not in ('', None, 'UNKNOWN'):
        try:
            frac = max(0.0, min(100.0, float(pct)))
            add('<rect x="16" y="78" width="300" height="8" fill="#eaeef2" stroke="#d0d7de" stroke-width="0.5"/>')
            add('<rect x="16" y="78" width="%.1f" height="8" fill="#1a7f37"/>' % (300.0 * frac / 100.0))
        except ValueError:
            pass
    add('<text x="16" y="104" font-family="sans-serif" font-size="10.5" fill="#57606a">Percent basis: %s</text>'
        % esc(clip(sub.get('percent_basis'), 118)))
    add('<text x="16" y="120" font-family="sans-serif" font-size="10.5" fill="#57606a">Scope note / next action: %s</text>'
        % esc(clip(sub.get('next_action'), 118)))
    add('<text x="16" y="136" font-family="sans-serif" font-size="10.5" fill="#57606a">Blocked children: %s</text>'
        % esc(clip(sub.get('blockers'), 118) or 'none'))

    head_y = HEAD_H - 14
    add('<text x="12" y="%d" font-family="sans-serif" font-size="10" font-weight="700" fill="#24292f">Requirement</text>' % head_y)
    for i, (_key, label) in enumerate(DIMS):
        x = LABEL_W + i * COL_W
        add('<text x="%d" y="%d" font-family="sans-serif" font-size="9" fill="#24292f">%s</text>'
            % (x + 4, head_y - 10, esc(label)))
        add('<text x="%d" y="%d" font-family="sans-serif" font-size="8" fill="#57606a">%s</text>'
            % (x + 4, head_y + 1, esc(_key.replace('_status', ''))))
    add('<line x1="8" y1="%d" x2="%d" y2="%d" stroke="#d0d7de"/>' % (HEAD_H - 2, WIDTH - 8, HEAD_H - 2))

    if not children:
        add('<text x="16" y="%d" font-family="sans-serif" font-size="11.5" fill="#cf222e">No child requirement rows are mapped to this substage.</text>' % (HEAD_H + 20))

    for i, row in enumerate(sorted(children, key=lambda r: sort_key(r.get('requirement_id')))):
        y = HEAD_H + i * ROW_H
        if i % 2 == 0:
            add('<rect x="8" y="%d" width="%d" height="%d" fill="#f6f8fa"/>' % (y, WIDTH - 16, ROW_H))
        add('<text x="12" y="%d" font-family="sans-serif" font-size="10.5" font-weight="700" fill="#1b1f23">%s</text>'
            % (y + 15, esc(row.get('requirement_id'))))
        add('<text x="78" y="%d" font-family="sans-serif" font-size="10" fill="#24292f">%s</text>'
            % (y + 15, esc(clip(row.get('requirement'), 52))))
        for j, (key, label) in enumerate(DIMS):
            state = str(row.get(key) or 'UNVERIFIED').upper()
            x = LABEL_W + j * COL_W
            add('<rect x="%d" y="%d" width="%d" height="16" fill="%s" stroke="#8c959f" stroke-width="0.5">'
                '<title>%s \u00b7 %s: %s</title></rect>'
                % (x + 2, y + 4, COL_W - 6, cell_colour(state), esc(row.get('requirement_id')), esc(label), esc(state)))
            if state != 'NOT_APPLICABLE':
                add('<text x="%d" y="%d" font-family="sans-serif" font-size="9" fill="#ffffff" text-anchor="middle">%s</text>'
                    % (x + (COL_W - 6) / 2.0 + 2, y + 15, esc(SHORT.get(state, '?'))))
        add('<text x="%d" y="%d" font-family="sans-serif" font-size="8.5" fill="#57606a">%s</text>'
            % (WIDTH - 176, y + 15, esc(clip(row.get('owner_lane'), 22))))

    legend(out, 16, height - 46)
    add('<text x="16" y="%d" font-family="sans-serif" font-size="9.5" fill="#57606a">Generated by docs/venice-audit-v1/build_charts.py from STAGES.csv and REQUIREMENTS.csv. '
        'Percentages are copied from STAGES.csv and are scoped to this substage only; stage rows carry none.</text>' % (height - 24))
    add('</svg>')
    return '\n'.join(out) + '\n'


def main():
    with STAGES.open(encoding='utf-8', newline='') as fh:
        stage_rows = list(csv.DictReader(fh))
    with REQS.open(encoding='utf-8', newline='') as fh:
        req_rows = list(csv.DictReader(fh))
    substages = [r for r in stage_rows if (r.get('node_type') or '') == 'substage']
    if not substages:
        raise SystemExit('STAGES.csv has no substage rows')
    by_parent = {}
    for row in req_rows:
        by_parent.setdefault(row.get('parent_substage_id', ''), []).append(row)
    known = {r['node_id'] for r in substages}
    stray = sorted({p for p in by_parent if p not in known and p != ''})
    if stray:
        raise SystemExit('requirements point at unknown substages: %s' % ', '.join(stray))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    index = []
    total_children = 0
    for sub in substages:
        sid = sub['node_id']
        children = by_parent.get(sid, [])
        total_children += len(children)
        path = OUTDIR / ('%s.svg' % sid)
        path.write_text(render(sub, children), encoding='utf-8')
        index.append({
            'chart_id': 'CH-%s' % sid,
            'substage_id': sid,
            'parent_stage_id': sub.get('parent_id', ''),
            'substage_title': sub.get('substage_title', ''),
            'substage_status': sub.get('substage_status', ''),
            'substage_percent': sub.get('substage_percent', ''),
            'percent_numerator': sub.get('percent_numerator', ''),
            'percent_denominator': sub.get('percent_denominator', ''),
            'percent_basis': sub.get('percent_basis', ''),
            'child_count': str(len(children)),
            'svg_path': 'charts/%s.svg' % sid,
            'details_path': sub.get('details_path', '') or 'details/%s.md' % sid,
            'chart_kind': 'per-substage lifecycle gantt, one lane per child requirement',
        })
    with INDEX.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=INDEX_COLS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(index)
    print(json.dumps({'substages': len(substages), 'children': total_children, 'charts': len(index)}))


if __name__ == '__main__':
    main()

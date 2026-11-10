#!/usr/bin/env python3
'''Granular question index. Authority tables only, offline and deterministic.

Every row is a real, answerable question with a stable id, the substage that owns
its phase, an unambiguous template plus the authority parameter/timeframe domain
and the separate design/implementation/answer/verification states. Nothing is
marked complete that no main artifact proves.
'''
import csv
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WSD_P = ROOT / 'dictionary/WORLD_SNAPSHOT_DICTIONARY.csv'
LENS_P = ROOT / 'docs/LENSES_COVERAGE_V1.csv'
OUT = HERE / 'QUESTION_INDEX.csv'
MAN_DIR = HERE / 'questions'
MAN = MAN_DIR / 'INDEX.json'

# Phase substages that exist in build_hierarchy.SUBSTAGES.
DESIGN_SID = 'S4.1'
ANSWER_SID = 'S5.1'
ALIAS_SID = 'S5B.1'
PHASES = (
    ('design', DESIGN_SID),
    ('implementation', ANSWER_SID),
    ('answer', ANSWER_SID),
    ('verification', ANSWER_SID),
    ('alias', ALIAS_SID),
)

COLS = [
    'question_id', 'phase', 'parent_substage_id', 'subject_id', 'inventory_id', 'item',
    'lens', 'timeframe_domain', 'parameter_domain', 'literal_predicate', 'template',
    'source_artifact', 'source_anchor', 'design_status', 'implementation_status',
    'answer_status', 'verification_status', 'evidence_refs', 'missing_work',
    'next_action', 'unresolved_reason',
]

NS, PART, COMP, UNV, NA = ('NOT_STARTED', 'PARTIAL', 'COMPLETE', 'UNVERIFIED', 'NOT_APPLICABLE')
EXCLUDED_CLS = {'NO_QUESTIONS', 'NOT_APPLICABLE'}

TEMPLATES = {
    'absolute': 'At day D, using only data up to the D-1 close, is {q} strictly greater than the absolute level a for a in {p}?',
    'relative': 'At day D, using only data up to the D-1 close, is the relative change ({q} - {q}[t-N]) / abs({q}[t-N]) greater than r for N in {p}?',
    'position': 'At day D, using only data up to the D-1 close, is {q} in the upper position p of window W ({w}) computed as ({q} - min(W)) / (max(W) - min(W)) >= p?',
    'threshold': 'At day D, using only data up to the D-1 close, does {q} cross above the fixed level L for L in {p}?',
    'divergence': 'At day D, using only data up to the D-1 close, does {q} diverge from its registered reference series y so that sign(delta {q}) differs from sign(delta y)?',
    'outlier': 'At day D, using only data up to the D-1 close, is abs({q} - mean(W)) greater than z * stdev(W) over window W ({w}) for z in {p}?',
    'path': 'At day D, using only data up to the D-1 close, does the path of {q} over window W ({w}) satisfy the registered monotonic/ordering path condition?',
    'streak': 'At day D, using only data up to the D-1 close, is the current same-sign run length of {q} at least s for s in {p}?',
    'cross': 'At day D, using only data up to the D-1 close, does {q} cross its registered reference series y, i.e. {q}[t-1] < y[t-1] and {q}[t] >= y[t]?',
    'change_since_last': 'At day D, using only data up to the D-1 close, has {q} changed since the last observed bar in direction d for d in {p}?',
    'rank': 'At day D, using only data up to the D-1 close, is the point-in-time peer rank of {q} at or above k for k in {p}, with a named PIT peer set?',
    'percentile': 'At day D, using only data up to the D-1 close, is the percentile of {q} within its own history at or below p for p in {p}?',
    'extreme_vs_own_history': 'At day D, using only data up to the D-1 close, is {q} equal to its own maximum or minimum over lookback H for H in {p}?',
    'timeframe': 'At day D, using only data up to the D-1 close, do at least m registered timeframes agree on the direction of {q} for m in {p}?',
}


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


def slug(text):
    return re.sub(r'[^A-Z0-9]+', '-', text.upper()).strip('-')


def domain(row):
    '''Parameter domain taken verbatim from the authority row, plus the basis.'''
    raw = val(row, 'parameters')
    found = []
    for token in re.split(r';', raw):
        token = token.strip()
        if '=' in token:
            found.append(token)
    if found:
        return ' ; '.join(found), 'dictionary parameters column'
    if raw:
        return raw, 'dictionary parameters column (unnamed)'
    return 'UNKNOWN', 'no parameter domain declared in the authority row'


def timeframes(row):
    window = val(row, 'window')
    params = val(row, 'parameters')
    tokens = [t.strip() for t in re.split(r'[;]', params) if 'monthly' in t or re.search(r'\bd\b', t)]
    parts = [p for p in (window, ' ; '.join(tokens)) if p]
    if parts:
        return ' ; '.join(parts)
    return 'UNKNOWN'


def states(lens_row, excluded):
    if excluded:
        return dict(design_status=NA, implementation_status=NA, answer_status=NA, verification_status=NA)
    impl = val(lens_row, 'implementation_status').upper()
    min6 = val(lens_row, 'minimum_6_status').upper()
    scope = val(lens_row, 'coverage_scope').upper()
    design = NS
    implementation = NS
    if impl in ('IMPLEMENTED', 'MEASURED') or 'MEASURED' in scope:
        design = COMP
        implementation = PART
    elif impl == 'UNMEASURED' or scope == 'CLASS_APPLICABILITY_ONLY':
        design = NS
        implementation = UNV
    verification = UNV
    if min6 and min6 != 'NOT_PROVEN':
        verification = PART
    return dict(design_status=design, implementation_status=implementation,
                answer_status=NS, verification_status=verification)


def main():
    wsd = load(WSD_P)
    lens = load(LENS_P)
    shas = {str(WSD_P.relative_to(ROOT)): blob(WSD_P), str(LENS_P.relative_to(ROOT)): blob(LENS_P)}
    wsd_by = {}
    for row in wsd:
        wsd_by.setdefault(val(row, 'id'), row)
    lens_by = {}
    for row in lens:
        lens_by.setdefault(val(row, 'id'), row)
    order = []
    for row in wsd + lens:
        key = val(row, 'id')
        if key and key not in order:
            order.append(key)
    rows = []
    omissions = []
    counts = {'ids': len(order), 'questions': 0, 'excluded_controls': 0, 'rows': 0}
    for key in order:
        l = lens_by.get(key, {})
        w = wsd_by.get(key, {})
        cls = val(l, 'cls').upper()
        applicable = val(l, 'applicable')
        item = val(w, 'item') or val(l, 'item') or 'UNKNOWN'
        excluded = cls in EXCLUDED_CLS or applicable.upper() == 'NOT_APPLICABLE'
        pdom, pbasis = domain(w)
        tdom = timeframes(w)
        source_artifact = 'docs/LENSES_COVERAGE_V1.csv@' + shas['docs/LENSES_COVERAGE_V1.csv'] + ':' + key
        anchor = 'dictionary/WORLD_SNAPSHOT_DICTIONARY.csv@' + shas['dictionary/WORLD_SNAPSHOT_DICTIONARY.csv'] + ':' + key
        if excluded:
            counts['excluded_controls'] += 1
            reason = 'class ' + (cls or 'UNKNOWN') + ' is an explicit excluded control; no answerable question'
            omissions.append({'inventory_id': key, 'lens': None, 'reason': reason})
            base = dict(question_id='Q-' + slug(key) + '-CONTROL', subject_id=key, inventory_id=key, item=item,
                        lens='(excluded control)', timeframe_domain=tdom, parameter_domain=pdom,
                        literal_predicate='Excluded control: no question, kept for coverage accounting.',
                        template='', source_artifact=source_artifact, source_anchor=anchor,
                        evidence_refs=source_artifact, missing_work='none - excluded control',
                        next_action='Keep in the coverage index only', unresolved_reason=reason)
            for phase, sid in (('design', DESIGN_SID),):
                row = dict(base)
                row.update(states(l, True))
                row['phase'] = phase
                row['parent_substage_id'] = sid
                rows.append(row)
                counts['rows'] += 1
            continue
        lenses = [x for x in applicable.split('|') if x]
        potential = int(val(l, 'potential_lens_count') or 0)
        if potential and len(lenses) < potential:
            omissions.append({'inventory_id': key, 'lens': None,
                              'reason': 'authority lists %d potential lenses but only %d are applicable: %s' % (potential, len(lenses), '|'.join(lenses))})
        if not lenses:
            omissions.append({'inventory_id': key, 'lens': None, 'reason': 'no applicable lens declared'})
            continue
        alias = val(l, 'candidate_alias')
        flags = val(l, 'flags')
        for ln in lenses:
            tmpl = TEMPLATES.get(ln)
            if tmpl is None:
                omissions.append({'inventory_id': key, 'lens': ln, 'reason': 'unregistered lens name'})
                continue
            qid = 'Q-' + slug(key) + '-' + slug(ln)
            counts['questions'] += 1
            reason = ' ; '.join(x for x in (flags, ('alias candidate: ' + alias) if alias else '') if x)
            pred = tmpl.format(q=item, p=pdom, w=tdom)
            base = dict(question_id=qid, subject_id=key, inventory_id=key, item=item, lens=ln,
                        timeframe_domain=tdom, parameter_domain=pdom, literal_predicate=pred, template=tmpl,
                        source_artifact=source_artifact, source_anchor=anchor, evidence_refs=source_artifact,
                        missing_work='strict definition, implementation and stored answer not proven on main' if val(l, 'implementation_status').upper() != 'MEASURED' else 'main acceptance not proven',
                        next_action='Bind the literal predicate to the canonical columns, then compute the historical answer',
                        unresolved_reason=reason)
            plan = PHASES if alias else tuple(p for p in PHASES if p[0] != 'alias')
            for phase, sid in plan:
                row = dict(base)
                row.update(states(l, False))
                row['phase'] = phase
                row['parent_substage_id'] = sid
                if phase == 'alias':
                    row['unresolved_reason'] = (reason + ' ; alias semantics unresolved').strip(' ;')
                rows.append(row)
                counts['rows'] += 1
    with OUT.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    MAN_DIR.mkdir(exist_ok=True)
    manifest = {
        'generated_by': 'docs/venice-audit-v1/build_questions.py',
        'authority_blob_shas': shas,
        'phase_substages': {'design': DESIGN_SID, 'implementation': ANSWER_SID, 'answer': ANSWER_SID, 'verification': ANSWER_SID, 'alias': ALIAS_SID},
        'counts': counts,
        'columns': COLS,
        'omissions': omissions,
        'rule': 'one row per (question, phase); parameter and timeframe domains stay explicit rather than hidden; UNKNOWN stays UNKNOWN',
    }
    MAN.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ids': counts['ids'], 'questions': counts['questions'], 'rows': counts['rows'], 'omissions': len(omissions)}))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Checklist QA. Usage: python3 qa/check.py [--root DIR] [--final] [--fuzzy]"""
import argparse, csv, glob, os, re, collections
try:
    from rapidfuzz import fuzz
    def sim(a, b): return fuzz.ratio(a, b)
except ImportError:
    import difflib
    def sim(a, b): return difflib.SequenceMatcher(None, a, b).ratio() * 100

ALIASES = {
    'id': ['id', 'row_id', 'check_id'],
    'variant': ['variant', 'name', 'item', 'field'],
    'lens': ['lens', 'method', 'comparison', 'type'],
    'timeframe': ['timeframe', 'window', 'horizon', 'lookback'],
    'definition': ['strict_definition', 'definition', 'rule', 'condition'],
    'direction': ['yes_means', 'direction', 'signal', 'bias'],
    'source': ['source', 'data_source'],
    'history_start': ['history_start', 'data_available_from', 'history'],
    'kbo': ['known_before_open', 'known_before_open?', 'kbo', 'pre_open'],
    'owner': ['added_by', 'owner'],
    'notes': ['notes', 'note'],
}
def colmap(header):
    norm = {re.sub(r'[^a-z0-9]', '', h.lower()): h for h in header}
    m = {}
    for k, al in ALIASES.items():
        for a in al:
            n = re.sub(r'[^a-z0-9]', '', a.lower())
            hit = norm.get(n) or next((v for kk, v in norm.items() if kk.startswith(n)), None)
            if hit: m[k] = hit; break
    return m

NUM = re.compile(r'\d|[<>]=?|≤|≥|=|\bcross(es|ed)?\b|\btop\b|\bbottom\b|\bpattern\b|\bregex\b|\bbetween\b|\bstreak\b')
TFS = ['1', '3', '5', '10', '20', '60']
METHODS = {'level': ['level', 'fixed', 'threshold'], 'extreme': ['extreme', 'percentile', 'high', 'low'],
           'change': ['change', 'delta', 'revis'], 'cross': ['cross'], 'streak': ['streak', 'consecutive'],
           'divergence': ['divergen'], 'rank': ['rank']}
SELF = re.compile(r'own|its own|prior|vs \d+d ago|history|extreme|percentile|change|streak|sma|days? (ago|earlier)', re.I)
OTHERS = re.compile(r'sector|industry|market|spy|peer|theme|index|qqq|universe|vs s&p|group', re.I)

SECRE = re.compile(r'\b(?:SEC|EDGAR|10-K|10-Q|8-K|Form\s*4|S-1|S-3|424B\w*|13D|13G|13F|DEF\s*14A|filings?)\b', re.I)
FTD = re.compile(r'\b(?:fails?[- ]to[- ]deliver|FTDs?)\b', re.I)
FVX = re.compile(r'\bfinviz\b', re.I)
CAL = re.compile(r'\b(?:Fed|Federal Reserve|FOMC|NYSE|Cboe)\b', re.I)

KRE = re.compile(r'parse|read the|extract|summari[sz]e|transcript|paragraph|LLM|NLP', re.I)

def norm_def(s):
    s = s.lower()
    s = re.sub(r'\bbut mirror:?', '', s)
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9<>=.%+\- ]', ' ', s)).strip()

def tf_of(s):
    out = set()
    for t in re.findall(r'(\d+)\s*(?:d\b|day|-day|trading)', s.lower()): out.add(t)
    if re.search(r'prev bar|d-1\)|1d|today|daily', s.lower()): out.add('1')
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--root', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument('--final', action='store_true'); ap.add_argument('--fuzzy', action='store_true', help='also fuzzy-dedupe within an owner')
    a = ap.parse_args()
    root = a.root; qa = os.path.join(root, 'qa'); os.makedirs(qa, exist_ok=True)
    rows = []
    for f in sorted(glob.glob(os.path.join(root, 'inbox', '*.csv'))):
        b = os.path.basename(f)
        if b.endswith('.compact.csv') or '-removed-' in b or '-dropped-' in b: continue
        owner = b[:-4]
        with open(f, newline='', encoding='utf-8-sig') as fh:
            rd = csv.DictReader(fh); m = colmap(rd.fieldnames or [])
            for i, r in enumerate(rd):
                g = lambda k: (r.get(m[k]) or '').strip() if k in m else ''
                rows.append(dict(owner=owner, file=b, id=g('id') or f'{owner}#{i+2}', variant=g('variant'), lens=g('lens'),
                                 tf=g('timeframe'), d=g('definition'), dir=g('direction'), src=g('source'),
                                 hs=g('history_start'), kbo=g('kbo'), notes=g('notes'), issues=[]))
    ids = {r['id'] for r in rows}
    for r in rows:
        if not r['src']: r['issues'].append('a:no_source')
        if not r['hs']: r['issues'].append('b:no_history_start')
        if not NUM.search(r['d'].lower()): r['issues'].append('c:loose_definition')
        d0 = r['dir']
        if not (re.match(r'^(bullish|bearish)\b', d0, re.I) or re.match(r'^neutral\s*[(/:–-]\s*\S', d0, re.I)):
            r['issues'].append('d:bad_direction')
        if r['kbo'].lower() not in ('yes', 'y', 'true'): r['issues'].append('e:not_known_before_open')
        txt = ' '.join([r['id'], r['variant'], r['lens'], r['notes'], r['d']]).lower()
        r['is_but'] = 'but' in re.findall(r'[a-z]+', txt) or 'mirror' in txt
    # h: series must be fetch-proven in qa/src/fetch_proof_*.csv (also qa/fetch_proof_*.csv)
    reg = {}; regi = {}
    for pf in sorted(set(glob.glob(os.path.join(qa, 'src', 'fetch_proof_*.csv')) + glob.glob(os.path.join(qa, 'fetch_proof_*.csv')))):
        with open(pf, newline='', encoding='utf-8-sig') as fh:
            for p in csv.DictReader(fh):
                k = re.sub(r'\s+', ' ', (p.get('series') or '').strip().lower())
                if 'known_at' not in p and 'published_at' in p: p['known_at'] = p.pop('published_at')
                if k: reg[k] = (p.get('status') or '').strip().lower(); regi[k] = p
    hwarn = collections.Counter()
    for r in rows:
        ser = re.sub(r'\s+', ' ', re.sub(r'\(?\s*but( mirror)?\s*\)?', '', r['variant'], flags=re.I)).strip().lower()
        st = reg.get(ser)
        if st is None: r['issues'].append('h:not_fetch_proven')
        elif st == 'no_source': r['issues'].append('h:no_source')
        elif st == 'save_nightly': r.setdefault('warn', []).append('h:untestable until ~30 fires'); hwarn[r['owner']] += 1
        elif st != 'works': r['issues'].append('h:bad_status')
        # i: known_at must exist and be <= 09:25 ET on the test day (format 'D-n HH:MM ET'); revised=yes needs first_release_source
        p = regi.get(ser)
        if p is not None:
            ka = (p.get('known_at') or '').strip()
            m = re.match(r'^D(?:-(\d+)|0)?\s+(\d{1,2}):(\d{2})\s*ET', ka, re.I)
            if not ka: r['issues'].append('i:no_known_at')
            elif not m: r['issues'].append('i:bad_known_at_format')
            elif not m.group(1) and (int(m.group(2)), int(m.group(3))) > (9, 25): r['issues'].append('i:known_after_0925ET')
            df = (p.get('data_form') or '').strip().lower()
            if df not in ('number', 'label', 'date'): r['issues'].append('k:data_form_' + (df or 'missing'))
            if (p.get('revised') or '').strip().lower() in ('yes', 'y', 'true') and not (p.get('first_release_source') or '').strip():
                r['issues'].append('i:revised_no_first_release')
    # j: SEC/EDGAR filing-derived rows FAIL unless source is a Finviz export/snapshot column or a fixed-calendar source (Fed, NYSE, Cboe)
    for r in rows:
        if SECRE.search(r['src'] + ' ' + r['d']) and not (FVX.search(r['src']) or CAL.search(r['src']) or FTD.search(r['variant'] + ' ' + r['d'] + ' ' + r['src'])):
            r['issues'].append('j:sec_filing_source')
    # k: definition must not need text parsing / NLP
    for r in rows:
        if KRE.search(r['d']): r['issues'].append('k:text_parsing_definition')
    # BUT twin check: twin = same owner+variant base with opposite direction
    grp = collections.defaultdict(list)
    for r in rows:
        base = re.sub(r'\(?\s*but( mirror)?\s*\)?', '', r['variant'], flags=re.I).strip().lower()
        r['base'] = base; grp[(r['owner'], base)].append(r)
    for k, g in grp.items():
        dirs = {x['dir'][:7].lower() for x in g}
        has_but = any(x['is_but'] for x in g) or ('bullish' in dirs and 'bearish' in dirs)
        for r in g:
            idbut = r['id'] + '-BUT' in ids or (r['id'].endswith('-BUT') and r['id'][:-4] in ids)
            if not (has_but or idbut): r['issues'].append('g:no_BUT_twin')
    # f: near-duplicates across owners, bucketed by leading tokens + length
    dup_pairs = []
    buckets = collections.defaultdict(list)
    for r in rows:
        r['nd'] = norm_def(r['d'])
        toks = sorted(set(t for t in r['nd'].split() if len(t) > 3 and not t.isdigit()))[:3]
        buckets[(tuple(toks), len(r['nd']) // 20)].append(r)
    seen = set()
    for bk in buckets.values():
        if len(bk) < 2: continue
        for i in range(len(bk)):
            for j in range(i + 1, len(bk)):
                x, y = bk[i], bk[j]
                if x['owner'] == y['owner'] and not a.fuzzy: continue
                if (x['id'], y['id']) in seen: continue
                if not x['nd'] or abs(len(x['nd']) - len(y['nd'])) > 0.25 * max(len(x['nd']), 1): continue
                s = sim(x['nd'], y['nd'])
                if s >= 88:
                    seen.add((x['id'], y['id'])); dup_pairs.append((x, y, s))
                    x['issues'].append(f"f:dup~{y['owner']}:{y['id']}"); y['issues'].append(f"f:dup~{x['owner']}:{x['id']}")
    # grid coverage per variant
    vg = collections.defaultdict(list)
    for r in rows: vg[(r['owner'], r['base'])].append(r)
    grid = []
    for (o, v), g in sorted(vg.items()):
        blob = ' '.join(x['lens'] + ' ' + x['d'] + ' ' + x['tf'] for x in g)
        tfs = set().union(*[tf_of(x['tf'] + ' ' + x['d']) for x in g]) & set(TFS)
        meth = {k for k, al in METHODS.items() if any(w in blob.lower() for w in al)}
        has_self = bool(SELF.search(blob)) or bool(meth & {'extreme', 'change', 'streak', 'cross'})
        has_oth = bool(OTHERS.search(blob))
        gaps = []
        if not has_self: gaps.append('self')
        if not has_oth: gaps.append('others')
        mt = [t + 'd' for t in TFS if t not in tfs]
        mm = [k for k in METHODS if k not in meth]
        if mt: gaps.append('tf:' + '/'.join(mt))
        if mm: gaps.append('method:' + '/'.join(mm))
        grid.append(dict(owner=o, variant=v, rows=len(g), self=int(has_self), others=int(has_oth),
                         timeframes=' '.join(t + 'd' for t in TFS if t in tfs), methods=' '.join(sorted(meth)),
                         but_twin=int(not any('g:no_BUT_twin' in x['issues'] for x in g)), gaps='; '.join(gaps)))
    with open(os.path.join(qa, 'grid_coverage.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(grid[0].keys()) if grid else ['owner']); w.writeheader(); w.writerows(grid)
    owners = sorted({r['owner'] for r in rows})
    codes = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k']
    for o in owners:
        with open(os.path.join(qa, f'fix_{o}.csv'), 'w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['id', 'file', 'issue_count', 'issues'])
            for r in rows:
                if r['owner'] == o and r['issues']: w.writerow([r['id'], r['file'], len(r['issues']), ' | '.join(r['issues'])])
    L = [f"# Checklist QA report — {'FINAL' if a.final else 'PRELIMINARY'}", '',
         'Checks: a source, b history_start, c numeric/exact definition, d direction, e known_before_open=Yes, f cross-owner near-dup (>=88%), g BUT twin, h fetch-proven series (qa/src/fetch_proof_*.csv; missing/no_source=FAIL, save_nightly=WARN untestable until ~30 fires), i known_at <= 09:25 ET test day (registry col known_at, was published_at; format D-n HH:MM ET; revised=yes needs first_release_source), j no SEC/EDGAR/filing-derived source (exempt: Finviz export/snapshot, Fed/NYSE/Cboe, fails-to-deliver/FTD), k registry data_form in number|label|date and no parse/extract/transcript/LLM/NLP definitions.', '',
         '| owner | rows | a | b | c | d | e | f | g | h | i | j | k | h WARN | rows w/ issues | variants | variants w/ gaps |', '|' + '---|' * 18]
    for o in owners:
        rs = [r for r in rows if r['owner'] == o]
        cnt = collections.Counter(i.split(':')[0] for r in rs for i in r['issues'])
        gv = [x for x in grid if x['owner'] == o]
        L.append(f"| {o} | {len(rs)} | " + ' | '.join(str(cnt[c]) for c in codes) + f" | {hwarn[o]}" +
                 f" | {sum(1 for r in rs if r['issues'])} | {len(gv)} | {sum(1 for x in gv if x['gaps'])} |")
    L += ['', f'Cross-owner near-duplicate pairs: {len(dup_pairs)}', '']
    for x, y, s in dup_pairs[:50]: L.append(f"- {x['owner']}:{x['id']} ~ {y['owner']}:{y['id']} ({s:.0f}%)")
    L += ['', '## Variants with coverage gaps', '']
    for x in grid:
        if x['gaps']: L.append(f"- **{x['owner']}** / {x['variant']} ({x['rows']} rows): {x['gaps']}")
    open(os.path.join(qa, 'report.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L[:8 + len(owners) + 2]))
    print('\n'.join(sorted({i for r in rows for i in r['issues'] if i[:2] in ('h:', 'i:')} | {i for r in rows for i in r.get('warn', [])})))

if __name__ == '__main__': main()

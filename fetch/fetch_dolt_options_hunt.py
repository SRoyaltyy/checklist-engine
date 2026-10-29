"""DoltHub post-no-preference/options REAL coverage + PIT hunt (§0b 2026-10-30 00:10).

Prior work (docs/DOLT_OPTIONS_COVERAGE_V5.json, runs 40307954973 / 40335534016)
only measured coverage SAMPLES. This script does the real pulls:

  Phase A  per-month, per-table (volatility_history, option_chain) 2020-01..now:
           rows, distinct symbols, weekend-labelled rows, min/max date,
           min/max expiration (option_chain only); accumulates the distinct
           act_symbol set per table across the whole window.
  Phase B  universe match: tickers from universe_2020_survivors_le2024.parquet
           matched against the accumulated symbol sets -> real per-year coverage
           of OUR universe (not samples).
  Phase C  PIT probes:
           1. weekend/non-trading-date labels (from Phase A counters)
           2. data lag: max(date) per month vs run date
           3. revision check: commit from ~8 months back (dolt_log offset) vs
              HEAD over sampled (symbol, date) rows of BOTH tables - identical
              values => never revised => PIT-safe
           4. publish timing: last 12 commit messages vs commit timestamps
              (daily "volatility_history YYYY-MM-DD update" pattern)

Output: $RUNNER_TEMP/dolt_options_hunt_v1.json, uploaded to data-ext-2020-26-v1.

Usage (runner): python3 fetch/fetch_dolt_options_hunt.py \
    --universe $RUNNER_TEMP/world_in/universe_2020_survivors_le2024.parquet \
    --out $RUNNER_TEMP/dolt_options_hunt_v1.json
"""
import argparse, io, json, os, sys, time, urllib.parse, urllib.request

API = 'https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master'
UA = {'User-Agent': 'checklist-engine-fetch/1.0'}
TABLES = ('volatility_history', 'option_chain')


def q(sql, tries=6):
    err = None
    for k in range(tries):
        try:
            u = API + '?' + urllib.parse.urlencode({'q': sql})
            req = urllib.request.Request(u, headers=UA)
            j = json.load(urllib.request.urlopen(req, timeout=180))
            if j.get('query_execution_status') == 'Success':
                return j['rows']
            err = j.get('query_execution_message')
        except Exception as e:
            err = e
        time.sleep(min(30, 3 * (2 ** k)))
    raise RuntimeError(f'query failed after {tries} tries: {sql[:90]}... last err: {err}')


def months(start='2020-01'):
    out, y, m = [], int(start[:4]), int(start[5:7])
    today = time.strftime('%Y-%m')
    while f'{y:04d}-{m:02d}' <= today:
        out.append(f'{y:04d}-{m:02d}')
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def next_month(mm):
    y, m = int(mm[:4]), int(mm[5:7]) + 1
    return f'{y + (m == 13):04d}-{1 if m == 13 else m:02d}-01'


def phase_a(state):
    for mm in months():
        for t in TABLES:
            key = f'{t}:{mm}'
            if key in state['monthly']:
                continue
            exp = ', MIN(expiration) exp_min, MAX(expiration) exp_max' if t == 'option_chain' else ''
            rows = q(f"SELECT COUNT(*) n, COUNT(DISTINCT act_symbol) s, "
                     f"SUM(DAYOFWEEK(date) IN (1,7)) weekend_rows, MIN(date) mn, MAX(date) mx{exp} "
                     f"FROM {t} WHERE date >= '{mm}-01' AND date < '{next_month(mm)}'")
            r = rows[0]
            syms = q(f"SELECT DISTINCT act_symbol FROM {t} "
                     f"WHERE date >= '{mm}-01' AND date < '{next_month(mm)}'")
            symset = {x['act_symbol'] for x in syms}
            state['symbols'][t] |= symset
            rec = dict(month=mm, rows=int(r['n']), symbols=int(r['s']),
                       weekend_rows=int(r['weekend_rows'] or 0),
                       min_date=str(r['mn']), max_date=str(r['mx']))
            if t == 'option_chain':
                rec['exp_min'] = str(r['exp_min']); rec['exp_max'] = str(r['exp_max'])
            state['monthly'][key] = rec
            print(f'A {key}: rows={rec["rows"]} symbols={rec["symbols"]} '
                  f'weekend={rec["weekend_rows"]}', flush=True)
        save()


def phase_b(state, universe_path):
    try:
        import pandas as pd
        u = pd.read_parquet(universe_path, columns=['ticker'])
        tickers = set(u['ticker'].astype(str))
    except Exception as e:
        state['universe_note'] = f'universe unavailable: {e}'
        print('B: universe unavailable:', e, flush=True)
        return
    state['universe_n'] = len(tickers)
    for t in TABLES:
        have = state['symbols'][t]
        matched = tickers & have
        state['match'][t] = dict(
            universe_symbols=len(tickers), table_symbols=len(have),
            matched=len(matched), matched_pct=round(100 * len(matched) / max(1, len(tickers)), 2),
            sample_missed=sorted(tickers - have)[:15])
        print(f'B {t}: matched {len(matched)}/{len(tickers)} '
              f'({state["match"][t]["matched_pct"]}%)', flush=True)


def phase_c(state):
    c = {}
    # publish timing: last 12 commits
    log = q('SELECT commit_hash, committer, date, message FROM dolt_log LIMIT 12')
    c['publish_timing'] = [
        dict(commit=x['commit_hash'][:12], committed_at=x['date'], message=x['message'])
        for x in log]
    msgs = [x['message'] for x in log]
    import re
    lags = []
    for x in log:
        m = re.match(r'(volatility_history|option_chain) (\d{4}-\d{2}-\d{2}) update', x['message'])
        if m:
            d_data = time.mktime(time.strptime(m.group(2), '%Y-%m-%d'))
            d_commit = time.mktime(time.strptime(x['date'][:19], '%Y-%m-%d %H:%M:%S'))
            lags.append(round((d_commit - d_data) / 3600, 1))
    c['publish_lag_hours_sample'] = lags
    print('C: publish lags (h):', lags, flush=True)

    # revision check: commit ~8 months back
    old = q('SELECT commit_hash, date FROM dolt_log LIMIT 1 OFFSET 240')
    if not old:
        c['revision_check'] = 'no old commit found'
        return
    h_old, d_old = old[0]['commit_hash'], old[0]['date']
    print('C: old commit', h_old[:12], d_old, flush=True)
    c['old_commit'] = dict(hash=h_old, committed_at=d_old)

    # sample real rows: 8 spread-out dates, liquid symbols
    probes = [('2020-06-15', 'AAPL'), ('2021-01-27', 'GME'), ('2022-01-21', 'GME'),
              ('2023-03-13', 'NVDA'), ('2024-06-14', 'AAPL'), ('2025-04-04', 'MSFT')]
    mm, checked = 0, 0
    for d, sym in probes:
        now = q(f"SELECT * FROM volatility_history WHERE date='{d}' AND act_symbol='{sym}'")
        if not now:
            continue
        old_r = q(f"SELECT * FROM volatility_history AS OF '{h_old}' "
                  f"WHERE date='{d}' AND act_symbol='{sym}'")
        checked += 1
        if old_r != now:
            mm += 1
            print(f'C: VH MISMATCH {d} {sym}', flush=True)
            c.setdefault('vh_mismatches', []).append(dict(date=d, symbol=sym))
    c['vh_revision'] = dict(probes=len(probes), present=checked, mismatches=mm)

    # option_chain revision probe: 4 (symbol, date) rows
    oc = q("SELECT date, act_symbol, expiration, strike, call_put, bid, ask, vol, delta "
           "FROM option_chain WHERE act_symbol='AAPL' AND date='2024-06-14' LIMIT 4")
    oc_mm = 0
    for row in oc:
        key = (f"date='{row['date']}' AND act_symbol='{row['act_symbol']}' "
               f"AND expiration='{row['expiration']}' AND strike={row['strike']} "
               f"AND call_put='{row['call_put']}'")
        now = q(f"SELECT bid, ask, vol, delta, gamma, theta, vega, rho FROM option_chain WHERE {key}")
        old_r = q(f"SELECT bid, ask, vol, delta, gamma, theta, vega, rho "
                  f"FROM option_chain AS OF '{h_old}' WHERE {key}")
        if old_r != now:
            oc_mm += 1
    c['oc_revision'] = dict(probes=len(oc), mismatches=oc_mm)
    state['pit'] = c
    print(f'C: VH mismatches {mm}/{checked}; OC mismatches {oc_mm}/{len(oc)}', flush=True)


OUT = None
STATE = None


def save():
    tmp = OUT + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        f.write(json.dumps(STATE, default=str))
    os.replace(tmp, OUT)


def main():
    global OUT, STATE
    ap = argparse.ArgumentParser()
    ap.add_argument('--universe', default='')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    OUT = a.out
    if os.path.exists(OUT):
        STATE = json.load(io.open(OUT, encoding='utf-8'))
        for t in TABLES:
            STATE['symbols'][t] = set(STATE['symbols'].get(t, []))
        print('RESUME from checkpoint', flush=True)
    else:
        STATE = dict(monthly={}, symbols={t: set() for t in TABLES}, match={}, pit={})
    phase_a(STATE)
    if a.universe:
        phase_b(STATE, a.universe)
    phase_c(STATE)
    for t in TABLES:
        STATE['symbols'][t] = sorted(STATE['symbols'][t])
    save()
    print('DONE ->', OUT, flush=True)


if __name__ == '__main__':
    main()

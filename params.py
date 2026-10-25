"""Named thresholds. Every cutoff a question uses is read from PARAMS at call time, so a grid file can sweep it.
Usage is detected automatically (TrackedParams records which names each question reads)."""
DEFAULTS = dict(leg_atr=3.0, long_trend=60,
                # v2.7.1 history-bucket numbers (HISTORY_BUCKETS_v2.7.1_FINAL.csv)
                div_unit=0.25, div_K=2, ooe_unit=1.0, speed_net=0.5, speed_fast=1.5, speed_slow=0.67, route_flat=1.0, route_mid=80,
                char_wild=1.5, char_calm=0.67, retest_tol=0.5, squeeze_pct=20, squeeze_break=0.5, stage_slope=0.05,
                vop_hi=80, vop_lo=20, ll_corr=0.2, tfa_t=2.0, shock_unit=3.0, shock_held=0.25, shock_gone=0.75, hist_250=250, hist_kdiv=10, hist_thirds=3, stage_min=10, stage_div=2, tfa_mult=3, stage_slope2=0.05)
CROSS = ('leg_atr', 'long_trend')        # Cyrus: full cross (16 versions) where a question uses both
class TrackedParams(dict):
    def __init__(s, *a): super().__init__(*a); s.used = set()
    def __getitem__(s, k): s.used.add(k); return dict.__getitem__(s, k)
P = TrackedParams(DEFAULTS)
def set_params(over):
    used = P.used; P.clear(); P.update(DEFAULTS); P.update(over); P.used = used

# v2.7.2 CUTOFF_GRID id -> engine param (only ids listed here are swept; the rest are reported as not wired)
CID = {'C414_divergence_sync__atr0p25':'div_unit','C415_order_of_events__atr1':'ooe_unit','C416_speed__atr0p5':'speed_net',
 'C417_change_of_state__bars250':'hist_250','C418_time_since__bars250':'hist_250','C419_route__atr1':'route_flat','C420_route__pct80':'route_mid',
 'C421_character_change__bars250':'hist_250','C422_character_change__scalar1p5':'char_wild','C423_character_change__scalar0p67':'char_calm',
 'C424_retests__atr0p5':'retest_tol','C425_retest_count__atr0p5':'retest_tol','C428_squeeze_release__scalar250':'hist_250',
 'C429_squeeze_release__atr0p5':'squeeze_break','C430_stage__scalar10':'stage_min','C431_stage__scalar2':'stage_div','C432_stage__atr0p05':'stage_slope',
 'C434_lead_lag__scalar0p2':'ll_corr','C435_timeframe_agreement__scalar2':'tfa_t','C436_shock_recovery__atr3':'shock_unit',
 'C437_shock_recovery__scalar0p25':'shock_held','C438_shock_recovery__scalar0p75':'shock_gone','C439_ALL_HISTORY__scalar10':'hist_kdiv',
 'C440_ALL_HISTORY__scalar3':'hist_thirds','C441_ALL_HISTORY__bars250':'hist_250'}

import json, hashlib
PINS = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'dials_pins.json')   # bump a version = edit path+sha256 here only
def pinned(name):
    from datapaths import D
    p = json.load(open(PINS))[name]; p['path'] = D(p['path']); s = hashlib.sha256(open(p['path'], 'rb').read()).hexdigest()
    if s != p['sha256']: raise SystemExit(f'{name} sha mismatch: {s} != pinned {p["sha256"]} - not running')
    return p['path']

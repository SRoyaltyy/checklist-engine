"""Emit docs/BINARY_MASTER_SEC_V1.csv — strict SEC/options binary definitions.

Kimi lane (TODO item 3). Standalone emitter: the canonical v2.7 grid and
BINARY_MASTER_V1.csv stay untouched (test_binary_canonical_plan.py pins the
sealed grid totals; extending it is a QUESTION_TREE_v3 decision for James).
Rows use the exact BINARY_MASTER_V1 column schema so a future v3 merge is a
mechanical append. Every row is a definition only — no data is downloaded;
measurements live in world_sec_events.py and answer NOT_EVALUABLE until
Venice's pipelines land (NE is excluded, never NO).
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from world_question_grid import identity, ROOT
from ci.binary_master_build import CSV_COLUMNS

SEC_CSV = 'BINARY_MASTER_SEC_V1.csv'
SEC_REPORT = 'BINARY_MASTER_SEC_V1_REPORT.json'

DATA_GROUP = '8 Non-price data'
NE_CSV = ('NOT_EVALUABLE (excluded, never NO): no usable event/record before D 09:30 ET '
          '(dictionary C29 public-timestamp rule), empty session calendar, or pre-source-start. '
          'A known 0 is evaluable. Measurements: world_sec_events.py')
KNOWABLE_CSV = ('Usable only if the record public timestamp (SEC acceptance datetime) is '
                '< setup date D 09:30 ET (dictionary C29); join on acceptance date < D, '
                'never period end; no day-D information.')
VIEWPORT_CSV = ('CONCRETE event marker: event date, days_since (trading days), direction from '
                'the fixed mapping table (upgrade/P = bullish, downgrade/S = bearish); '
                'no free text, no circles.')

BLOCK_FORM4 = 'E SEC Form 4 (I187)'
BLOCK_SECTOR = 'K Sector membership (C26)'
BLOCK_SHORTINT = 'J FINRA short interest (I188)'
BLOCK_SHARES = 'H Shares outstanding (I193)'
BLOCK_XBRL = 'L SEC XBRL fundamentals (I192)'
RECIPE_XBRL = 'sec_xbrl'
BLOCK_DIV = 'I Dividends (I196)'
RECIPE_SECTOR = 'sec_sector'
RECIPE_SHORTINT = 'finra_si'
RECIPE_SHARES = 'sec_shares'
RECIPE_DIV = 'sec_dividend'
BLOCK_ANALYST = 'G Analyst actions (I197)'
BLOCK_13F = 'M SEC 13F holdings (I199)'
BLOCK_SHORTVOL = 'F FINRA short volume (I189)'
BLOCK_CBOE = 'N CBOE market-wide options (I201)'
RECIPE_FORM4 = 'sec_form4'
RECIPE_ANALYST = 'sec_analyst'
RECIPE_13F = 'sec_13f'
RECIPE_FINRA = 'finra_short'
RECIPE_CBOE = 'cboe_market'

# Facet x dial grid for the Form 4 group (spec todo3_sec_options_defs_v1.md section 3).
# Thresholds literal; windows in trading days ending D-1.
_DAYS_SINCE = (5, 10, 20)
_COUNT_WINDOWS = (5, 10, 20)
_COUNT_RUNGS = (1, 2)
_NET_WINDOWS = (5, 20)
_NET_RUNGS = (0, 100000, 500000)
_SIZE_WINDOWS = (60,)
_SIZE_RUNGS = (100000, 500000, 1000000)
_DIRECTIONS = ('bullish', 'bearish')


def _row(facet, feature_expression, feature_kind, feature_unit, comparator, threshold,
         formula_expr, yes, outcome, recipe=RECIPE_FORM4, block=BLOCK_FORM4,
         source='I187', extra_feature=None):
    feature = dict(recipe=recipe, expression=feature_expression, kind=feature_kind,
                   unit=feature_unit)
    if extra_feature:
        feature.update(extra_feature)
    semantic = dict(feature=feature, comparator=comparator,
                    comparison_threshold=str(threshold), outcome=outcome)
    return {
        'question_id': 'BS1-' + identity(semantic),
        'feature_id': 'BSF1-' + identity(feature),
        'definition_status': 'BOUND',
        'data_group': DATA_GROUP,
        'block': block,
        'facet': facet,
        'source_question_id': source,
        'source_variant_id': '',
        'source_outcome': outcome,
        'timeframe_days': 1,
        'lookback_bars': '',
        'feature_recipe': recipe,
        'feature_expression': feature_expression,
        'feature_kind': feature_kind,
        'feature_unit': feature_unit,
        'transform': 'identity',
        'comparator': comparator,
        'comparison_threshold': str(threshold),
        'formula': '(' + formula_expr + ') ' + comparator + ' ' + str(threshold),
        'yes_condition': yes,
        'not_evaluable_condition': NE_CSV,
        'viewport_drawing': VIEWPORT_CSV,
        'knowable_at_setup_open': KNOWABLE_CSV,
        'expression': 'CONCRETE',
        'missing': 'sec_definition_only_answers_not_evaluable_until_data_lands',
        'feature_json': json.dumps(feature, sort_keys=True, separators=(',', ':')),
    }


def form4_definitions():
    rows = []
    for direction in _DIRECTIONS:
        for n in _DAYS_SINCE:
            expr = f'sec_form4_days_since_last_v1(direction={direction})'
            rows.append(_row(
                'form4_days_since', expr, 'integer_count', 'trading_days_since_last_' + direction,
                '<=', n, expr,
                f'latest {direction} Form 4 event (P=bullish, S=bearish) is <= {n} trading days '
                f'before D (event day = 0)', f'days_since_{direction}_le{n}'))
        for window in _COUNT_WINDOWS:
            for k in _COUNT_RUNGS:
                expr = f'sec_form4_count_v1(direction={direction},window={window})'
                rows.append(_row(
                    'form4_count', expr, 'integer_count',
                    f'count_{direction}_events_last_{window}_sessions',
                    '>=', k, expr,
                    f'>={k} {direction} Form 4 events in the last {window} completed sessions',
                    f'count_{direction}_w{window}_ge{k}'))
    # cluster: dictionary I187 spec (>=3 distinct insiders with P, 10 sessions)
    expr = 'sec_form4_cluster_v1(min_insiders=3,window=10)'
    rows.append(_row(
        'form4_cluster', expr, 'boolean', 'distinct_insider_buyers_ge3_last_10_sessions',
        '=', 1, expr,
        '>= 3 distinct insiders have a usable P event in the last 10 completed sessions',
        'cluster_ge3_w10', extra_feature=dict(min_insiders=3, window=10)))
    # net dollars is direction-agnostic (sum P - sum S): outside the direction loop
    for window in _NET_WINDOWS:
        for t in _NET_RUNGS:
            expr = f'sec_form4_net_dollars_v1(window={window})'
            rows.append(_row(
                'form4_net_dollars', expr, 'continuous',
                f'net_purchase_dollars_last_{window}_sessions',
                '>=', t, expr,
                f'sum($P) - sum($S) over the last {window} sessions >= {t} USD '
                '(non-directional codes contribute 0)',
                f'net_dollars_w{window}_ge{t}'))
    for window in _SIZE_WINDOWS:
        for t in _SIZE_RUNGS:
            expr = f'sec_form4_max_trade_v1(direction=bullish,window={window})'
            rows.append(_row(
                'form4_max_trade', expr, 'continuous',
                f'largest_purchase_dollars_last_{window}_sessions',
                '>=', t, expr,
                f'largest single P event in the last {window} sessions >= {t} USD',
                f'max_trade_w{window}_ge{t}'))
    return rows


def analyst_definitions():
    """I197 analyst actions: event facets reusing the fixed direction table
    (upgrade=bullish, downgrade=bearish; initiate/reiterate/PT-only counted,
    not directional)."""
    rows = []
    recipe, block, source = RECIPE_ANALYST, BLOCK_ANALYST, 'I197'
    for direction in _DIRECTIONS:
        for n in (5, 10, 20):
            expr = f'sec_analyst_days_since_last_v1(direction={direction})'
            rows.append(_row(
                'analyst_days_since', expr, 'integer_count',
                'trading_days_since_last_' + direction + '_action',
                '<=', n, expr,
                f'latest {direction} analyst action <= {n} trading days before D',
                f'days_since_{direction}_le{n}',
                recipe=recipe, block=block, source=source))
        for k in (1, 2):
            expr = f'sec_analyst_count_v1(direction={direction},window=30)'
            rows.append(_row(
                'analyst_count', expr, 'integer_count',
                f'count_{direction}_actions_last_30_sessions',
                '>=', k, expr,
                f'>={k} {direction} analyst actions in the last 30 completed sessions',
                f'count_{direction}_w30_ge{k}',
                recipe=recipe, block=block, source=source,
                extra_feature=dict(direction=direction, window=30)))
    for k in (1, 2, 3):
        expr = 'sec_analyst_net_direction_v1(window=30)'
        rows.append(_row(
            'analyst_net_direction', expr, 'signed_integer',
            'upgrades_minus_downgrades_last_30_sessions',
            '>=', k, expr,
            f'upgrades - downgrades over the last 30 sessions >= {k} '
            '(non-directional actions contribute 0)',
            f'net_dir_w30_ge{k}',
            recipe=recipe, block=block, source=source, extra_feature=dict(window=30)))
    expr = 'sec_analyst_last_pt_change_pct_v1()'
    rows.append(_row(
        'analyst_pt_change', expr, 'continuous', 'last_action_pt_change_percent',
        '>=', 5, expr,
        'latest usable analyst action raised the price target by >= 5%',
        'pt_change_ge5', recipe=recipe, block=block, source=source))
    rows.append(_row(
        'analyst_pt_change', expr, 'continuous', 'last_action_pt_change_percent',
        '>=', 10, expr,
        'latest usable analyst action raised the price target by >= 10%',
        'pt_change_ge10', recipe=recipe, block=block, source=source))
    rows.append(_row(
        'analyst_pt_change', expr, 'continuous', 'last_action_pt_change_percent',
        '<=', -5, expr,
        'latest usable analyst action cut the price target by >= 5%',
        'pt_change_le-5', recipe=recipe, block=block, source=source))
    return rows


def holdings13f_definitions():
    """I199 13F holdings: quarterly position reports. NO direction mapping
    (spec section 2) — changes are quantitative only. Usable only if the
    filing's public timestamp (SEC acceptance) is < D 09:30 ET; the 45-day
    quarter-end lag is a data property enforced by the pipeline."""
    rows = []
    recipe, block, source = RECIPE_13F, BLOCK_13F, 'I199'
    for n in (10, 20):
        expr = 'sec_13f_days_since_last_v1()'
        rows.append(_row(
            '13f_days_since', expr, 'integer_count', 'trading_days_since_latest_filing',
            '<=', n, expr,
            f'latest usable 13F filing <= {n} trading days before D (filing accepted '
            '< D 09:30 ET)', f'days_since_filing_le{n}',
            recipe=recipe, block=block, source=source))
    for k in (5, 10, 20):
        expr = 'sec_13f_filers_v1()'
        rows.append(_row(
            '13f_filers', expr, 'integer_count', 'filer_count_latest_filing',
            '>=', k, expr,
            f'>= {k} distinct filers hold the stock in the latest usable 13F filing',
            f'filers_ge{k}', recipe=recipe, block=block, source=source))
    expr = 'sec_13f_shares_change_pct_v1()'
    rows.append(_row(
        '13f_shares_change', expr, 'continuous', 'total_shares_qoq_change_percent',
        '>=', 10, expr,
        'aggregate 13F shares held rose >= 10% between the latest two usable filings',
        'shares_chg_ge10', recipe=recipe, block=block, source=source))
    rows.append(_row(
        '13f_shares_change', expr, 'continuous', 'total_shares_qoq_change_percent',
        '>=', 25, expr,
        'aggregate 13F shares held rose >= 25% between the latest two usable filings',
        'shares_chg_ge25', recipe=recipe, block=block, source=source))
    rows.append(_row(
        '13f_shares_change', expr, 'continuous', 'total_shares_qoq_change_percent',
        '<=', -10, expr,
        'aggregate 13F shares held fell >= 10% between the latest two usable filings',
        'shares_chg_le-10', recipe=recipe, block=block, source=source))
    expr = 'sec_13f_new_filer_v1()'
    rows.append(_row(
        '13f_new_filer', expr, 'boolean', 'new_filer_in_latest_filing',
        '=', 1, expr,
        'the latest usable 13F filing contains at least one filer absent from the '
        'previous usable filing', 'new_filer',
        recipe=recipe, block=block, source=source))
    return rows


def short_interest_definitions():
    """I188 FINRA short interest: bi-weekly settlement publications; the
    SETTLEMENT->PUBLICATION lag is explicit (only publications with
    public_dt < D 09:30 ET are usable, never period end)."""
    rows = []
    recipe, block, source = RECIPE_SHORTINT, BLOCK_SHORTINT, 'I188'
    for t in (5, 10, 20):
        expr = 'finra_si_pct_float_v1()'
        rows.append(_row(
            'si_pct_float', expr, 'continuous', 'short_interest_pct_of_float_latest_publication',
            '>=', t, expr,
            f'short interest >= {t}% of float in the latest usable publication',
            f'si_pct_ge{t}', recipe=recipe, block=block, source=source))
    for t in (3, 5, 10):
        expr = 'finra_si_days_to_cover_v1()'
        rows.append(_row(
            'si_days_to_cover', expr, 'continuous', 'short_interest_over_avg_daily_volume',
            '>=', t, expr,
            f'days to cover >= {t} in the latest usable publication',
            f'dtc_ge{t}', recipe=recipe, block=block, source=source))
    for t in (0.8, 0.9):
        expr = 'finra_si_pct_percentile_v1(lookback=12)'
        rows.append(_row(
            'si_percentile', expr, 'continuous', 'si_pct_percentile_last_12_publications',
            '>=', t, expr,
            f'latest SI% of float is in the top {round((1-t)*100)}% of its own last 12 '
            'publication points', f'si_pct_l12_ge{t}',
            recipe=recipe, block=block, source=source, extra_feature=dict(lookback=12)))
    expr = 'finra_si_tercile_state_change_v1()'
    rows.append(_row(
        'si_tercile_state_change', expr, 'boolean', 'si_tercile_crossed_third_or_two_thirds',
        '=', 1, expr,
        'SI% tercile (percentile within the prior 11 publication points) crossed the 1/3 '
        'or 2/3 boundary between the last two usable publications',
        'si_tercile_change', recipe=recipe, block=block, source=source))
    return rows


def sector_definitions():
    """C26 sector membership from SEC SIC/GICS records filed <= D-1."""
    rows = []
    recipe, block, source = RECIPE_SECTOR, BLOCK_SECTOR, 'C26'
    for t in (20, 60):
        expr = 'sec_sector_membership_days_v1()'
        rows.append(_row(
            'sector_membership_days', expr, 'integer_count',
            'trading_days_current_sector_code_in_force',
            '>=', t, expr,
            f'current sector code has been in force for >= {t} trading days '
            '(single usable publication = the code is new: answers 0)', f'sector_days_ge{t}',
            recipe=recipe, block=block, source=source))
    for t in (5, 20):
        expr = f'sec_sector_changed_within_v1(within={t})'
        rows.append(_row(
            'sector_state_change', expr, 'boolean',
            f'sector_code_changed_within_last_{t}_sessions',
            '=', 1, expr,
            f'the sector code most recently changed within the last {t} sessions',
            f'sector_changed_w{t}', recipe=recipe, block=block, source=source,
            extra_feature=dict(within=t)))
    expr = 'sec_sector_change_count_v1(window=252)'
    rows.append(_row(
        'sector_change_count', expr, 'integer_count', 'sector_code_transitions_last_252_sessions',
        '>=', 1, expr,
        '>= 1 sector-code transition among usable publications in the last 252 sessions',
        'sector_changes_ge1', recipe=recipe, block=block, source=source,
        extra_feature=dict(window=252)))
    return rows


def shares_definitions():
    """I193 shares outstanding (SEC dei): change % between latest two usable
    records; large jumps are the split/dilution event facet."""
    rows = []
    recipe, block, source = RECIPE_SHARES, BLOCK_SHARES, 'I193'
    for t in (1, 40):
        expr = 'sec_shares_change_pct_v1()'
        rows.append(_row(
            'shares_change_pct', expr, 'continuous',
            'shares_outstanding_change_pct_latest_two_records',
            '>=', t, expr,
            f'shares outstanding changed >= +{t}% between the latest two usable dei records',
            f'shares_chg_ge{t}', recipe=recipe, block=block, source=source))
    expr = 'sec_shares_out_event_within_v1(threshold_pct=40)'
    rows.append(_row(
        'shares_split_event', expr, 'boolean', 'large_shares_jump_between_latest_two_records',
        '=', 1, expr,
        'a >= 40% shares-outstanding change (split/dilution scale) occurred between the '
        'latest two usable dei records',
        'shares_jump_40', recipe=recipe, block=block, source=source,
        extra_feature=dict(threshold_pct=40)))
    return rows


def dividend_definitions():
    """I196 dividends: ex-dividend recency and per-share change."""
    rows = []
    recipe, block, source = RECIPE_DIV, BLOCK_DIV, 'I196'
    for t in (30, 60, 90):
        expr = 'sec_div_days_since_ex_v1()'
        rows.append(_row(
            'div_days_since_ex', expr, 'integer_count', 'trading_days_since_latest_ex_dividend',
            '<=', t, expr,
            f'latest usable ex-dividend date is <= {t} trading days before D (event day = 0)',
            f'days_since_ex_le{t}', recipe=recipe, block=block, source=source))
    expr = 'sec_div_dps_changed_v1()'
    rows.append(_row(
        'div_dps_changed', expr, 'boolean', 'dps_changed_vs_previous_record',
        '=', 1, expr,
        'dividend per share of the latest usable record differs from the previous usable record',
        'dps_changed', recipe=recipe, block=block, source=source))
    return rows


def xbrl_definitions():
    """I192 SEC XBRL fundamentals: ratio/growth facets over fact points already
    PIT-selected by world_sec_facts (filed strictly < D, statuses propagate;
    non-VALUE -> NOT_EVALUABLE, never partially imputed). Price input = raw
    D-1 close, never adjusted. Only 3,996/8,439 tickers have CIK coverage ->
    outside coverage is NE, never NO."""
    rows = []
    recipe, block, source = RECIPE_XBRL, BLOCK_XBRL, 'I192'
    for t in (10, 15, 20, 30):
        expr = 'sec_xbrl_pe_v1()'
        rows.append(_row(
            'xbrl_pe', expr, 'continuous', 'price_over_diluted_eps_ttm',
            '>=', t, expr,
            f'P/E (raw D-1 close / diluted EPS TTM) >= {t}; NE on non-positive EPS '
            'or any non-VALUE fact status', f'pe_ge{t}',
            recipe=recipe, block=block, source=source))
    for t in (1, 3, 5):
        expr = 'sec_xbrl_pb_v1()'
        rows.append(_row(
            'xbrl_pb', expr, 'continuous', 'price_over_book_value_per_share',
            '>=', t, expr,
            f'P/B (raw D-1 close / book value per share) >= {t}; NE on non-positive book '
            'value or any non-VALUE fact status', f'pb_ge{t}',
            recipe=recipe, block=block, source=source))
    for t in (0, 10):
        expr = 'sec_xbrl_revenue_growth_yoy_v1()'
        rows.append(_row(
            'xbrl_revenue_growth', expr, 'continuous', 'revenue_ttm_yoy_change_percent',
            '>=', t, expr,
            f'revenue (TTM) grew >= {t}% year over year; NE on zero/negative prior base '
            'or any non-VALUE fact status', f'rev_growth_ge{t}',
            recipe=recipe, block=block, source=source))
    expr = 'sec_xbrl_margin_expanded_yoy_v1()'
    rows.append(_row(
        'xbrl_margin_expanded', expr, 'boolean', 'net_margin_expanded_vs_prior_ttm',
        '=', 1, expr,
        'net margin (NI/revenue, TTM) of the current period exceeds the prior period',
        'margin_expanded', recipe=recipe, block=block, source=source))
    return rows


def short_volume_definitions():
    """I189 FINRA daily short volume: per-session short/total ratio facets."""
    rows = []
    recipe, block, source = RECIPE_FINRA, BLOCK_SHORTVOL, 'I189'
    for t in (0.45, 0.5, 0.55):
        expr = 'finra_short_ratio_v1()'
        rows.append(_row(
            'short_volume_ratio', expr, 'continuous', 'short_volume_over_total_volume_latest_session',
            '>=', t, expr,
            f'latest usable session short/total volume ratio >= {t}', f'ratio_ge{t}',
            recipe=recipe, block=block, source=source))
    for window in (5,):
        for t in (0.45, 0.5, 0.55):
            expr = f'finra_short_ratio_mean_v1(window={window})'
            rows.append(_row(
                'short_volume_ratio_mean', expr, 'continuous',
                f'mean_short_ratio_last_{window}_sessions',
                '>=', t, expr,
                f'mean short/total ratio over the last {window} usable sessions >= {t}',
                f'mean_w{window}_ge{t}',
                recipe=recipe, block=block, source=source, extra_feature=dict(window=window)))
    for lookback in (60,):
        for t in (0.8, 0.9):
            expr = f'finra_short_ratio_percentile_v1(lookback={lookback})'
            rows.append(_row(
                'short_volume_ratio_percentile', expr, 'continuous',
                f'short_ratio_percentile_last_{lookback}_sessions',
                '>=', t, expr,
                f'latest short ratio is in the top {round((1-t)*100)}% of its own last '
                f'{lookback} usable sessions (percentile in [0,1])',
                f'pct_l{lookback}_ge{t}',
                recipe=recipe, block=block, source=source, extra_feature=dict(lookback=lookback)))
    expr = 'finra_short_ratio_cross_median_v1(lookback=60,within=5)'
    rows.append(_row(
        'short_volume_ratio_state_change', expr, 'boolean',
        'short_ratio_crossed_above_60session_median_within_5_sessions',
        '=', 1, expr,
        'short/total ratio crossed above the median of the prior 60 usable sessions at any '
        'point within the last 5 sessions',
        'cross_median_60_within5', recipe=recipe, block=block, source=source,
        extra_feature=dict(lookback=60, within=5)))
    return rows


def cboe_definitions():
    """I201 CBOE market-wide options: put/call ratios (raw counts, equity and
    total groups), era-split percentile, VIX level/term structure, SKEW."""
    rows = []
    recipe, block, source = RECIPE_CBOE, BLOCK_CBOE, 'I201'
    for group in ('equity', 'total'):
        for t in (0.7, 0.8, 0.9, 1.0):
            expr = f'cboe_put_call_volume_ratio_v1(group={group})'
            rows.append(_row(
                'cboe_pc_volume_ratio', expr, 'continuous',
                f'put_call_volume_ratio_latest_session_{group}',
                '>=', t, expr,
                f'latest usable session put/call VOLUME ratio ({group} group, raw counts) >= {t}',
                f'pc_vol_{group}_ge{t}',
                recipe=recipe, block=block, source=source, extra_feature=dict(group=group)))
    for t in (0.7, 0.9, 1.1):
        expr = 'cboe_put_call_oi_ratio_v1(group=equity)'
        rows.append(_row(
            'cboe_pc_oi_ratio', expr, 'continuous',
            'put_call_open_interest_ratio_latest_session_equity',
            '>=', t, expr,
            f'latest usable session put/call OPEN INTEREST ratio (equity group, raw counts) >= {t}',
            f'pc_oi_equity_ge{t}',
            recipe=recipe, block=block, source=source, extra_feature=dict(group='equity')))
    for lookback in (252,):
        for t in (0.8, 0.9):
            expr = f'cboe_pc_ratio_percentile_v1(lookback={lookback},group=equity)'
            rows.append(_row(
                'cboe_pc_ratio_percentile', expr, 'continuous',
                'pc_volume_ratio_percentile_current_era_only',
                '>=', t, expr,
                f'latest equity put/call volume ratio is in the top {round((1-t)*100)}% of its '
                f'own last {lookback} usable sessions WITHIN THE CURRENT CBOE ERA '
                '(never crosses the 2019-10-07 definition break or the post-2022 0DTE flag)',
                f'pc_pct_l{lookback}_ge{t}',
                recipe=recipe, block=block, source=source,
                extra_feature=dict(lookback=lookback, group='equity')))
    for t in (12, 20, 30):
        expr = 'vix_level_v1()'
        rows.append(_row(
            'vix_level', expr, 'continuous', 'vix_close_latest_session',
            '>=', t, expr,
            f'latest usable VIX close >= {t}', f'vix_ge{t}',
            recipe=recipe, block=block, source=source))
    for state in ('backwardation', 'contango'):
        expr = 'vix_term_structure_state_v1()'
        rows.append(_row(
            'vix_term_structure', expr, 'category_code', 'vix_vs_vix3m_state_fixed_set',
            '=', state, expr,
            f'VIX term structure state = {state} (contango: VIX < VIX3M; backwardation: '
            'VIX >= VIX3M; fixed two-outcome set)',
            f'term_{state}', recipe=recipe, block=block, source=source))
    for t in (120, 130, 140):
        expr = 'cboe_skew_v1()'
        rows.append(_row(
            'cboe_skew', expr, 'continuous', 'skew_index_latest_session',
            '>=', t, expr,
            f'latest usable CBOE SKEW index level >= {t}', f'skew_ge{t}',
            recipe=recipe, block=block, source=source))
    return rows


def build(root=ROOT):
    root = Path(root)
    rows = (form4_definitions() + analyst_definitions() + holdings13f_definitions()
            + short_interest_definitions() + sector_definitions() + shares_definitions()
            + dividend_definitions() + xbrl_definitions()
            + short_volume_definitions() + cboe_definitions())
    ids = [r['question_id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate question_id in SEC definitions')
    path = root / 'docs' / SEC_CSV
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(csv=SEC_CSV, csv_sha256=digest, rows=len(rows),
                  blocks=sorted({r['block'] for r in rows}),
                  facets=sorted({r['facet'] for r in rows}),
                  status='DEFINITIONS_ONLY_NO_ANSWERS')
    (root / 'docs' / SEC_REPORT).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(ROOT))
    args = parser.parse_args()
    print(json.dumps(build(args.root), indent=2))

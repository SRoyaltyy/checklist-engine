# WIRE50 V1 — Addendum A (add-only; written and committed BEFORE any result was computed)
Scope add from Grok Bot master coverage (Drive 1wGJORBFa-pm5Uj8ZHnbOpqgMnfQJAMLo): 19 master-list Options ideas PV-TF-411..429.
Raw data: DoltHub post-no-preference/options `volatility_history`, Drive vol_history_2020..2024.csv.gz (shas verified vs README v2: d3337de0…, f2249eb9…, ea344b21…, 7dc2c9ae…, 2e5044a7…). Fields: hv/iv current, week_ago, month_ago, year_high/low only (one IV tenor; no strikes, no volume, no OI).

## Master idea -> tested row
| master | variant | tested as |
|---|---|---|
| PV-TF-411 | IV rank | GK-OPX-IVR-HI (map row) |
| PV-TF-412 | IV rank | GK-OPX-IVR-LO (map row) |
| PV-TF-413 | IV30/HV20 | GK-OPX-IVHV-HI (map row; DoltHub IV/HV, not exactly IV30/HV20) |
| PV-TF-414 | IV30/HV20 | GK-OPX-IVHV-LO (map row) |
| PV-TF-415 | IV change | GK-OPX-IVCHG-UP (map row) |
| PV-TF-416 | IV change | GK-OPX-IVCHG-DN (map row) |
| PV-TF-417 | IV change | NEW TR-OPX-IVCHG1M-UP: iv_current/iv_month_ago−1 >= +0.25 ; TR-OPX-IVCHG1M-DN: <= −0.25 |
| PV-TF-421 | IV up, price up | NEW TR-OPX-IVUP-PXUP: iv_current/iv_week_ago−1 >= +0.10 AND close(D)/close(5 sessions before D)−1 > 0 |
| PV-TF-428 | Implied move vs ATR | NEW TR-OPX-IMPMV-HI: (iv_current/sqrt(252)) / ATR20%(D) > 1.5 ; TR-OPX-IMPMV-LO: < 0.67 |
| PV-TF-418 | IV term structure | BLOCKED: volatility_history has one IV tenor; term structure needs DoltHub option_chain per-expiry IV, not pulled/built for 2020–24 |
| PV-TF-419 | 25d skew | BLOCKED: needs per-strike IV/delta (option_chain); not built for 2020–24 tonight |
| PV-TF-420 | Call skew | BLOCKED: same as 419 |
| PV-TF-422/423 | Put/call volume ratio | BLOCKED: no free 2020–24 per-stock option volume source (DoltHub has none) |
| PV-TF-424 | Put/call OI ratio | BLOCKED: no free 2020–24 open-interest history |
| PV-TF-425 | Option volume vs avg | BLOCKED: no free option volume history |
| PV-TF-426 | OI change | BLOCKED: no free OI history |
| PV-TF-427 | Unusual call volume | BLOCKED: no free option volume history |
| PV-TF-429 | Paid OI/PCR history | BLOCKED: paid data, out of scope |

## Point-in-time for NEW rows
Raw row dated D (EOD) -> entry at OPEN of the first price session strictly after D (fresh readings only; no carry). ATR20% and 5-day return use bars <= D. All other rules (exits E1/E2, 30bp each way, buyable v2 on cases and control, runs=one trade, discover 2020–22 / confirm 2023–24, pass bar) exactly as RULES_V1.md. Test count becomes (50 + 5 new) rows × 2 exits = 110.

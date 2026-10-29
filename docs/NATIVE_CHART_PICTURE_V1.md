# Pinned native chart-picture component

Authority is James's exact definition block at
`11a01175af8fc7dd0a842ac823d2b0835e556d8b` in METHODOLOGY. The completed
price diagnostic1044-column registry has none of these nine required fields.
This component supplies their calculations as a separate layer. It changes no
original price recipe, payload, question tree, registered cutoff grid or type.

| Default field | Pinned calculation |
|---|---|
| cp_mid_slope_up | BB20 middle(t) − middle(t−5) > 0 |
| cp_gr_body20 | sum green absolute bodies / sum red absolute bodies,20 bars, >=0.9 |
| cp_pctB | (close−BB lower)/(BB upper−lower), >=0.12 |
| cp_dip_atr | (20-bar high−close)/Wilder ATR14, <=4.2 |
| cp_days_since_h20 | age of most recent tied20-bar high in5..18 inclusive |
| cp_dd_vs_run | (high−minimum low since that high)/(high−minimum low in20 bars BEFORE that high), >=0.5 |
| cp_redgreen_vol10 | red volume / green volume,10 bars, >1; warning only |
| cp_hard_all | first six tags all yes; unavailable conditions cannot pass |
| lower_highs10 | count of High < preceding High over10 native bars |

Green means close>open, red close<open, and doji neither. Bodies are absolute
price differences. True range is max(H−L,abs(H−previous close),abs(L−previous
close)); the first observed bar is H−L even with pre-IPO grid rows preceding it.
Wilder ATR seeds with the first N true ranges and uses the Wilder recurrence.
An internal unknown true range leaves the recursive state unknown; it is not
reseeded or approximated across a data gap. Finite-window metrics become
available only when their actual input windows and the minimum60 complete
native bars are known. Warmup values remain blank; `hard_gate_mask` returns
false for a blank hard gate.

Bollinger uses population variance(ddof=0); equal bands make percent-B blank.
High ties select the most recent bar. The prior-low interval excludes the
high bar, while the drawdown interval includes that bar through t. Nonpositive
run is blank. Positive/zero ratios use the default `_inf` policy; zero/zero
stays blank. `_blank` variants remain separately labelled, including the hard
composite. Unadorned pinned names alias the default policy. Volume warning is
excluded from both hard composites.

`chart_metrics` exposes the underlying float64 values for the existing named
test variables; `chart_tags` applies the explicit settings. `ChartSettings`
contains only the named numbers in the pin. No new ranges/grid are declared.
Nondefault exports must have distinct registered variant identities; a default
name alone cannot prove a full variable sweep. The native output has39 fields,
including raw inputs to the tags and explicit aliases. Alias metadata prevents
counting repeated formulas as extra questions; no question is generated here.

The native adapter uses the existing actual-session grids, all1d..21d plus
monthly. It retains unavailable intervals before lookbacks, rejects mixed
literal tickers, excludes the complete day-D row, and requires source candle
end < actual availability <= query D. Invalid OHLCV is unavailable and counted.
The original source frame is unchanged.

Local validation:48 focused chart/native/proof checks passed53.89s; the two
new literal-symbol cases passed separately1.35s, and schema/alias binding
checks passed1.59s. The GitHub request uses the original MAN/MNTS/EYE+SPY
raw bytes, all22 grids, exact persisted reconstruction and two independent
raw/calendar cutoff rebuilds. It measures defaults only. Full-universe
coverage, every registered setting, v3/history quality, comprehensive leaks,
historical tradeability, portable exact reconstruction and full dependency
closure remain open. No checkbox or scoring acceptance is claimed.

## Actual default proof

Run40850036315 at1f1e4f3 passed50 Linux tests9.41s and measured all88 native
frames(MAN/MNTS/EYE/SPY ×22). Exact persisted reconstruction and176 independent
raw/calendar cutoff rebuilds reported zero mismatches on every field.
The report covers5,339,568 numeric cells,2,924,895 known, and15,085,201B of
temporary exact references. Each input has34,228 native grid rows; these
include pre2020 and pre-IPO rows, not a whole-universe2020–26 fill rate. No
invalid OHLCV rows occurred in any sample.

The public506,263B report has SHA256
`def60dc27f1f6cff39add198d3cf439aaf94b4ae6435b5cd80024cfcde72276e`.
`CHART_NATIVE_PUBLIC_READBACK_V1.json` authenticates the public bytes, all14
code hashes, every receipt/input/schema and eight explicit aliases. Native
reference files were temporary runner data: this public readback inspects
the bound code/receipts rather than independently downloading or regenerating
their full numeric contents. Defaults only; full registered-grid coverage,
all8,447 names and comprehensive quality/PIT/cap gates are not proved here.

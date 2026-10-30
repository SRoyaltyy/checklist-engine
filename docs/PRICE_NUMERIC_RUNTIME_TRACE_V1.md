# Numeric runtime trace: diagnostic plan

The part172 replay41059646552 rebuilt all50 names but found166 changed known
answer cells across8 names. Independent FEIM bit readback identifies log-return
skew, Hurst and historical-volatility rising predicates. The cause is not yet
established. This diagnostic preserves the current failed gate and original bits.

The predeclared targets are all8 mismatch names(FEIM,HHS,JHI,NKTR,OCGN,ABX,AMTD,
CATO), plus two zero-difference controls(DJCO from retained legacy outputs,BPOP
from guarded outputs). Prepare authenticates the original/current raw source,
reference composition, final replay report, both packet bodies and registry,
then retains every166 changed question/row pair. Controls use fixed query row217
and the same three predeclared skew/Hurst/volatility questions.

Stock jobs are capped at four concurrent runners. Each starts three fresh
processes with the same authenticated guarded13-file source, raw inputs and
prefix-check schedule:

1. Baseline A, with exact numeric prefix checks at the affected native-candle
   position and two candles later. This isolates statistics on identical native
   OHLCV prefixes; it is not a full raw/calendar/question/PIT rebuild proof.
2. Baseline B, a fresh process with the same CPU-dispatch configuration and workload.
3. A diagnostic process disabling NumPy's available optional CPU dispatch
   features through its process-local environment. This is an experiment, not
   a production arithmetic, stored-value or recipe change.

The worker imports only the bound native-candle and bar-statistics modules. It
observes the existing log ufunc without changing its operands/results, records
ratio/log bit hashes and input alignment/strides, exact field arrays and point
bits, CPU/runtime/module hashes, all selector answer codes, and full-vs-prefix
differences. Both numerical value and known/missing differences are explicit;
no epsilon, decimal rounding or tolerance is used. Log-return prefix differences
are reported separately from downstream statistic differences.

Full numeric arrays stay in the Actions evidence artifact, with their hashes in
the public trace. The final report can establish counterexamples or narrow the
runtime hypothesis; it cannot certify all stocks, settings, timeframes or full
world/scoring readiness. No profile will be selected merely to imitate retained
bits. Any later production correction needs an explicit version and its complete
source, quality, prefix/eligibility and exact-storage proofs.

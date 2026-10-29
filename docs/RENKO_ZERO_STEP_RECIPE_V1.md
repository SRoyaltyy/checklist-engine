# Versioned Renko zero-step recipe proof

The frozen float64 recipe at `7dcaa48680daeac9a6025c09f9e4d138f5fcbda5`
can enter a nonterminating Renko loop. The authenticated EQLT source reaches
2021-01-04 with close and last brick both37, but a positive ATR smaller than
half the floating-point spacing at37. Adding/subtracting the box leaves the
brick unchanged, so the original true loop condition never becomes false.
The measured source and exact trace are in `RENKO_EQLT_INPUT_DIAGNOSIS_V1.json`.

This separate recipe inserts a guard in each of those two loops. When the
next brick is unchanged and finite and close equals that brick, no price
distance remains: leave the state and counter unchanged and finish that loop.
A nonzero distance with a nonadvancing brick raises an explicit error. No
epsilon, rounded jump, float32 cast, parameter range or new question is added.
Any terminating old execution never reaches the new guard, so its original
arithmetic and counter updates execute unchanged.

`ci/renko_recipe.py` derives this recipe only from the authenticated original
13-file snapshot. Only `facets_world.py` changes. The resulting fingerprint is
`40ea182cf6fb377d12710ccbfccd7ab2b5f17b9e6e6f07df08cf4399956ca0c3`;
`recipes/renko_zero_step_v1/RECIPE.json` records all13 file hashes. The full
override is stored there for review. The main-level module and all live build
requests retain their original behavior.

The precommitted proof request first regenerates all1044 numeric columns on
all22 native grids for MAN, MNTS and EYE, comparing every float64 and date bit
with the immutable earlier recomputation receipts. Those receipts came from
an independent comparison against the retained numeric arrays. SPY is built
with both the old and candidate recipes on the same full numeric grid. Only
after all comparisons pass does a separate worker try EQLT, followed by the
existing packed-answer worker and encoder for its68904 diagnostic questions.
Every worker has a900-second bound and starts in a clean process with the
bound recipe first on its import path. Original runtime package versions are
pinned. All inputs are already published and individually SHA-256 bound.

The proof publishes a new release with the report, recipe hashes, exact
override, authenticated EQLT bars, diagnostic registry and answer payload.
Errors remain explicit in an incomplete report. Success permits reviewing
this one new recipe/sample; it does not replace any published values, recover
the full universe, prove full world/question/PIT coverage, or satisfy the
100GB dependency-closure gate. Scoring remains closed. No new run of the
protected world build or existing add-on is requested.

Actual proof40834508707 at `c803c62` passed. Both old and candidate recipes
matched all51,008,796 historical stock numeric cells/date bits; SPY matched
32,724,180 cells per recipe. EQLT completed12,260,736 numeric cells in6.05s,
then the packed diagnostic in101.17s. Independent public readback authenticated
all six assets15,396,634B and every bitplane/code/provenance binding in all550
answer chunks:117,963,648 cells, including18,019,282 missing. The4,234 constant
and4,973 empty questions remain explicit; this diagnostic does not pass P3b.
See `RENKO_ZERO_STEP_PROOF_V1.json` and `RENKO_ZERO_STEP_PUBLIC_READBACK_V1.json`.

The earlier40802810949 stock hash mismatches remain unresolved and archived
in `RENKO_ZERO_STEP_INCOMPLETE_PROOF_V1.json`. The second run compared both
recipes against those same historical receipts and passed without a recipe,
input, arithmetic, precision or equality change. This establishes exact
reproduction on that runner; cross-runtime/portable exact recomputation remains
unproven. Existing published numeric results are never replaced on this basis.

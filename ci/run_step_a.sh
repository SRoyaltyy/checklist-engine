#!/usr/bin/env bash
# Run Step A on the runner with seamless resume. Seeds chunks/ from the results branch
# (scores+errors) and from answers_*.npz already uploaded to the release, so a run cut off
# by the 6h job limit (or anything else) continues where the last one stopped.
# A push loop checkpoints every finished piece while the engine runs.
set -uo pipefail
OUT="$RUNNER_TEMP/out"; CH="$OUT/chunks"; DATA="$RUNNER_TEMP/data"; TMP="$RUNNER_TEMP/tmp"
mkdir -p "$CH" "$TMP"
RESULTS_BRANCH="${RESULTS_BRANCH:-results/step-a-2020-22}"

echo "== seed chunks from $RESULTS_BRANCH"
git fetch -q origin "$RESULTS_BRANCH"
for f in $(git ls-tree --name-only "origin/$RESULTS_BRANCH" step_a/ | grep -E '(scores|errors)_'); do
  git show "origin/$RESULTS_BRANCH:$f" > "$CH/$(basename "$f")" && echo "seeded $(basename "$f")"
done

echo "== seed answers npz from release assets"
for f in "$DATA"/answers_*.npz; do
  [ -e "$f" ] || continue
  base=$(basename "$f")
  # step_a skips a chunk only when BOTH scores and answers exist; scores seeding above pairs them
  cp "$f" "$CH/$base" && echo "seeded $base"
done

echo "== launch engine + checkpoint push loop"
CHECKLIST_DATA_DIR="$DATA" OUT_DIR="$OUT" TMPDIR="$TMP" SAVE_ANSWERS=1 \
  python3 -u step_a.py --workers 4 --chunk 400 > "$OUT/step_a.log" 2>&1 &
ENGINE=$!

# push loop: checkpoints pieces as they land, stops the engine before the job cap
python3 ci/push_loop.py --engine-pid "$ENGINE" --chunks "$CH" --deadline-min "${PUSH_DEADLINE_MIN:-320}" &
PUSHER=$!

wait "$ENGINE" 2>/dev/null; ENGINE_RC=$?
wait "$PUSHER" 2>/dev/null || true
echo "== engine rc=$ENGINE_RC; final checkpoint"
python3 ci/push_loop.py --chunks "$CH" --deadline-min 0 --once || true
tail -5 "$OUT/step_a.log" || true
# rc 0 = all chunks done; 143/137/255 = killed at deadline or by pusher (normal, resume next run)
case "$ENGINE_RC" in 0|143|137|255) exit 0 ;; *) exit "$ENGINE_RC" ;; esac

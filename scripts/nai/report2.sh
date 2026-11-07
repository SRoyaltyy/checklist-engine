set -uo pipefail
T='Venice: failed no-AI pipeline runs'
AUTH='Authorization: Bearer '"${GH_TOKEN:-}"
R=${GITHUB_REPOSITORY:-SRoyaltyy/checklist-engine}
OWNER=${R%%/*}
REPO=${R#*/}
API="https://api.github.com/repos/$OWNER/$REPO"
BR=${1:-venice/sec-options-pipelines}
ENC=$(printf '%s' "$BR" | sed 's|/|%2F|')
api() { curl -sS --max-time 25 -H "$AUTH" -H 'Accept: application/vnd.github+json' "$@"; }
stop() { echo "reporter: $1"; exit 0; }
RUNS=$(api "$API/actions/runs?branch=$ENC&status=failure&per_page=50") || stop 'runs query unreachable'
RID=$(printf '%s' "$RUNS" | jq -r '(.workflow_runs // []) | map(select((.name // "") | test("nai-sec-|nai-occ-oi-daily"))) | .[0].id // empty' 2>/dev/null)
[ -n "$RID" ] || stop 'no matching failed run'
ISSUES=$(api "$API/issues?state=open&per_page=100") || stop 'issue lookup unreachable'
N=$(printf '%s' "$ISSUES" | jq -r --arg t "$T" '(. // []) | map(select((.title // "") == $t)) | .[0].number // empty' 2>/dev/null)
[ -n "$N" ] || stop 'no tracking issue'
CMTS=$(api "$API/issues/$N/comments?per_page=100&sort=created&direction=desc") || stop 'comment lookup unreachable'
SEEN=$(printf '%s' "$CMTS" | jq -r --arg r "$RID" '(. // []) | map(select((.body // "") | contains($r))) | length' 2>/dev/null)
[ "${SEEN:-0}" = "0" ] || { echo "already reported $RID"; exit 0; }
api "$API/actions/runs/$RID" > /tmp/run.json || stop 'run read failed'
api "$API/actions/runs/$RID/jobs" > /tmp/jobs.json || stop 'jobs read failed'
NAME=$(jq -r '.name // "unknown"' /tmp/run.json 2>/dev/null)
URL=$(jq -r '.html_url // ""' /tmp/run.json 2>/dev/null)
JOB=$(jq -r '(.jobs // []) | .[0].name // "n/a"' /tmp/jobs.json 2>/dev/null)
STEP=$(jq -r '[(.jobs // []) | .[0].steps // [] | .[] | select(.conclusion == "failure") | .name] | join(", ")' /tmp/jobs.json 2>/dev/null)
[ -n "${STEP:-}" ] || STEP='n/a'
: > /tmp/tail.txt
curl -sSL --max-time 60 -H "$AUTH" "$API/actions/runs/$RID/logs" -o /tmp/logs.zip || true
if [ -s /tmp/logs.zip ]; then
unzip -o /tmp/logs.zip -d /tmp/l >/dev/null 2>&1 || true
find /tmp/l -type f -exec cat {} + 2>/dev/null | tail -c 1500 > /tmp/tail.txt || true
fi
BODY=$(printf 'Run [%s %s](%s) - failure\n\nFailing job: %s\nFailing step: %s\n\n%s\n\nPosted automatically.' "${NAME:-unknown}" "$RID" "${URL:-}" "$JOB" "$STEP" "$(cat /tmp/tail.txt)")
jq -nc --arg b "$BODY" '{body:$b}' > /tmp/c.json || stop 'body encode failed'
OUT=$(api -X POST -H 'Content-Type: application/json' -d @/tmp/c.json "$API/issues/$N/comments") || stop 'comment post failed'
printf '%s' "$OUT" | jq -r '.html_url // "posted"' 2>/dev/null
exit 0

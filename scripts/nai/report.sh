#!/usr/bin/env bash
set -euo pipefail
RID=${1:-}
OWNER=$(printf '%s' "$GITHUB_REPOSITORY" | cut -d/ -f1)
REPO=$(printf '%s' "$GITHUB_REPOSITORY" | cut -d/ -f2)
API="https://api.github.com/repos/$OWNER/$REPO"
AUTH='Authorization: Bearer '"$GH_TOKEN"
T='Venice: failed no-AI pipeline runs'
curl -sS -H "$AUTH" "$API/actions/runs/$RID" -o /tmp/run.json
curl -sS -H "$AUTH" "$API/actions/runs/$RID/jobs" -o /tmp/jobs.json
curl -sSL -H "$AUTH" "$API/actions/runs/$RID/logs" -o /tmp/logs.zip || true
unzip -o /tmp/logs.zip -d /tmp/l >/dev/null 2>&1 || true
find /tmp/l -type f -exec cat {} + 2>/dev/null | tail -c 1500 > /tmp/tail.txt || true
N=$(curl -sS -H "$AUTH" "$API/issues?state=open&per_page=100" | jq -r --arg t "$T" '[.[]|select(.title==$t)][0].number // empty')
if [ -z "$N" ]; then echo 'no tracking issue'; exit 1; fi
SEEN=$(curl -sS -H "$AUTH" "$API/issues/$N/comments?per_page=100" | jq -r --arg r "$RID" '[.[]|select(.body|contains($r))]|length')
if [ "$SEEN" != "0" ]; then echo "already reported $RID"; exit 0; fi
BODY=$(jq -rn --slurpfile run /tmp/run.json --slurpfile jobs /tmp/jobs.json --rawfile tail /tmp/tail.txt '"Run [" + ($run[0].name) + " " + ($run[0].id|tostring) + "](" + $run[0].html_url + ") - " + ($run[0].conclusion // "unknown") + "\n\nFailing job: " + (($jobs[0].jobs[0].name) // "n/a") + "\nFailing step: " + ((($jobs[0].jobs[0].steps[]|select(.conclusion=="failure")|.name)) // "n/a") + "\n\n" + $tail + "\n\nPosted automatically. This is the retired nai-verdict workflow still firing on every push: its python collector dies instantly and the commit step is skipped, so the run reports nothing."')
jq -nc --arg b "$BODY" '{body:$b}' > /tmp/c.json
curl -sS -X POST -H "$AUTH" -H 'Content-Type: application/json' -d @/tmp/c.json "$API/issues/$N/comments" | jq -r .html_url

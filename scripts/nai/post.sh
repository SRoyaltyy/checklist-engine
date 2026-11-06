#!/usr/bin/env bash
set -euo pipefail
T='Venice: failed no-AI pipeline runs'
AUTH='Authorization: Bearer '"$GH_TOKEN"
N=$(curl -sS -H "$AUTH" "$API/issues?state=open&per_page=100" | jq -r --arg t "$T" '[.[]|select(.title==$t)][0].number // empty')
if [ -z "$N" ]; then
N=$(curl -sS -X POST -H "$AUTH" -H 'Content-Type: application/json' -d "$(jq -nc --arg t "$T" '{title:$t,body:"Automated record of failed no-AI pipeline runs, posted by the wake bridge. GPT owns the fix; Venice only reports."}')" "$API/issues" | jq -r .number)
fi
BODY=$(jq -r '. as $r | "Run [" + .run.name + " " + (.run.id|tostring) + "](" + .run.html_url + ") - " + .run.conclusion + "\n\nFailing job: " + (.jobs[0].name // "n/a") + "\nFailing step: " + (.jobs[0].failed_steps[0] // "n/a") + "\n\n" + .log_tail[-1200:] + "\n\nPosted automatically. Evidence: agent/RESULT.json"' agent/RESULT.json)
jq -nc --arg b "$BODY" '{body:$b}' > /tmp/c.json
curl -sS -X POST -H "$AUTH" -H 'Content-Type: application/json' -d @/tmp/c.json "$API/issues/$N/comments" | jq -r .html_url

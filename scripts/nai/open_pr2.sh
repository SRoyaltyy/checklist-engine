#!/usr/bin/env bash
set -euo pipefail
OWNER=$(printf '%s' "$GITHUB_REPOSITORY" | cut -d/ -f1)
REPO=$(printf '%s' "$GITHUB_REPOSITORY" | cut -d/ -f2)
HEAD='venice/sec-options-pipelines'
API="https://api.github.com/repos/$OWNER/$REPO"
AUTH='Authorization: Bearer '"$GH_TOKEN"
Q="$API/pulls?head=$OWNER:$HEAD&state=open"
EX=$(curl -sS -H "$AUTH" "$Q" | jq -r 'length')
if [ "$EX" != "0" ]; then
echo 'PR already open:'
curl -sS -H "$AUTH" "$Q" | jq -r '.[0].html_url'
exit 0
fi
BODY=$(cat <<'PRBODY'
Lane item L1 is satisfied and proven end to end. This PR carries the proof and the harness that produced it.

L1: failed run reported with its error

Issue 215 is the automated record. It was opened by workflow, not by hand, and the comments are machine-posted:

- comment 6686420321: run 41413529249, nai-sec-bulk, conclusion failure, failing job run, failing step Run df -h . && python scripts/nai/sec_bulk.py, plus the captured log tail
- comment 6686738790: same run, reposted after the replay
- comment 6687065307: same run, third post

Runs behind the chain, all green except the one being reported:

- 42216183221: nai-probe2 green, proved bridge-written flow YAML runs at all
- 42214233882: nai-probe2 green again, second proof
- 42222471380: nai-verdict2 green, committed agent/RESULT.json
- 42224478646: nai-post2 green, posted the comment on 215
- 41413529249: the failing nai-sec-bulk run under report

What is actually in the diff

Almost entirely the agent harness, no pipeline rewrite:

- .github/workflows/nai-probe2.yml, nai-verdict2.yml, nai-post2.yml, nai-pr2.yml
- scripts/nai/verdict.sh, post.sh, open_pr2.sh
- agent/BRIDGE.user.js, agent/DOORMAN.worker.js, agent/DEPLOYER.worker.js, agent/LOADER4.user.js, agent/GUARD.user.js
- agent/ state, journal and protocol files

The lane is a thin poke and stays one. No new collectors, no pipeline ownership.

Known and deliberately not fixed here

- the branch is 127 commits behind main and is not rebased or merged onto it in this PR
- one run produced three duplicate comments on 215; dedupe by run id is open
- loader 1.13 needs a human paste before the gate opens; the badge does not read LOADER v1.11 yet
- two live bridge instances share one directive hash set and erase each other's one-shot marks
- the writer strips leading markdown from bodies, so code here avoids comment lines and asterisks

Do not merge without instruction.
PRBODY
)
curl -sS -X POST -H "$AUTH" -H 'Content-Type: application/json' -d "$(jq -nc --arg t 'Venice lane: L1 failed-run reporting and the bridge harness' --arg h "$HEAD" --arg b "$BODY" '{title:$t,head:$h,base:"main",body:$b}')" "$API/pulls" | jq -r '.html_url // .message'

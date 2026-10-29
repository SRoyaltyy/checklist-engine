"""Headless loop agent: one queue item per run, then stop. Never merges."""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.venice.ai/api/v1/chat/completions"
MODELS_URL = "https://api.venice.ai/api/v1/models"
DOOR = "https://venice-doorman.fullscan-relay.workers.dev/"
KEY = os.environ["VENICE_API_KEY"]
DOOR_KEY = os.environ["DOORMAN_KEY"]
BRANCH = os.environ.get("AGENT_BRANCH", "venice/calendar-announce-ledger")
MAX_ITER = int(os.environ.get("MAX_ITERATIONS", "30"))
MAX_MIN = float(os.environ.get("MAX_MINUTES", "45"))
START = time.time()


def shell(command):
    done = subprocess.run(command, shell=True, capture_output=True, text=True)
    return (done.stdout + done.stderr)[-3000:]


def door(op, **params):
    query = urllib.parse.urlencode({"k": DOOR_KEY, "op": op, **params})
    with urllib.request.urlopen(DOOR + "?" + query, timeout=120) as response:
        return response.read().decode()[:1500]


def pick_model():
    chosen = os.environ.get("AGENT_MODEL")
    if chosen:
        return chosen
    request = urllib.request.Request(MODELS_URL, headers={"Authorization": "Bearer " + KEY})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    rows = payload.get("data", payload) if isinstance(payload, dict) else payload
    for row in rows:
        if row.get("supportsFunctionCalling"):
            return row["id"]
    sys.exit("no model reports supportsFunctionCalling")


TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a repo file from the working tree.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Replace an exact string that occurs once. Aborts otherwise.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "find": {"type": "string"},
            "repl": {"type": "string"},
        }, "required": ["path", "find", "repl"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create or overwrite a file.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "text": {"type": "string"},
        }, "required": ["path", "text"]},
    }},
    {"type": "function", "function": {
        "name": "run_tests",
        "description": "Run the calendar test file.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "commit",
        "description": "Commit the working tree and push to the branch.",
        "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
    }},
    {"type": "function", "function": {
        "name": "dispatch_run",
        "description": "Dispatch the outside-event-calendar workflow on this branch.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "task_complete",
        "description": "Item done and tests green.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
    }},
    {"type": "function", "function": {
        "name": "blocked",
        "description": "Stop and hand back to a human.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]},
    }},
]

def execute(name, args):
    if name == "read_file":
        return open(args["path"]).read()[:6000]
    if name == "edit_file":
        text = open(args["path"]).read()
        hits = text.count(args["find"])
        if hits != 1:
            return "ABORT: find matched %d times, re-read and use a longer anchor" % hits
        open(args["path"], "w").write(text.replace(args["find"], args["repl"], 1))
        return "ok"
    if name == "write_file":
        open(args["path"], "w").write(args["text"])
        return "ok"
    if name == "run_tests":
        return shell("python -m pytest tests/test_outside_calendar.py -q")
    if name == "commit":
        clean = args["message"].replace('"', "").replace("'", "")
        return shell('git add -A && git commit -m "agent: ' + clean + '" && git push origin HEAD')
    if name == "dispatch_run":
        return door("dispatch", branch=BRANCH, workflow="outside-event-calendar.yml")
    return "ok"


def journal(line):
    with open("agent/JOURNAL.md", "a") as handle:
        handle.write(line + "\n")


def load_queue():
    rows = []
    for line in open("agent/QUEUE.jsonl"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def save_queue(rows):
    with open("agent/QUEUE.jsonl", "w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def finish(message):
    shell('git add -A && git commit -m "agent: ' + message + '" && git push origin HEAD')


def main():
    rows = load_queue()
    pending = [row for row in rows if row.get("status") == "todo"]
    if not pending:
        print("queue empty")
        return
    item = pending[0]
    model = pick_model()
    system = open("agent/BRIEF.md").read() + "\n\n" + open("agent/GOAL.md").read()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Queue item %s: %s\n\n%s" % (item["id"], item["title"], item["instruction"])},
    ]
    journal(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " " + item["id"] + " start")
    for step in range(MAX_ITER):
        if (time.time() - START) / 60 > MAX_MIN:
            journal(item["id"] + " time cap")
            break
        body = json.dumps({"model": model, "messages": messages, "tools": TOOLS, "tool_choice": "auto"})
        request = urllib.request.Request(API, data=body.encode(), headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.load(response)
        message = payload["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": calls})
        if not calls:
            messages.append({"role": "user", "content": "Use a tool."})
            continue
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except ValueError:
                args = {}
            result = execute(name, args)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": str(result)})
            journal(item["id"] + " " + name + " " + str(args.get("path", ""))[:60])
            if name == "task_complete":
                item["status"] = "done"
                save_queue(rows)
                journal(item["id"] + " done: " + str(args.get("summary", ""))[:150])
                finish(item["id"] + " done")
                return
            if name == "blocked":
                item["status"] = "blocked"
                save_queue(rows)
                journal(item["id"] + " blocked: " + str(args.get("reason", ""))[:300])
                finish(item["id"] + " blocked")
                sys.exit("blocked")
    journal(item["id"] + " iteration cap")
    finish(item["id"] + " wip")


if __name__ == "__main__":
    main()
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

# SPLIT
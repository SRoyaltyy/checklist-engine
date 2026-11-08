"""Deterministic, read-only inventory of configured SEC/options workflow triggers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

SCHEMA_VERSION = 1

_FAMILIES = (
    re.compile(r"^nai[_-]sec[_-].*\.ya?ml$"),
    re.compile(r"^nai[_-]occ[_-]oi[_-]daily\.ya?ml$"),
)


class AuditError(Exception):
    """A selected workflow source is not a valid inventory entry."""


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys."""


def _construct_mapping(loader, node, deep=False):
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(None, None, "expected a mapping node", node.start_mark)
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(None, None, "unhashable mapping key", key_node.start_mark) from exc
        if key in mapping:
            raise yaml.constructor.ConstructorError(None, None, "duplicate mapping key: %r" % (key,), key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _is_selected(name):
    return any(pattern.match(name) for pattern in _FAMILIES)


def _yaml_message(exc):
    parts = [str(p) for p in (getattr(exc, "context", None), getattr(exc, "problem", None)) if p]
    if parts:
        return "; ".join(parts)
    text = str(exc).strip().splitlines()
    return text[0] if text else exc.__class__.__name__


def _selected_paths(workflow_dir):
    try:
        root = Path(workflow_dir).resolve(strict=True)
    except OSError:
        return [], [{"path": ".", "message": "workflow directory does not exist"}]
    if not root.is_dir():
        return [], [{"path": ".", "message": "workflow directory is not a directory"}]
    try:
        entries = sorted(os.listdir(root))
    except OSError as exc:
        return [], [{"path": ".", "message": "cannot list workflow directory: %s" % (exc.strerror or exc,)}]
    paths = []
    errors = []
    for entry in entries:
        if not _is_selected(entry):
            continue
        path = root / entry
        if path.is_symlink():
            try:
                target = path.resolve(strict=True)
            except OSError:
                errors.append({"path": entry, "message": "symlink target is missing or unresolvable"})
                continue
            if target != root and root not in target.parents:
                errors.append({"path": entry, "message": "symlink resolves outside the workflow directory"})
                continue
        if not path.is_file():
            errors.append({"path": entry, "message": "selected source is not a regular file"})
            continue
        paths.append(path)
    return paths, errors


def _trigger(data):
    if "on" in data:
        return data["on"]
    if True in data:
        return data[True]
    return None


def _events(value):
    if isinstance(value, str):
        if not value.strip():
            raise AuditError("event name is empty")
        return [value]
    if isinstance(value, list):
        found = set()
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise AuditError("invalid event entry: %r" % (item,))
            found.add(item)
        if not found:
            raise AuditError("event list is empty")
        return sorted(found)
    if isinstance(value, dict):
        found = set()
        for key in value:
            if isinstance(key, bool) or not isinstance(key, str) or not key.strip():
                raise AuditError("invalid event key: %r" % (key,))
            found.add(key)
        if not found:
            raise AuditError("event mapping is empty")
        return sorted(found)
    raise AuditError("unsupported on trigger type: %s" % (type(value).__name__,))


def _schedules(value):
    if not isinstance(value, dict) or "schedule" not in value:
        return []
    raw = value["schedule"]
    if not isinstance(raw, list):
        raise AuditError("schedule must be a sequence of mappings")
    if not raw:
        raise AuditError("schedule sequence is empty")
    result = []
    for item in raw:
        if not isinstance(item, dict):
            raise AuditError("schedule entry must be a mapping")
        if "cron" not in item:
            raise AuditError("schedule entry is missing cron")
        cron = item["cron"]
        if not isinstance(cron, str) or not cron.strip():
            raise AuditError("schedule cron must be a nonempty string")
        timezone = item.get("timezone", "UTC")
        if not isinstance(timezone, str) or not timezone.strip():
            raise AuditError("schedule timezone must be a nonempty string")
        result.append({"cron": cron, "timezone": timezone})
    return result


def _name(data, filename):
    if "name" not in data:
        return filename
    name = data["name"]
    if not isinstance(name, str) or not name.strip():
        raise AuditError("workflow name must be a nonempty string")
    return name


def _audit_file(path):
    filename = path.name
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AuditError("cannot read file: %s" % (exc.strerror or exc,))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise AuditError("file is not valid UTF-8")
    try:
        data = yaml.load(text, Loader=_StrictLoader)
    except yaml.YAMLError as exc:
        raise AuditError("malformed YAML: %s" % (_yaml_message(exc),))
    if not isinstance(data, dict):
        raise AuditError("workflow document must be a mapping")
    trigger = _trigger(data)
    if trigger is None:
        raise AuditError("workflow has no on trigger")
    events = _events(trigger)
    schedules = _schedules(trigger)
    return {
        "path": filename,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "name": _name(data, filename),
        "events": events,
        "schedules": schedules,
    }


def audit_directory(workflow_dir):
    """Return a deterministic inventory report for SEC/options workflow sources."""
    paths, errors = _selected_paths(workflow_dir)
    workflows = []
    for path in paths:
        try:
            workflows.append(_audit_file(path))
        except AuditError as exc:
            errors.append({"path": path.name, "message": str(exc)})
    workflows.sort(key=lambda row: row["path"])
    errors.sort(key=lambda item: (item["path"], item["message"]))
    if not paths:
        errors.append({"path": ".", "message": "no SEC/options workflow sources selected"})
    status = "PASS" if workflows and not errors else "FAIL"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "workflows": workflows,
        "errors": errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic read-only SEC/options workflow trigger inventory.")
    parser.add_argument("--workflows", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-commit", default=None)
    args = parser.parse_args(argv)
    report = audit_directory(Path(args.workflows))
    if args.source_commit is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", args.source_commit):
            parser.error("--source-commit must be a 40-character hex SHA")
        report["source_commit"] = args.source_commit
    output = Path(args.output)
    if output.parent and not output.parent.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

"""Owner-supplied acceptance tests. Venice must not modify this file."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
MODULE = PROJECT / "agent/workflow_schedule_audit.py"

class WorkflowScheduleAuditAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("candidate_schedule_audit", MODULE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def audit(self):
        return self.module.audit_directory(self.root)

    def valid(self, report):
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["errors"], [])
        return report["workflows"]

    def test_selects_only_sec_and_occ_daily_families(self):
        self.put("nai_sec_bulk.yml", "name: SEC bulk\non: push\n")
        self.put("nai-occ-oi-daily.yaml", "on: [push, workflow_dispatch]\n")
        self.put("world-v2-code-ci.yml", "on: [push]\n")
        self.put("nai_daily_forward.yml", "on: [push]\n")
        rows = self.valid(self.audit())
        self.assertEqual([r["path"] for r in rows], ["nai-occ-oi-daily.yaml", "nai_sec_bulk.yml"])
        self.assertEqual(rows[0]["events"], ["push", "workflow_dispatch"])

    def test_plain_on_key_is_not_lost_to_yaml_boolean_coercion(self):
        self.put("nai_sec_bulk.yml", "name: SEC\non:\n  push:\n    branches: [main]\n  workflow_dispatch:\n  schedule:\n    - cron: '7 3 * * 1'\n")
        row = self.valid(self.audit())[0]
        self.assertEqual(row["events"], ["push", "schedule", "workflow_dispatch"])
        self.assertEqual(row["schedules"], [{"cron": "7 3 * * 1", "timezone": "UTC"}])

    def test_explicit_timezone_is_recorded_without_predicting_a_run(self):
        self.put("nai_occ_oi_daily.yml", "'on':\n  schedule:\n    - cron: '8 6 * * *'\n      timezone: Asia/Hong_Kong\n")
        row = self.valid(self.audit())[0]
        self.assertEqual(row["schedules"], [{"cron": "8 6 * * *", "timezone": "Asia/Hong_Kong"}])
        self.assertNotIn("missed", row)
        self.assertNotIn("next_run", row)

    def test_file_digest_matches_exact_source_bytes(self):
        path = self.put("nai_sec_form13f.yml", "on: workflow_dispatch\n")
        row = self.valid(self.audit())[0]
        self.assertEqual(row["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(row["name"], path.name)

    def test_repeated_and_different_root_runs_are_deterministic(self):
        text = "name: SEC\non: [workflow_dispatch, push]\n"
        self.put("nai_sec_bulk.yml", text)
        first = self.audit()
        self.assertEqual(first, self.audit())
        with tempfile.TemporaryDirectory() as other:
            Path(other, "nai_sec_bulk.yml").write_text(text, encoding="utf-8")
            self.assertEqual(first, self.module.audit_directory(Path(other)))
        self.assertNotIn(str(self.root), json.dumps(first))
        self.assertNotIn("generated_at", first)

    def test_malformed_selected_yaml_is_an_explicit_failure(self):
        self.put("nai_sec_bulk.yml", "on: [push\n")
        report = self.audit()
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(e["path"] == "nai_sec_bulk.yml" and e["message"] for e in report["errors"]))

    def test_duplicate_mapping_keys_are_rejected(self):
        self.put("nai_sec_bulk.yml", "on: push\non: workflow_dispatch\n")
        report = self.audit()
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report["errors"])

    def test_unsafe_yaml_constructors_are_not_executed(self):
        sentinel = self.root / "must-not-exist"
        self.put("nai_sec_bulk.yml", "name: !!python/object/apply:builtins.open ['" + sentinel.as_posix() + "', 'w']\non: push\n")
        report = self.audit()
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(sentinel.exists())

    def test_invalid_trigger_types_are_not_silently_accepted(self):
        for text in ["on: 42\n", "on: true\n", "on:\n  schedule: {cron: '0 1 * * *'}\n", "on:\n  schedule:\n    - cron: ''\n"]:
            with self.subTest(text=text):
                self.put("nai_sec_bulk.yml", text)
                self.assertEqual(self.audit()["status"], "FAIL")

    def test_empty_selection_is_not_a_green_audit(self):
        self.put("unrelated.yml", "on: push\n")
        report = self.audit()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["workflows"], [])
        self.assertTrue(report["errors"])

    def test_outside_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            source = Path(outside, "external.yml")
            source.write_text("on: push\n", encoding="utf-8")
            try:
                (self.root / "nai_sec_link.yml").symlink_to(source)
            except OSError:
                self.skipTest("Symlink creation unavailable; must run on Linux CI")
            report = self.audit()
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(report["errors"])

    def test_cli_writes_machine_readable_output_and_source_identity(self):
        self.put("nai_sec_bulk.yml", "on: push\n")
        output = self.root / "output.json"
        commit = "a" * 40
        result = subprocess.run([sys.executable, str(MODULE), "--workflows", str(self.root), "--output", str(output), "--source-commit", commit], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["source_commit"], commit)

    def test_cli_returns_failure_for_invalid_selected_input(self):
        self.put("nai_sec_bulk.yml", "on: [push\n")
        output = self.root / "output.json"
        result = subprocess.run([sys.executable, str(MODULE), "--workflows", str(self.root), "--output", str(output)], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "FAIL")

if __name__ == "__main__":
    unittest.main(verbosity=2)
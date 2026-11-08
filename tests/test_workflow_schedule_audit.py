"""Unit tests for the deterministic SEC/options workflow schedule audit."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MODULE = PROJECT / "agent" / "workflow_schedule_audit.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("workflow_schedule_audit_under_test", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowScheduleAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_module()

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def audit(self):
        return self.module.audit_directory(self.root)

    def rows(self, report):
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["errors"], [])
        return report["workflows"]

    def test_reports_schema_and_selected_families(self):
        self.write("nai_sec_bulk.yml", "name: SEC bulk\non: push\n")
        self.write("nai-sec-form345.yaml", "on: [push, workflow_dispatch]\n")
        self.write("nai_occ_oi_daily.yml", "on: schedule\n")
        self.write("nai-occ-oi-daily.yml", "on: push\n")
        self.write("world-v2-code-ci.yml", "on: push\n")
        self.write("nai_daily_forward.yml", "on: push\n")
        paths = [row["path"] for row in self.rows(self.audit())]
        self.assertEqual(paths, ["nai-occ-oi-daily.yml", "nai-sec-form345.yaml", "nai_occ_oi_daily.yml", "nai_sec_bulk.yml"])

    def test_events_and_schedules_are_normalized(self):
        self.write("nai_sec_bulk.yml", "on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n  schedule:\n    - cron: '7 3 * * 1'\n")
        row = self.rows(self.audit())[0]
        self.assertEqual(row["events"], ["push", "schedule", "workflow_dispatch"])
        self.assertEqual(row["schedules"], [{"cron": "7 3 * * 1", "timezone": "UTC"}])

    def test_explicit_timezone_kept_verbatim(self):
        self.write("nai_occ_oi_daily.yml", "'on':\n  schedule:\n    - cron: '8 6 * * *'\n      timezone: Asia/Hong_Kong\n")
        row = self.rows(self.audit())[0]
        self.assertEqual(row["schedules"], [{"cron": "8 6 * * *", "timezone": "Asia/Hong_Kong"}])
        self.assertNotIn("next_run", row)

    def test_name_falls_back_to_filename(self):
        self.write("nai_sec_form13f.yml", "on: workflow_dispatch\n")
        self.assertEqual(self.rows(self.audit())[0]["name"], "nai_sec_form13f.yml")

    def test_sha256_uses_exact_bytes(self):
        path = self.write("nai_sec_bulk.yml", "on: push\n")
        self.assertEqual(self.rows(self.audit())[0]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_invalid_inputs_fail(self):
        cases = [
            "on: [push\n",
            "on: push\non: workflow_dispatch\n",
            "on: 42\n",
            "on: true\n",
            "on:\n  schedule: {cron: '0 1 * * *'}\n",
            "on:\n  schedule:\n    - cron: ''\n",
            "on:\n  schedule:\n    - timezone: UTC\n",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.write("nai_sec_bulk.yml", text)
                report = self.audit()
                self.assertEqual(report["status"], "FAIL")
                self.assertTrue(report["errors"])

    def test_empty_selection_fails(self):
        self.write("unrelated.yml", "on: push\n")
        report = self.audit()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["workflows"], [])
        self.assertTrue(report["errors"])

    def test_unsafe_tag_creates_no_file(self):
        sentinel = self.root / "must-not-exist"
        self.write("nai_sec_bulk.yml", "name: !!python/object/apply:builtins.open ['" + sentinel.as_posix() + "', 'w']\non: push\n")
        self.assertEqual(self.audit()["status"], "FAIL")
        self.assertFalse(sentinel.exists())

    def test_output_is_deterministic_and_path_free(self):
        text = "name: SEC\non: [workflow_dispatch, push]\n"
        self.write("nai_sec_bulk.yml", text)
        first = self.audit()
        self.assertEqual(first, self.audit())
        with tempfile.TemporaryDirectory() as other:
            Path(other, "nai_sec_bulk.yml").write_text(text, encoding="utf-8")
            self.assertEqual(first, self.module.audit_directory(Path(other)))
        self.assertNotIn(str(self.root), json.dumps(first))
        self.assertNotIn("generated_at", first)

    def test_symlink_outside_directory_fails(self):
        with tempfile.TemporaryDirectory() as outside:
            source = Path(outside, "external.yml")
            source.write_text("on: push\n", encoding="utf-8")
            try:
                (self.root / "nai_sec_link.yml").symlink_to(source)
            except OSError:
                self.skipTest("symlinks unavailable")
            report = self.audit()
            self.assertEqual(report["status"], "FAIL")
            self.assertTrue(report["errors"])

    def test_cli_pass_writes_source_commit(self):
        self.write("nai_sec_bulk.yml", "on: push\n")
        output = self.root / "out" / "audit.json"
        commit = "b" * 40
        result = subprocess.run([sys.executable, str(MODULE), "--workflows", str(self.root), "--output", str(output), "--source-commit", commit], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["source_commit"], commit)

    def test_cli_fail_returns_one(self):
        self.write("nai_sec_bulk.yml", "on: [push\n")
        output = self.root / "audit.json"
        result = subprocess.run([sys.executable, str(MODULE), "--workflows", str(self.root), "--output", str(output)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)

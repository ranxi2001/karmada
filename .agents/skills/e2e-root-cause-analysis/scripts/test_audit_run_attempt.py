#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("audit_run_attempt.py")
SPEC = importlib.util.spec_from_file_location("audit_run_attempt", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class AuditRunAttemptTests(unittest.TestCase):
    def setUp(self):
        self.target = {"owner": "karmada-io", "repo": "karmada", "run_id": "10", "job_id": "20"}
        self.artifact = {
            "id": 30,
            "name": "karmada_e2e_log_v1.35.0",
            "created_at": "2026-08-13T10:10:00Z",
            "expired": False,
        }
        self.run = {
            "id": 10,
            "run_attempt": 2,
            "created_at": "2026-08-13T09:00:00Z",
            "run_started_at": "2026-08-13T10:00:00Z",
        }

    def test_current_attempt_artifact_is_attempt_compatible(self):
        job = {"id": 20, "run_id": 10, "run_attempt": 2}
        report = MODULE.build_report(self.target, job, self.run, [self.artifact])
        self.assertEqual("attempt_compatible", report["artifacts"][0]["classification"])

    def test_older_job_attempt_rejects_current_run_artifact(self):
        job = {"id": 20, "run_id": 10, "run_attempt": 1}
        report = MODULE.build_report(self.target, job, self.run, [self.artifact])
        self.assertEqual("not_attributable", report["artifacts"][0]["classification"])
        self.assertIn("older attempt", report["summary"]["conclusion"])

    def test_missing_attempt_is_ambiguous(self):
        job = {"id": 20, "run_id": 10}
        report = MODULE.build_report(self.target, job, self.run, [self.artifact])
        self.assertEqual("ambiguous", report["artifacts"][0]["classification"])

    def test_expired_artifact_keeps_ownership_but_is_unavailable(self):
        job = {"id": 20, "run_id": 10, "run_attempt": 2}
        artifact = {**self.artifact, "expired": True}
        report = MODULE.build_report(self.target, job, self.run, [artifact])
        self.assertEqual("attempt_compatible", report["artifacts"][0]["classification"])
        self.assertEqual("expired", report["artifacts"][0]["availability"])
        self.assertIn("expired", report["summary"]["conclusion"])

    def test_parse_job_url(self):
        parsed = MODULE.parse_job_url(
            "https://github.com/karmada-io/karmada/actions/runs/10/job/20"
        )
        self.assertEqual("10", parsed["run_id"])
        self.assertEqual("20", parsed["job_id"])

    def test_rejects_mismatched_job_run(self):
        job = {"id": 20, "run_id": 11, "run_attempt": 2}
        with self.assertRaisesRegex(ValueError, "job run id mismatch"):
            MODULE.validate_target(self.target, job, self.run)


if __name__ == "__main__":
    unittest.main()

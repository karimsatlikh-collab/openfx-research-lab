import hashlib
import tempfile
import unittest
from pathlib import Path

from worker.openfx_worker import (
    JobValidationError, WorkerConfig, process_job, validate_job,
)

def make_config(**overrides):
    values = {
        "control_plane_url": "https://control.example.test",
        "poll_interval_seconds": 30,
        "request_timeout_seconds": 15,
        "max_jobs_per_poll": 1,
        "allowed_ea_ids": ["openfx-demo-ea"],
        "max_backtest_days": 365,
        "max_runtime_seconds": 1800,
        "local_state_file": "worker_state.json",
        "execution_enabled": False,
    }
    values.update(overrides)
    return WorkerConfig.from_mapping(values)

def make_job(**overrides):
    job = {
        "job_id": "test-job-001",
        "idempotency_key": "test-key-001",
        "ea_id": "openfx-demo-ea",
        "ea_sha256": hashlib.sha256(b"demo").hexdigest(),
        "symbol": "EURUSD",
        "timeframe": "M15",
        "start_date": "2025-01-01",
        "end_date": "2025-02-01",
        "modeling_mode": "every_tick",
        "parameters": {"RiskPercent": 0.5},
        "approved": True,
        "timeout_seconds": 300,
    }
    job.update(overrides)
    return job

class WorkerValidationTests(unittest.TestCase):
    def test_accepts_valid_job(self):
        self.assertEqual(validate_job(make_job(), make_config())["job_id"], "test-job-001")

    def test_rejects_unknown_fields(self):
        with self.assertRaises(JobValidationError):
            validate_job(make_job(command="whoami"), make_config())

    def test_rejects_unapproved_ea(self):
        with self.assertRaises(JobValidationError):
            validate_job(make_job(ea_id="other-ea"), make_config())

    def test_rejects_unapproved_job(self):
        with self.assertRaises(JobValidationError):
            validate_job(make_job(approved=False), make_config())

    def test_rejects_non_iso_date_spellings(self):
        # date.fromisoformat accepts compact YYYYMMDD in modern Python; the API
        # contract requires the unambiguous YYYY-MM-DD representation.
        with self.assertRaises(JobValidationError):
            validate_job(make_job(start_date="20250101"), make_config())

    def test_rejects_metadata_that_is_not_bounded_json_primitives(self):
        with self.assertRaises(JobValidationError):
            validate_job(make_job(metadata={"nested": {"command": "run"}}), make_config())

    def test_idempotency_key_prevents_duplicate_submission_under_new_job_id(self):
        state = {"seen_jobs": {}, "events": []}
        config = make_config()
        first = make_job()
        second = make_job(job_id="test-job-002")
        self.assertEqual(process_job(first, config, state), "VALIDATED_NOT_EXECUTED")
        self.assertEqual(process_job(second, config, state), "DUPLICATE")

    def test_state_records_same_key_only_once(self):
        state = {"seen_jobs": {}, "events": []}
        config = make_config()
        process_job(make_job(), config, state)
        process_job(make_job(job_id="test-job-002"), config, state)
        self.assertEqual(len(state["seen_jobs"]), 1)

if __name__ == "__main__":
    unittest.main()

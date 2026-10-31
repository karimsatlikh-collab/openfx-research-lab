"""Offline tests for the OpenFX VPS worker prototype."""
import hashlib
import unittest

from worker.openfx_worker import (
    JobValidationError,
    WorkerConfig,
    process_job,
    safe_poll,
    validate_job,
)


def make_config():
    return WorkerConfig.from_mapping({
        "control_plane_url": "https://CONTROL-PLANE-PLACEHOLDER.invalid",
        "poll_interval_seconds": 30,
        "request_timeout_seconds": 15,
        "max_jobs_per_poll": 1,
        "allowed_ea_ids": ["openfx-demo-ea"],
        "max_backtest_days": 365,
        "max_runtime_seconds": 1800,
        "local_state_file": "worker_state.json",
        "execution_enabled": False,
    })


def make_job():
    return {
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


class WorkerValidationTests(unittest.TestCase):
    def setUp(self):
        self.config = make_config()

    def test_accepts_valid_job(self):
        self.assertEqual(validate_job(make_job(), self.config)["symbol"], "EURUSD")

    def test_network_polling_fails_closed_without_signed_authorization(self):
        # Even a plausible HTTPS endpoint and bearer token cannot authorize polling.
        config = WorkerConfig.from_mapping({
            "control_plane_url": "https://control.example.test",
            "poll_interval_seconds": 30,
            "request_timeout_seconds": 15,
            "max_jobs_per_poll": 1,
            "allowed_ea_ids": ["openfx-demo-ea"],
            "max_backtest_days": 365,
            "max_runtime_seconds": 1800,
            "local_state_file": "worker_state.json",
            "execution_enabled": False,
        })
        with self.assertRaisesRegex(RuntimeError, "Network polling is disabled"):
            safe_poll(config, "x" * 40)

    def test_rejects_unknown_fields_and_commands(self):
        with self.assertRaises(JobValidationError):
            validate_job({**make_job(), "command": "powershell"}, self.config)

    def test_rejects_unapproved_ea(self):
        with self.assertRaises(JobValidationError):
            validate_job({**make_job(), "ea_id": "other-ea"}, self.config)

    def test_rejects_unapproved_job(self):
        with self.assertRaises(JobValidationError):
            validate_job({**make_job(), "approved": False}, self.config)

    def test_rejects_too_long_date_range(self):
        with self.assertRaises(JobValidationError):
            validate_job({**make_job(), "start_date": "2020-01-01", "end_date": "2025-01-01"}, self.config)

    def test_deduplicates_jobs_and_does_not_execute(self):
        state = {"seen_jobs": {}, "events": []}
        self.assertEqual(process_job(make_job(), self.config, state), "VALIDATED_NOT_EXECUTED")
        self.assertEqual(process_job(make_job(), self.config, state), "DUPLICATE")
        self.assertEqual(state["seen_jobs"]["test-job-001"]["status"], "VALIDATED_NOT_EXECUTED")


if __name__ == "__main__":
    unittest.main()

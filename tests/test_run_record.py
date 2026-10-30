import unittest

from openfx.run_record import (
    EVIDENCE_LEVELS, RUN_STATUSES, new_run_record, transition_run_record,
    validate_run_record,
)

HASH = "a" * 64
INPUTS = {
    "job_spec_sha256": HASH,
    "strategy_spec_sha256": HASH,
    "implementation_sha256": HASH,
    "data_profile_sha256": HASH,
    "cost_profile_sha256": HASH,
    "gate_config_sha256": HASH,
}


def sample(evidence="mock"):
    return new_run_record("run-001", "job-001", evidence, INPUTS)


class RunRecordTests(unittest.TestCase):
    def test_all_schema_statuses_are_supported(self):
        self.assertEqual(len(RUN_STATUSES), 11)

    def test_all_evidence_levels_are_supported(self):
        self.assertEqual(EVIDENCE_LEVELS, {"mock", "synthetic", "mt5-demo"})

    def test_evidence_level_is_required_and_enum_checked(self):
        with self.assertRaises(ValueError):
            new_run_record("r", "j", "", INPUTS)
        with self.assertRaises(ValueError):
            new_run_record("r", "j", "live", INPUTS)

    def test_hashes_are_required_and_validated(self):
        bad = dict(INPUTS)
        bad["implementation_sha256"] = "not-a-hash"
        with self.assertRaises(ValueError):
            new_run_record("r", "j", "mock", bad)
        with self.assertRaises(ValueError):
            new_run_record("r", "j", "mock", {})

    def test_happy_path_sets_start_and_finish_timestamps(self):
        record = sample()
        record = transition_run_record(record, "VALIDATED")
        record = transition_run_record(record, "APPROVED")
        record = transition_run_record(record, "RUNNING")
        self.assertIsNotNone(record["timestamps"]["started_at_utc"])
        record = transition_run_record(record, "VERIFYING")
        record = transition_run_record(record, "COMPLETED")
        self.assertIsNotNone(record["timestamps"]["finished_at_utc"])
        validate_run_record(record)

    def test_rejects_illegal_transitions(self):
        with self.assertRaises(ValueError):
            transition_run_record(sample(), "RUNNING")
        with self.assertRaises(ValueError):
            transition_run_record(sample(), "COMPLETED")

    def test_failure_requires_error_and_sets_finished_time(self):
        record = sample()
        for status in ("VALIDATED", "APPROVED", "RUNNING"):
            record = transition_run_record(record, status)
        with self.assertRaises(ValueError):
            transition_run_record(record, "FAILED")
        failed = transition_run_record(record, "FAILED", error="worker crashed")
        self.assertEqual(failed["error"], "worker crashed")
        self.assertIsNotNone(failed["timestamps"]["finished_at_utc"])

    def test_evidence_and_input_identity_are_immutable(self):
        record = sample("synthetic")
        changed = dict(record)
        changed["evidence_level"] = "mt5-demo"
        with self.assertRaises(ValueError):
            transition_run_record(changed, "VALIDATED")
        changed = dict(record)
        changed["inputs"] = dict(INPUTS, implementation_sha256="b" * 64)
        with self.assertRaises(ValueError):
            transition_run_record(changed, "VALIDATED")

    def test_rejected_and_cancelled_are_terminal(self):
        rejected = transition_run_record(sample(), "REJECTED", error="policy denied")
        with self.assertRaises(ValueError):
            transition_run_record(rejected, "CANCELLED")
        cancelled = transition_run_record(sample(), "CANCELLED")
        self.assertIsNotNone(cancelled["timestamps"]["finished_at_utc"])

    def test_completed_does_not_claim_independent_approval(self):
        record = sample()
        for status in ("VALIDATED", "APPROVED", "RUNNING", "VERIFYING", "COMPLETED"):
            record = transition_run_record(record, status)
        self.assertNotIn("independently_verified", record)


if __name__ == "__main__":
    unittest.main()

"""M2 prototype calibration tests; synthetic fixtures only, never market validation."""
import json
import tempfile
import unittest
from pathlib import Path

from openfx.synthetic_engine import run_synthetic
from openfx.statistical_gate import evaluate_synthetic_summary, GateConfigError
from openfx.trial_registry import LocalTrialRegistry, TrialRegistryError
from openfx.synthetic_engine import validate_feature_timing


class SyntheticEngineTests(unittest.TestCase):
    def test_seeded_runs_are_repeatable(self):
        a = run_synthetic(seed=17, n=300, edge=0.1, noise=1.0)
        b = run_synthetic(seed=17, n=300, edge=0.1, noise=1.0)
        self.assertEqual(a, b)
        self.assertEqual(a["evidence_level"], "synthetic")
        self.assertFalse(a["is_market_backtest"])

    def test_noise_without_edge_has_calibrated_low_false_positive_rate(self):
        # Fixed seeds make this calibration test deterministic and reproducible.
        config = {"frozen_before_trials": True,
                  "trial_family_policy": {"max_trials": 200, "count_failures_and_abandoned": True},
                  "gate_id": "noise-calibration", "version": "1",
                  "multiple_testing_method": "other_pre_registered",
                  "acceptance_thresholds": {"min_mean_return": 0.25}}
        passes = 0
        for seed in range(200):
            summary = run_synthetic(seed=seed, n=100, edge=0.0, noise=1.0)
            verdict = evaluate_synthetic_summary(summary, config, trial_count=seed + 1)
            passes += verdict["decision"] == "pass"
        self.assertLessEqual(passes, 5, f"noise false-positive count too high: {passes}/200")

    def test_planted_edge_is_detectable_in_simple_fixture(self):
        config = {"frozen_before_trials": True,
                  "trial_family_policy": {"max_trials": 10, "count_failures_and_abandoned": True},
                  "gate_id": "planted-edge", "version": "1",
                  "multiple_testing_method": "other_pre_registered",
                  "acceptance_thresholds": {"min_mean_return": 0.25}}
        summary = run_synthetic(seed=11, n=300, edge=0.5, noise=0.5)
        verdict = evaluate_synthetic_summary(summary, config, trial_count=1)
        self.assertEqual(verdict["decision"], "pass")

    def test_future_timestamp_feature_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_feature_timing("future_close", "2025-01-01T10:15:00+00:00",
                                    "2025-01-01T10:00:00+00:00")
        self.assertTrue(validate_feature_timing("past_close", "2025-01-01T09:55:00+00:00",
                                                "2025-01-01T10:00:00+00:00"))


class GateTests(unittest.TestCase):
    def test_gate_must_be_frozen_and_trial_budget_is_enforced(self):
        summary = run_synthetic(seed=1, n=30)
        config = {"frozen_before_trials": True,
                  "trial_family_policy": {"max_trials": 1},
                  "gate_id": "budget", "version": "1",
                  "multiple_testing_method": "other_pre_registered",
                  "acceptance_thresholds": {"min_sample_size": 10}}
        self.assertEqual(evaluate_synthetic_summary(summary, config, trial_count=2)["decision"], "fail")
        config["frozen_before_trials"] = False
        with self.assertRaises(GateConfigError):
            evaluate_synthetic_summary(summary, config, trial_count=1)

    def test_unknown_gate_threshold_is_rejected(self):
        summary = run_synthetic(seed=2, n=30)
        config = {"frozen_before_trials": True,
                  "trial_family_policy": {"max_trials": 5},
                  "gate_id": "strict", "version": "1",
                  "multiple_testing_method": "other_pre_registered",
                  "acceptance_thresholds": {"mysterious_metric": 0.9}}
        with self.assertRaises(GateConfigError):
            evaluate_synthetic_summary(summary, config, trial_count=1)


class RegistryTests(unittest.TestCase):
    def test_hash_chain_and_idempotent_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "trials.jsonl")
            first = registry.append(event_id="evt-1", family_id="fam-1", trial_id="trial-1",
                                    outcome="failed", payload={"reason": "test"})
            retry = registry.append(event_id="evt-1", family_id="fam-1", trial_id="trial-1",
                                    outcome="failed", payload={"reason": "test"})
            self.assertEqual(first, retry)
            second = registry.append(event_id="evt-2", family_id="fam-1", trial_id="trial-2",
                                     outcome="completed")
            self.assertEqual(second["sequence"], 2)
            self.assertEqual(second["family_sequence"], 2)
            self.assertEqual(registry.verify()["event_count"], 2)

    def test_idempotency_key_cannot_be_reused_for_different_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "trials.jsonl")
            registry.append(event_id="evt-1", family_id="fam-1", trial_id="trial-1", outcome="failed")
            with self.assertRaises(TrialRegistryError):
                registry.append(event_id="evt-1", family_id="fam-1", trial_id="trial-1", outcome="completed")

    def test_trial_budget_is_enforced_atomically_and_failed_trials_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "trials.jsonl")
            first = registry.append(event_id="e1", family_id="fam", trial_id="t1",
                                    outcome="failed", max_trials=1)
            self.assertEqual(first["trial_index"], 1)
            # An idempotent retry is accepted even when the family budget is full.
            self.assertEqual(
                registry.append(event_id="e1", family_id="fam", trial_id="t1",
                                outcome="failed", max_trials=1), first
            )
            with self.assertRaisesRegex(TrialRegistryError, "budget exceeded"):
                registry.append(event_id="e2", family_id="fam", trial_id="t2",
                                outcome="pending", max_trials=1)
            self.assertEqual(registry.trial_count("fam"), 1)

    def test_pending_can_finish_once_but_terminal_contradictions_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "trials.jsonl")
            registry.append(event_id="e1", family_id="fam", trial_id="t1", outcome="pending")
            registry.append(event_id="e2", family_id="fam", trial_id="t1", outcome="completed")
            with self.assertRaisesRegex(TrialRegistryError, "terminal trial outcome"):
                registry.append(event_id="e3", family_id="fam", trial_id="t1", outcome="failed")
            self.assertEqual(registry.trial_count("fam"), 1)

    def test_invalid_outcome_type_is_rejected_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "trials.jsonl")
            with self.assertRaisesRegex(TrialRegistryError, "unsupported trial outcome"):
                registry.append(event_id="e1", family_id="fam", trial_id="t1", outcome=["failed"])

    def test_stale_lock_times_out_without_deleting_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.jsonl"
            registry = LocalTrialRegistry(path, lock_timeout_seconds=0.05)
            registry.lock_path.write_text("owner metadata unavailable", encoding="utf-8")
            with self.assertRaisesRegex(TrialRegistryError, "lock timeout"):
                registry.append(event_id="e1", family_id="fam", trial_id="t1", outcome="pending")
            self.assertTrue(registry.lock_path.exists())

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.jsonl"
            registry = LocalTrialRegistry(path)
            registry.append(event_id="evt-1", family_id="fam-1", trial_id="trial-1", outcome="failed")
            path.write_text(path.read_text(encoding="utf-8").replace('"failed"', '"completed"'), encoding="utf-8")
            with self.assertRaises(TrialRegistryError):
                registry.verify()


if __name__ == "__main__":
    unittest.main()

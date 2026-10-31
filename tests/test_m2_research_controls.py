"""M2 prototype calibration tests; synthetic fixtures only, never market validation."""
import json
import multiprocessing
import tempfile
import unittest
from pathlib import Path

from openfx.synthetic_engine import run_synthetic
from openfx.statistical_gate import evaluate_synthetic_summary, GateConfigError
from openfx.trial_registry import LocalTrialRegistry, TrialRegistryError
from openfx.synthetic_engine import validate_feature_timing


def _concurrent_registry_append(path, worker_id, result_queue):
    """Spawn-safe worker for cross-process registry budget testing."""
    registry = LocalTrialRegistry(path, lock_timeout_seconds=15.0)
    try:
        registry.append(event_id=f"event-{worker_id}", family_id="concurrent-family",
                        trial_id=f"trial-{worker_id}", outcome="failed", max_trials=6)
        result_queue.put((worker_id, "accepted"))
    except TrialRegistryError as exc:
        if "budget exceeded" in str(exc):
            result_queue.put((worker_id, "budget_rejected"))
        else:
            result_queue.put((worker_id, "error", str(exc)))
    except Exception as exc:
        result_queue.put((worker_id, "error", repr(exc)))


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

    def test_gate_rejects_boolean_trial_and_family_counts(self):
        summary = run_synthetic(seed=3, n=30)
        config = {"frozen_before_trials": True,
                  "trial_family_policy": {"max_trials": 5},
                  "gate_id": "strict", "version": "1",
                  "multiple_testing_method": "other_pre_registered",
                  "acceptance_thresholds": {"min_sample_size": 10}}
        with self.assertRaisesRegex(GateConfigError, "trial_count"):
            evaluate_synthetic_summary(summary, config, trial_count=True)
        config["trial_family_policy"]["max_trials"] = True
        with self.assertRaisesRegex(GateConfigError, "max_trials"):
            evaluate_synthetic_summary(summary, config, trial_count=1)

    def test_gate_rejects_non_numeric_and_non_finite_thresholds(self):
        summary = run_synthetic(seed=4, n=30)
        config = {"frozen_before_trials": True,
                  "trial_family_policy": {"max_trials": 5},
                  "gate_id": "strict", "version": "1",
                  "multiple_testing_method": "other_pre_registered",
                  "acceptance_thresholds": {"min_mean_return": "0.1"}}
        with self.assertRaisesRegex(GateConfigError, "finite number"):
            evaluate_synthetic_summary(summary, config, trial_count=1)
        config["acceptance_thresholds"]["min_mean_return"] = float("nan")
        with self.assertRaisesRegex(GateConfigError, "finite number"):
            evaluate_synthetic_summary(summary, config, trial_count=1)

    def test_gate_rejects_invalid_summary_metrics(self):
        summary = run_synthetic(seed=5, n=30)
        config = {"frozen_before_trials": True,
                  "trial_family_policy": {"max_trials": 5},
                  "gate_id": "strict", "version": "1",
                  "multiple_testing_method": "other_pre_registered",
                  "acceptance_thresholds": {"min_mean_return": 0.1}}
        summary["mean_return"] = float("inf")
        with self.assertRaisesRegex(GateConfigError, "summary mean_return"):
            evaluate_synthetic_summary(summary, config, trial_count=1)
        summary["mean_return"] = 0.2
        summary["sample_size"] = True
        with self.assertRaisesRegex(GateConfigError, "sample_size"):
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

    def test_registry_rejects_invalid_json_and_unknown_event_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_text("{broken\n", encoding="utf-8")
            with self.assertRaisesRegex(TrialRegistryError, "invalid JSON"):
                LocalTrialRegistry(path).verify()

        from openfx.trial_registry import GENESIS, _event_hash
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            event = {
                "schema_version": 1, "sequence": 1, "family_sequence": 1,
                "trial_index": 1, "event_id": "e1", "family_id": "f1",
                "trial_id": "t1", "outcome": "pending", "payload": {},
                "previous_event_sha256": GENESIS, "unreviewed": True,
            }
            event["event_sha256"] = _event_hash(event)
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(TrialRegistryError, "unexpected or missing"):
                LocalTrialRegistry(path).verify()

    def test_registry_rejects_unsupported_event_schema_version(self):
        from openfx.trial_registry import GENESIS, _event_hash
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            event = {
                "schema_version": 2, "sequence": 1, "family_sequence": 1,
                "trial_index": 1, "event_id": "e1", "family_id": "f1",
                "trial_id": "t1", "outcome": "pending", "payload": {},
                "previous_event_sha256": GENESIS,
            }
            event["event_sha256"] = _event_hash(event)
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(TrialRegistryError, "schema_version"):
                LocalTrialRegistry(path).verify()

    def test_readers_wait_for_writer_lock_and_fail_closed_on_stale_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.jsonl"
            registry = LocalTrialRegistry(path, lock_timeout_seconds=0.05)
            registry.lock_path.write_text("writer lock", encoding="utf-8")
            for read in (registry.verify, lambda: registry.trial_count("fam"),
                         lambda: registry.next_trial_index("fam")):
                with self.assertRaisesRegex(TrialRegistryError, "lock timeout"):
                    read()
            self.assertTrue(registry.lock_path.exists())

    def test_stale_lock_times_out_without_deleting_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.jsonl"
            registry = LocalTrialRegistry(path, lock_timeout_seconds=0.05)
            registry.lock_path.write_text("owner metadata unavailable", encoding="utf-8")
            with self.assertRaisesRegex(TrialRegistryError, "lock timeout"):
                registry.append(event_id="e1", family_id="fam", trial_id="t1", outcome="pending")
            self.assertTrue(registry.lock_path.exists())

    def test_multiprocess_appends_enforce_family_budget_atomically(self):
        # Each process opens its own registry instance against the same ledger.
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "trials.jsonl")
            ctx = multiprocessing.get_context("spawn")
            result_queue = ctx.Queue()
            workers = [ctx.Process(target=_concurrent_registry_append,
                                   args=(path, worker_id, result_queue))
                       for worker_id in range(12)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=25)
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
                    self.fail("concurrent registry worker did not finish")
                self.assertEqual(worker.exitcode, 0)
            results = [result_queue.get(timeout=3) for _ in workers]
            errors = [result for result in results if result[1] == "error"]
            self.assertEqual(errors, [], f"unexpected worker errors: {errors}")
            self.assertEqual(sum(result[1] == "accepted" for result in results), 6)
            self.assertEqual(sum(result[1] == "budget_rejected" for result in results), 6)
            registry = LocalTrialRegistry(path)
            self.assertEqual(registry.trial_count("concurrent-family"), 6)
            self.assertEqual(registry.verify()["event_count"], 6)

    def test_truncated_final_event_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trials.jsonl"
            registry = LocalTrialRegistry(path)
            registry.append(event_id="evt-1", family_id="fam-1", trial_id="trial-1",
                            outcome="failed")
            with path.open("a", encoding="utf-8") as stream:
                stream.write('{"sequence":2,"event_id":"partial')
            with self.assertRaisesRegex(TrialRegistryError, "invalid JSON"):
                registry.verify()

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

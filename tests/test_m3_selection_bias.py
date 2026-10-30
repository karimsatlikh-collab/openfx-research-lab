import tempfile
import unittest
from pathlib import Path

from openfx.selection_bias import (
    SelectionBiasError,
    evaluate_registered_family,
    holm_step_down,
    sha256_json,
)
from openfx.trial_registry import LocalTrialRegistry


def _manifest(**overrides):
    value = {
        "family_id": "family-A",
        "frozen_before_trials": True,
        "data_profile_id": "data-v1",
        "cost_profile_id": "cost-v1",
        "validation_split_id": "validation-v1",
        "return_frequency": "daily",
        "source_revision": "abc123",
        "frozen_at_utc": "2026-01-01T00:00:00Z",
        "max_trials": 10,
        "alpha": 0.05,
        "bootstrap_replicates": 199,
        "min_observations": 30,
    }
    value.update(overrides)
    return value


def _payload(returns, *, timestamps=None, **overrides):
    if timestamps is None:
        timestamps = [f"2025-01-{i + 1:02d}T00:00:00Z" for i in range(len(returns))]
    validation = {
        "returns": returns,
        "returns_sha256": sha256_json([float(x) for x in returns]),
        "timestamps": timestamps,
        "data_profile_id": "data-v1",
        "cost_profile_id": "cost-v1",
        "split_id": "validation-v1",
        "return_frequency": "daily",
    }
    validation.update(overrides)
    return {"validation": validation}


class FakeRegistry:
    def __init__(self, trials, manifest):
        self.trials = trials
        self.manifest_digest = sha256_json(manifest)

    def family_snapshot(self, family_id):
        trials = []
        for row in self.trials:
            item = dict(row)
            item["registration_outcome"] = "pending"
            item["registration_payload"] = {
                "family_manifest_sha256": self.manifest_digest,
                "registered_before_execution": True,
            }
            trials.append(item)
        return {
            "valid": True,
            "family_id": family_id,
            "trials": trials,
            "evidence_level": "synthetic",
        }


class M3SelectionBiasTests(unittest.TestCase):
    def test_holm_step_down_and_deterministic_ties(self):
        result = holm_step_down({"b": 0.001, "a": 0.001, "c": 0.04}, 0.05)
        self.assertEqual(result["a"]["rank"], 1)
        self.assertEqual(result["b"]["rank"], 2)
        self.assertTrue(result["a"]["rejected"])
        self.assertTrue(result["b"]["rejected"])
        self.assertFalse(result["c"]["rejected"])
        self.assertAlmostEqual(result["c"]["holm_adjusted_p_value"], 0.04)

    def test_complete_family_counts_failed_trials_as_p_one(self):
        returns = [0.15 + ((i % 7) - 3) * 0.01 for i in range(80)]
        trials = [
            {"trial_id": "t1", "trial_index": 1, "outcome": "completed",
             "payload": _payload(returns)},
            {"trial_id": "t2", "trial_index": 2, "outcome": "failed", "payload": {}},
        ]
        manifest = _manifest()
        verdict = evaluate_registered_family(registry=FakeRegistry(trials, manifest), manifest=manifest)
        self.assertEqual(verdict["trial_count"], 2)
        self.assertEqual(verdict["trial_ids"], ["t1", "t2"])
        self.assertEqual(verdict["trials"][1]["raw_p_value"], 1.0)
        self.assertFalse(verdict["trials"][1]["eligible"])
        self.assertEqual(verdict["trials"][1]["holm_adjusted_p_value"], 1.0)
        self.assertEqual(verdict["evidence_level"], "synthetic")

    def test_same_inputs_reproduce_identical_verdict(self):
        returns = [0.1 + ((i % 9) - 4) * 0.02 for i in range(90)]
        manifest = _manifest()
        registry = FakeRegistry([{
            "trial_id": "trial-1", "trial_index": 1, "outcome": "completed",
            "payload": _payload(returns),
        }], manifest)
        first = evaluate_registered_family(registry=registry, manifest=manifest)
        second = evaluate_registered_family(registry=registry, manifest=manifest)
        self.assertEqual(first, second)
        self.assertTrue(first["verdict_sha256"])

    def test_alignment_mismatch_is_excluded_not_silently_used(self):
        a = [0.1 + ((i % 5) - 2) * 0.03 for i in range(70)]
        b = [0.2 + ((i % 5) - 2) * 0.03 for i in range(70)]
        times_a = [f"2025-02-{i + 1:02d}" for i in range(70)]
        times_b = [f"2025-03-{i + 1:02d}" for i in range(70)]
        trials = [
            {"trial_id": "a", "trial_index": 1, "outcome": "completed",
             "payload": _payload(a, timestamps=times_a)},
            {"trial_id": "b", "trial_index": 2, "outcome": "completed",
             "payload": _payload(b, timestamps=times_b)},
        ]
        manifest = _manifest()
        verdict = evaluate_registered_family(registry=FakeRegistry(trials, manifest), manifest=manifest)
        self.assertTrue(verdict["trials"][0]["eligible"])
        self.assertFalse(verdict["trials"][1]["eligible"])
        self.assertIn("unaligned_timestamps", verdict["trials"][1]["exclusion_reason"])

    def test_changed_returns_hash_fails_closed_to_p_one(self):
        returns = [0.1 + ((i % 6) - 2) * 0.02 for i in range(60)]
        payload = _payload(returns)
        payload["validation"]["returns_sha256"] = "0" * 64
        manifest = _manifest()
        registry = FakeRegistry([{
            "trial_id": "tampered", "trial_index": 1, "outcome": "completed",
            "payload": payload,
        }], manifest)
        verdict = evaluate_registered_family(registry=registry, manifest=manifest)
        self.assertEqual(verdict["decision"], "BLOCKED")
        self.assertEqual(
            verdict["exclusions"]["tampered"],
            "return_artifact_hash_mismatch_counted_with_p1",
        )

    def test_manifest_requires_frozen_configuration(self):
        manifest = _manifest(frozen_before_trials=False)
        registry = FakeRegistry([{"trial_id": "x", "trial_index": 1, "outcome": "failed"}], manifest)
        with self.assertRaises(SelectionBiasError):
            evaluate_registered_family(registry=registry, manifest=manifest)

    def test_local_registry_snapshot_retains_all_terminal_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = LocalTrialRegistry(Path(directory) / "trials.jsonl")
            manifest = _manifest()
            binding = {
                "family_manifest_sha256": sha256_json(manifest),
                "registered_before_execution": True,
            }
            registry.append(event_id="e1", family_id="family-A", trial_id="failed-1",
                            outcome="pending", payload=binding)
            registry.append(event_id="e2", family_id="family-A", trial_id="failed-1",
                            outcome="failed", payload={"reason": "timeout"})
            registry.append(event_id="e3", family_id="family-A", trial_id="done-1",
                            outcome="pending", payload=binding)
            registry.append(event_id="e4", family_id="family-A", trial_id="done-1",
                            outcome="completed",
                            payload=_payload([0.1 + (i % 3) * 0.01 for i in range(40)]))
            snapshot = registry.family_snapshot("family-A")
            self.assertTrue(snapshot["valid"])
            self.assertEqual(snapshot["trial_count"], 2)
            self.assertEqual([x["trial_id"] for x in snapshot["trials"]], ["failed-1", "done-1"])
            self.assertEqual(snapshot["trials"][0]["outcome"], "failed")
            self.assertEqual(snapshot["trials"][1]["outcome"], "completed")

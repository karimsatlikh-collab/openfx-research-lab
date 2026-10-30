import unittest
from datetime import datetime, timedelta, timezone

from openfx.selection_bias_v2 import (
    HAC_KERNEL_ID,
    HAC_LAG_RULE,
    METHOD_ID,
    METHOD_VERSION,
    BLOCK_LENGTH_RULE,
    SelectionBiasV2Error,
    _bootstrap_pvalues,
    _hac_studentized_mean,
    evaluate_registered_family,
    holm_step_down,
    sha256_json,
)


def _manifest(**overrides):
    value = {
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "family_id": "family-v2",
        "frozen_before_trials": True,
        "data_profile_id": "data-v1",
        "cost_profile_id": "cost-v1",
        "validation_split_id": "validation-v1",
        "return_frequency": "daily",
        "source_revision": "a" * 40,
        "frozen_at_utc": "2026-01-01T00:00:00Z",
        "max_trials": 10,
        "alpha": 0.05,
        "bootstrap_replicates": 9999,
        "min_observations": 252,
        "hac_kernel": HAC_KERNEL_ID,
        "hac_lag_rule": HAC_LAG_RULE,
        "block_length_rule": BLOCK_LENGTH_RULE,
    }
    value.update(overrides)
    return value


def _timestamps(length):
    origin = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [(origin + timedelta(days=i)).isoformat().replace("+00:00", "Z")
            for i in range(length)]


def _validation_payload(returns, source_revision="a" * 40):
    return {
        "validation": {
            "returns": returns,
            "returns_sha256": sha256_json([float(x) for x in returns]),
            "timestamps": _timestamps(len(returns)),
            "data_profile_id": "data-v1",
            "cost_profile_id": "cost-v1",
            "split_id": "validation-v1",
            "return_frequency": "daily",
            "source_revision": source_revision,
        }
    }


class FakeRegistry:
    def __init__(self, trials, manifest):
        self.trials = trials
        self.manifest_digest = sha256_json(manifest)

    def family_snapshot(self, family_id):
        result = []
        for row in self.trials:
            item = dict(row)
            item["registration_outcome"] = "pending"
            item["registration_payload"] = {
                "family_manifest_sha256": self.manifest_digest,
                "registered_before_execution": True,
            }
            result.append(item)
        event_count = sum(2 if row.get("outcome") == "completed" else 1 for row in self.trials)
        return {"valid": True, "family_id": family_id, "trials": result,
                "event_count": event_count, "trial_count": len(result),
                "family_event_sha256": [f"{i:064x}" for i in range(event_count)],
                "trust": "local_prototype_not_independently_authenticated",
                "evidence_level": "synthetic"}


class M3HACSelectionBiasTests(unittest.TestCase):
    def test_hac_studentized_statistic_is_finite_and_positive_for_positive_mean(self):
        values = [0.1 + ((i % 7) - 3) * 0.01 for i in range(252)]
        statistic = _hac_studentized_mean(values, 7)
        self.assertGreater(statistic, 0.0)

    def test_hac_rejects_degenerate_variance(self):
        with self.assertRaises(SelectionBiasV2Error):
            _hac_studentized_mean([0.0] * 252, 7)

    def test_bootstrap_is_deterministic_for_fixed_seed(self):
        values = [0.01 + ((i % 9) - 4) * 0.02 for i in range(252)]
        series = {"t1": values}
        first = _bootstrap_pvalues(series, replicates=199, seed=12345)
        second = _bootstrap_pvalues(series, replicates=199, seed=12345)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["t1"], 0.0)
        self.assertLessEqual(first["t1"], 1.0)

    def test_holm_step_down_and_stop_rule(self):
        result = holm_step_down({"a": 0.001, "b": 0.03, "c": 0.04})
        self.assertTrue(result["a"]["rejected"])
        self.assertFalse(result["b"]["rejected"])
        self.assertFalse(result["c"]["rejected"])
        self.assertAlmostEqual(result["b"]["holm_adjusted_p_value"], 0.06)

    def test_family_evaluation_counts_failed_trials_and_emits_hac_contract(self):
        returns = [0.12 + ((i % 7) - 3) * 0.01 for i in range(252)]
        manifest = _manifest()
        trials = [
            {"trial_id": "candidate", "trial_index": 1, "outcome": "completed",
             "payload": _validation_payload(returns)},
            {"trial_id": "failed", "trial_index": 2, "outcome": "failed", "payload": {}},
        ]
        verdict = evaluate_registered_family(
            registry=FakeRegistry(trials, manifest), manifest=manifest
        )
        self.assertEqual(verdict["trial_count"], 2)
        self.assertEqual(verdict["trial_ids"], ["candidate", "failed"])
        self.assertEqual(verdict["trials"][1]["raw_p_value"], 1.0)
        self.assertEqual(verdict["hac_kernel"], HAC_KERNEL_ID)
        self.assertEqual(verdict["hac_lag"], 7)
        self.assertEqual(verdict["block_length"], 7)
        self.assertTrue(verdict["verdict_sha256"])


    def test_source_revision_mismatch_is_excluded_from_family(self):
        returns = [0.01 + ((i % 7) - 3) * 0.002 for i in range(252)]
        manifest = _manifest()
        trials = [{
            "trial_id": "wrong-source", "trial_index": 1, "outcome": "completed",
            "payload": _validation_payload(returns, source_revision="b" * 40),
        }]
        verdict = evaluate_registered_family(
            registry=FakeRegistry(trials, manifest), manifest=manifest
        )
        self.assertEqual(verdict["decision"], "BLOCKED")
        self.assertEqual(verdict["exclusions"]["wrong-source"],
                         "binding_mismatch:source_revision")

    def test_manifest_requires_git_sha_source_revision(self):
        manifest = _manifest(source_revision="abc123")
        registry = FakeRegistry([
            {"trial_id": "failed", "trial_index": 1, "outcome": "failed"}
        ], manifest)
        with self.assertRaises(SelectionBiasV2Error):
            evaluate_registered_family(registry=registry, manifest=manifest)

    def test_bootstrap_work_budget_blocks_oversized_family_before_sampling(self):
        returns = [0.02 + ((i % 7) - 3) * 0.001 for i in range(252)]
        manifest = _manifest(max_trials=60)
        trials = [
            {"trial_id": f"candidate-{i:02d}", "trial_index": i,
             "outcome": "completed", "payload": _validation_payload(returns)}
            for i in range(1, 61)
        ]
        verdict = evaluate_registered_family(
            registry=FakeRegistry(trials, manifest), manifest=manifest
        )
        self.assertEqual(verdict["decision"], "BLOCKED")
        self.assertEqual(verdict["reason"], "bootstrap_work_budget_exceeded")
        self.assertGreater(verdict["estimated_bootstrap_work"], verdict["max_bootstrap_work"])

    def test_method_settings_are_frozen(self):
        manifest = _manifest(hac_lag_rule="caller-selected")
        registry = FakeRegistry([
            {"trial_id": "failed", "trial_index": 1, "outcome": "failed"}
        ], manifest)
        with self.assertRaises(SelectionBiasV2Error):
            evaluate_registered_family(registry=registry, manifest=manifest)


if __name__ == "__main__":
    unittest.main()

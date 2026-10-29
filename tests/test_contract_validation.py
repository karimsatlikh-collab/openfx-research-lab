"""Regression tests for semantic contract consistency and registry-owned counts."""
import tempfile
import unittest
from pathlib import Path

from openfx.contract_validation import (
    ContractValidationError, canonical_sha256, validate_job_bundle,
    validate_run_against_job, validate_run_transition,
)
from openfx.statistical_gate import evaluate_registered_synthetic_summary, GateConfigError
from openfx.trial_registry import LocalTrialRegistry, TrialRegistryError


def bundle():
    strategy = {"strategy_id": "strat", "version": "1.0", "rules": []}
    data = {"profile_id": "data", "version": "1.0", "data_sha256": "b" * 64}
    costs = {"profile_id": "cost", "version": "1.0", "spread": 1}
    gate = {
        "gate_id": "gate", "version": "1.0", "frozen_before_trials": True,
        "trial_family_policy": {
            "family_id": "family", "max_trials": 3,
            "count_failures_and_abandoned": True,
        },
    }
    job = {
        "job_id": "job-1",
        "strategy_spec_ref": {"id": "strat", "version": "1.0", "sha256": canonical_sha256(strategy)},
        "data_profile_ref": {"id": "data", "version": "1.0", "sha256": canonical_sha256(data)},
        "cost_profile_ref": {"id": "cost", "version": "1.0", "sha256": canonical_sha256(costs)},
        "gate_config_ref": {"id": "gate", "version": "1.0", "sha256": canonical_sha256(gate)},
        "implementation": {"source_revision": "abc123", "build_sha256": "a" * 64},
        "budget": {"max_trials": 2, "timeout_seconds": 60},
        "requested_engine": "synthetic",
    }
    return job, strategy, data, costs, gate


class SemanticContractTests(unittest.TestCase):
    def test_valid_bundle_passes_and_reports_limitations(self):
        job, strategy, data, costs, gate = bundle()
        result = validate_job_bundle(
            job, strategy_spec=strategy, data_profile=data, cost_profile=costs, gate_config=gate
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["max_trials"], 2)

    def test_wrong_immutable_hash_is_rejected(self):
        job, strategy, data, costs, gate = bundle()
        job["data_profile_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractValidationError, "data_profile_ref.sha256"):
            validate_job_bundle(
                job, strategy_spec=strategy, data_profile=data, cost_profile=costs, gate_config=gate
            )

    def test_job_budget_cannot_exceed_frozen_gate_budget(self):
        job, strategy, data, costs, gate = bundle()
        job["budget"]["max_trials"] = 4
        with self.assertRaisesRegex(ContractValidationError, "exceeds"):
            validate_job_bundle(
                job, strategy_spec=strategy, data_profile=data, cost_profile=costs, gate_config=gate
            )

    def test_run_must_bind_to_job_and_matching_evidence_label(self):
        job, *_ = bundle()
        run = {
            "job_id": "job-1", "run_id": "run-1", "status": "COMPLETED",
            "evidence_level": "synthetic",
            "timestamps": {"finished_at_utc": "2026-01-01T00:01:00Z"},
            "inputs": {
                "implementation_sha256": job["implementation"]["build_sha256"],
                "strategy_spec_sha256": job["strategy_spec_ref"]["sha256"],
                "data_profile_sha256": job["data_profile_ref"]["sha256"],
                "cost_profile_sha256": job["cost_profile_ref"]["sha256"],
                "gate_config_sha256": job["gate_config_ref"]["sha256"],
            },
        }
        result = validate_run_against_job(run, job)
        self.assertEqual(result["performance_conclusion"], "not_inferred_from_run_status")
        run["evidence_level"] = "mt5-demo"
        with self.assertRaisesRegex(ContractValidationError, "evidence_level"):
            validate_run_against_job(run, job)

    def test_completed_requires_finish_timestamp_but_not_profitability(self):
        job, *_ = bundle()
        run = {
            "job_id": "job-1", "run_id": "run-1", "status": "COMPLETED",
            "evidence_level": "synthetic", "timestamps": {},
            "inputs": {
                "implementation_sha256": job["implementation"]["build_sha256"],
                "strategy_spec_sha256": job["strategy_spec_ref"]["sha256"],
                "data_profile_sha256": job["data_profile_ref"]["sha256"],
                "cost_profile_sha256": job["cost_profile_ref"]["sha256"],
                "gate_config_sha256": job["gate_config_ref"]["sha256"],
            },
        }
        with self.assertRaisesRegex(ContractValidationError, "finished_at_utc"):
            validate_run_against_job(run, job)

    def test_state_machine_rejects_skipping_approval(self):
        with self.assertRaisesRegex(ContractValidationError, "illegal run transition"):
            validate_run_transition("VALIDATED", "RUNNING")
        validate_run_transition("APPROVED", "RUNNING")
        with self.assertRaises(ContractValidationError):
            validate_run_transition("COMPLETED", "RUNNING")


class RegistrarOwnedCountTests(unittest.TestCase):
    def test_unique_trials_count_failures_and_duplicate_events_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "ledger.jsonl")
            registry.append(event_id="e1", family_id="fam", trial_id="t1", outcome="pending")
            registry.append(event_id="e2", family_id="fam", trial_id="t1", outcome="failed")
            registry.append(event_id="e3", family_id="fam", trial_id="t2", outcome="completed")
            self.assertEqual(registry.trial_count("fam"), 2)
            self.assertEqual(registry.next_trial_index("fam"), 3)
            self.assertEqual(registry.verify()["trial_count"], 2)

    def test_trial_id_cannot_be_reused_across_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "ledger.jsonl")
            registry.append(event_id="e1", family_id="fam-a", trial_id="t1", outcome="failed")
            with self.assertRaisesRegex(TrialRegistryError, "across trial families"):
                registry.append(event_id="e2", family_id="fam-b", trial_id="t1", outcome="completed")

    def test_gate_uses_registry_count_not_a_caller_supplied_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "ledger.jsonl")
            registry.append(event_id="e1", family_id="fam", trial_id="t1", outcome="failed")
            registry.append(event_id="e2", family_id="fam", trial_id="t2", outcome="completed")
            config = {
                "frozen_before_trials": True,
                "trial_family_policy": {"max_trials": 1, "count_failures_and_abandoned": True},
                "gate_id": "gate", "version": "1",
                "multiple_testing_method": "other_pre_registered",
                "acceptance_thresholds": {"min_sample_size": 1},
            }
            summary = {"sample_size": 100, "mean_return": 1.0, "evidence_level": "synthetic"}
            result = evaluate_registered_synthetic_summary(summary, config, registry=registry, family_id="fam")
            self.assertEqual(result["trial_count"], 2)
            self.assertEqual(result["decision"], "fail")
            self.assertEqual(result["reason"], "trial_budget_exceeded")
            self.assertEqual(result["trial_count_source"], "local_registry")

    def test_gate_rejects_empty_registry_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "ledger.jsonl")
            config = {
                "frozen_before_trials": True,
                "trial_family_policy": {"max_trials": 3},
                "gate_id": "gate", "version": "1",
                "multiple_testing_method": "other_pre_registered",
                "acceptance_thresholds": {"min_sample_size": 1},
            }
            with self.assertRaises(GateConfigError):
                evaluate_registered_synthetic_summary(
                    {"sample_size": 10}, config, registry=registry, family_id="empty"
                )


if __name__ == "__main__":
    unittest.main()

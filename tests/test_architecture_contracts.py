"""Regression checks for the versioned OpenFX architecture contracts.

These tests use only the standard library. They check JSON syntax and critical
contract invariants, but they do not constitute full JSON Schema validation.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"


class ArchitectureContractTests(unittest.TestCase):
    def load_schema(self, filename):
        with (SCHEMAS / filename).open(encoding="utf-8") as handle:
            schema = json.load(handle)
        self.assertEqual(schema.get("$schema"), "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema.get("type"), "object")
        self.assertIn("required", schema)
        return schema

    def test_all_m1_schemas_are_valid_json_and_versioned(self):
        files = [
            "strategy-spec-v1.schema.json",
            "job-spec-v1.schema.json",
            "run-record-v1.schema.json",
            "trial-registry-entry-v1.schema.json",
            "gate-verdict-v1.schema.json",
        ]
        for filename in files:
            with self.subTest(filename=filename):
                schema = self.load_schema(filename)
                self.assertIn("schema_version", schema["required"])
                self.assertEqual(schema["properties"]["schema_version"], {"const": 1})

    def test_job_binds_immutable_inputs_and_finite_budget(self):
        schema = self.load_schema("job-spec-v1.schema.json")
        required = set(schema["required"])
        self.assertTrue({
            "strategy_spec_ref", "implementation", "data_profile_ref",
            "cost_profile_ref", "frozen_parameters", "budget", "requested_engine"
        }.issubset(required))
        self.assertEqual(
            schema["properties"]["requested_engine"]["enum"],
            ["mock", "synthetic", "mt5-demo"],
        )
        budget = schema["properties"]["budget"]["properties"]
        self.assertEqual(budget["max_trials"]["minimum"], 1)
        self.assertEqual(budget["timeout_seconds"]["minimum"], 1)

    def test_run_state_is_separate_from_evidence_level(self):
        schema = self.load_schema("run-record-v1.schema.json")
        self.assertEqual(
            schema["properties"]["status"]["enum"],
            ["QUEUED", "VALIDATED", "APPROVED", "RUNNING", "VERIFYING",
             "COMPLETED", "FAILED", "TIMEOUT", "INTERRUPTED", "REJECTED", "CANCELLED"],
        )
        self.assertEqual(
            schema["properties"]["evidence_level"]["enum"],
            ["mock", "synthetic", "mt5-demo"],
        )
        self.assertIn("evidence_level", schema["required"])
        self.assertIn("status", schema["required"])

    def test_registry_preserves_non_success_outcomes(self):
        schema = self.load_schema("trial-registry-entry-v1.schema.json")
        outcomes = schema["properties"]["outcome"]["enum"]
        for value in ["failed", "timeout", "interrupted", "rejected", "cancelled"]:
            self.assertIn(value, outcomes)

    def test_verdict_binds_gate_config_and_trial_count(self):
        schema = self.load_schema("gate-verdict-v1.schema.json")
        required = set(schema["required"])
        self.assertTrue({
            "gate_version", "gate_config_sha256", "trial_family_id",
            "trial_count_at_decision", "checks", "limitations"
        }.issubset(required))
        self.assertEqual(schema["properties"]["trial_count_at_decision"]["minimum"], 1)
        self.assertGreaterEqual(schema["properties"]["limitations"]["minItems"], 1)

    def test_strategy_claims_keep_provenance_labels(self):
        schema = self.load_schema("strategy-spec-v1.schema.json")
        claim = schema["properties"]["claims"]["items"]["properties"]["label"]
        self.assertEqual(
            claim["enum"],
            ["Verified", "Source claim", "Hypothesis", "Unknown / not tested"],
        )


if __name__ == "__main__":
    unittest.main()

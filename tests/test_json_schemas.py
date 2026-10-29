"""Executable JSON Schema contract tests for the versioned OpenFX records."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from openfx.experiment import new_experiment, validate_manifest
from test_backtest_result import make_result

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "experiment": ROOT / "schemas" / "experiment-v1.schema.json",
    "source_registry": ROOT / "schemas" / "source-registry-v1.schema.json",
    "claim_register": ROOT / "schemas" / "claim-register-v1.schema.json",
    "backtest_result": ROOT / "schemas" / "backtest-result-v1.schema.json",
}


def load_schema(name: str) -> dict:
    return json.loads(SCHEMAS[name].read_text(encoding="utf-8"))


def make_validator(name: str) -> Draft202012Validator:
    schema = load_schema(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def make_manifest() -> dict:
    return new_experiment(
        experiment_id="schema-test-001",
        hypothesis="Synthetic schema contract fixture only",
        strategy_version="fixture-v1",
        symbol="EURUSD",
        timeframe="M15",
        data_start="2024-01-01",
        data_end="2024-12-31",
    )


class JsonSchemaContractTests(unittest.TestCase):
    def test_all_schemas_are_valid_draft_2020_12_schemas(self):
        for name in SCHEMAS:
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(load_schema(name))

    def test_checked_in_source_and_claim_examples_validate(self):
        examples = (
            ("source_registry", ROOT / "data" / "source_registry.example.json"),
            ("claim_register", ROOT / "data" / "claim_register.example.json"),
        )
        for schema_name, path in examples:
            with self.subTest(example=path.name):
                instance = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(list(make_validator(schema_name).iter_errors(instance)), [])

    def test_generated_experiment_manifest_matches_schema_and_python_validator(self):
        manifest = make_manifest()
        self.assertEqual(list(make_validator("experiment").iter_errors(manifest)), [])
        validate_manifest(manifest)

    def test_synthetic_backtest_result_fixture_matches_schema(self):
        # This fixture is synthetic metadata for validation tests, not a real MT5 run.
        result = make_result()
        self.assertEqual(list(make_validator("backtest_result").iter_errors(result)), [])

    def test_experiment_schema_rejects_unknown_root_field(self):
        manifest = make_manifest()
        manifest["unexpected_field"] = "must not be silently accepted"
        self.assertTrue(list(make_validator("experiment").iter_errors(manifest)))
        with self.assertRaisesRegex(ValueError, "unknown manifest fields"):
            validate_manifest(manifest)

    def test_experiment_schema_rejects_impossible_calendar_date(self):
        manifest = make_manifest()
        manifest["market"]["data_start"] = "2024-02-31"
        self.assertTrue(list(make_validator("experiment").iter_errors(manifest)))
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_claim_schema_rejects_unreviewed_source_confirmed_claim(self):
        register = {
            "schema_version": 1,
            "claims": [{
                "claim_id": "claim-test-001",
                "claim_text": "Synthetic claim",
                "classification": "source_confirmed",
                "review_status": "draft",
                "rationale": "Fixture used to test the schema constraint.",
                "evidence": [{
                    "source_id": "source-test-001",
                    "segment_id": "segment-test-001",
                    "quote": "Exact synthetic quote",
                }],
                "contradiction_group": None,
            }],
        }
        self.assertTrue(list(make_validator("claim_register").iter_errors(register)))

    def test_backtest_schema_rejects_mock_result_origin(self):
        result = copy.deepcopy(make_result())
        result["result_origin"] = "mock"
        self.assertTrue(list(make_validator("backtest_result").iter_errors(result)))


if __name__ == "__main__":
    unittest.main()

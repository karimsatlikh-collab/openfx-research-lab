"""Acceptance and tamper tests for the synthetic-only G0-G2 vertical slice."""
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from openfx.source_provenance import build_source_record, build_atomic_claim, build_hypothesis_card
from openfx.synthetic_e2e import (
    canonical_bytes, freeze_trial, run_synthetic_reproduction,
    sha256_bytes, verify_frozen_trial,
)
from openfx.statistical_gate import GateConfigError
from openfx.trial_registry import LocalTrialRegistry, TrialRegistryError

CONTENT = b"OpenFX local synthetic source fixture."
LOCATOR = "fixture://openfx/synthetic#segment=1"


def frozen():
    source = build_source_record(
        source_id="source-e2e-1", identity="locally authored synthetic fixture",
        rights_basis="owner_created", permission_evidence="created for tests",
        retrieved_at_utc="2026-10-30T12:00:00Z", exact_locator=LOCATOR,
        capture_method="inline fixture bytes", content=CONTENT,
        provenance_state="test_confirmed",
    )
    claim = build_atomic_claim(
        claim_id="claim-e2e-1", source_record=source, source_content=CONTENT,
        exact_locator=LOCATOR, statement="Fixture contains a synthetic observation.",
        provenance_state="test_confirmed",
    )
    hypothesis = build_hypothesis_card(
        hypothesis_id="hyp-e2e-1", title="Synthetic deterministic replay",
        falsifiable_statement="Identical frozen inputs produce identical run bytes.",
        linked_claims=[claim], predicted_mechanism="Seeded deterministic generator",
        invalidation_criteria="Any differing run record or artifact hash",
    )
    gate = {
        "gate_id": "synthetic-descriptive-v1", "version": 1,
        "frozen_before_trials": True,
        "trial_family_policy": {"max_trials": 1},
        "multiple_testing_method": "other_pre_registered",
        "acceptance_thresholds": {"min_sample_size": 20},
    }
    return freeze_trial(
        source_record=source, source_content=CONTENT, claim=claim, hypothesis=hypothesis,
        family_id="family-e2e-1", trial_id="trial-e2e-1",
        seed=17, n=50, edge=0.0, noise=1.0, gate_config=gate,
    )


class SyntheticEndToEndTests(unittest.TestCase):
    def test_two_replays_match_and_are_registered(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            result = run_synthetic_reproduction(frozen=frozen(), registry=registry, workspace=Path(tmp) / "runs")
            self.assertEqual(result["status"], "synthetic_reproduced")
            self.assertTrue(result["replay_hashes_equal"])
            self.assertEqual(result["evidence_level"], "synthetic")
            self.assertFalse(result["is_market_backtest"])
            self.assertEqual(result["registry"]["event_count"], 2)
            self.assertEqual(result["gate_verdict"]["trial_count"], 1)

    def test_artifact_tampering_after_write_is_detected_and_trial_fails(self):
        original_read_bytes = Path.read_bytes

        def tamper_then_read(path):
            if path.name == "run_record.json":
                original = original_read_bytes(path)
                path.write_bytes(original + b"tampered")
            return original_read_bytes(path)

        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            with mock.patch.object(Path, "read_bytes", autospec=True, side_effect=tamper_then_read):
                with self.assertRaisesRegex(ValueError, "persisted run artifact bytes differ"):
                    run_synthetic_reproduction(
                        frozen=frozen(), registry=registry, workspace=Path(tmp) / "runs"
                    )
            rows = registry._read_and_verify()
            self.assertEqual([row["outcome"] for row in rows], ["pending", "failed"])
            self.assertEqual(rows[-1]["event_id"], "trial-e2e-1-failed")

    def test_frozen_input_tampering_is_rejected_before_registration(self):
        spec = frozen()
        spec["engine_parameters"]["seed"] = 999
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                run_synthetic_reproduction(frozen=spec, registry=registry, workspace=Path(tmp) / "runs")
            self.assertEqual(registry.verify()["event_count"], 0)

    def test_freeze_binds_complete_provenance_documents(self):
        spec = frozen()
        self.assertEqual(len(spec["source_record_sha256"]), 64)
        self.assertEqual(len(spec["claim_sha256"]), 64)
        self.assertEqual(len(spec["hypothesis_sha256"]), 64)
        spec["claim_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            verify_frozen_trial(spec)

    def test_hypothesis_cannot_be_relabelled_as_verified_rule(self):
        spec = frozen()
        spec["hypothesis_status"] = "verified_rule"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verify_frozen_trial(spec)

    def test_changed_source_claim_binding_is_rejected_when_freezing(self):
        spec = frozen()
        spec["source_ref"]["content_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            verify_frozen_trial(spec)

    def test_freeze_rejects_nonfinite_parameters_and_nonstring_ids(self):
        base = frozen()
        source_record = build_source_record(
            source_id="source-e2e-2", identity="fixture", rights_basis="owner_created",
            permission_evidence="test fixture", retrieved_at_utc="2026-10-30T12:00:00Z",
            exact_locator=LOCATOR, capture_method="inline", content=CONTENT,
        )
        claim = build_atomic_claim(
            claim_id="claim-e2e-2", source_record=source_record, source_content=CONTENT,
            exact_locator=LOCATOR, statement="Fixture claim.",
        )
        hypothesis = build_hypothesis_card(
            hypothesis_id="hyp-e2e-2", title="H", falsifiable_statement="F",
            linked_claims=[claim], predicted_mechanism="M", invalidation_criteria="I",
        )
        gate = base["gate_config"]
        with self.assertRaisesRegex(ValueError, "finite numbers"):
            freeze_trial(
                source_record=source_record, source_content=CONTENT, claim=claim,
                hypothesis=hypothesis, family_id="family", trial_id="trial",
                seed=1, n=10, edge=float("nan"), noise=1.0, gate_config=gate,
            )
        with self.assertRaisesRegex(ValueError, "family_id and trial_id"):
            freeze_trial(
                source_record=source_record, source_content=CONTENT, claim=claim,
                hypothesis=hypothesis, family_id=123, trial_id="trial",
                seed=1, n=10, edge=0.0, noise=1.0, gate_config=gate,
            )

    def test_gate_input_error_is_preserved_and_trial_is_marked_failed(self):
        spec = frozen()
        spec["gate_config"]["acceptance_thresholds"]["min_sample_size"] = True
        body = {key: value for key, value in spec.items() if key != "frozen_sha256"}
        spec["frozen_sha256"] = sha256_bytes(canonical_bytes(body))
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            with self.assertRaisesRegex(GateConfigError, "min_sample_size"):
                run_synthetic_reproduction(
                    frozen=spec, registry=registry, workspace=Path(tmp) / "runs"
                )
            rows = registry._read_and_verify()
            self.assertEqual([row["outcome"] for row in rows], ["pending", "failed"])
            self.assertEqual(rows[-1]["event_id"], "trial-e2e-1-failed")


    def test_registry_rejects_nonfinite_json_payload_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            with self.assertRaisesRegex(TrialRegistryError, "finite JSON"):
                registry.append(
                    event_id="event-nan", family_id="family-nan", trial_id="trial-nan",
                    outcome="pending", payload={"nonfinite": float("nan")}, max_trials=1,
                )
            self.assertEqual(registry.verify()["event_count"], 0)



    def test_registry_rejects_duplicate_json_object_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.jsonl"
            path.write_text('{"schema_version":1,"schema_version":1}\\n', encoding="utf-8")
            registry = LocalTrialRegistry(path)
            with self.assertRaisesRegex(TrialRegistryError, "duplicate JSON object key"):
                registry.verify()

    def test_registry_rejects_nonstandard_json_numeric_constants(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.jsonl"
            path.write_text('{"payload":{"value":NaN}}\\n', encoding="utf-8")
            registry = LocalTrialRegistry(path)
            with self.assertRaisesRegex(TrialRegistryError, "non-standard JSON numeric constant"):
                registry.verify()

if __name__ == "__main__":
    unittest.main()

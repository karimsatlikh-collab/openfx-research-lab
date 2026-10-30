"""Acceptance and tamper tests for the synthetic-only G0-G2 vertical slice."""
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from openfx.source_provenance import build_source_record, build_atomic_claim, build_hypothesis_card
from openfx.synthetic_e2e import freeze_trial, run_synthetic_reproduction, verify_frozen_trial
from openfx.trial_registry import LocalTrialRegistry

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


if __name__ == "__main__":
    unittest.main()

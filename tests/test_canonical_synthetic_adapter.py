"""Tests for the canonical M1 synthetic adapter; no market claims are made."""
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from openfx.canonical_synthetic_adapter import (
    CanonicalSyntheticAdapterError,
    _validate_manifest,
    run_canonical_synthetic_job,
)
from openfx.source_provenance import (
    build_atomic_claim, build_hypothesis_card, build_source_record,
)
from openfx.synthetic_e2e import freeze_trial
from openfx.synthetic_engine import run_synthetic
from openfx.trial_registry import LocalTrialRegistry, TrialRegistryError


CONTENT = b"Canonical OpenFX synthetic adapter test fixture."
LOCATOR = "fixture://canonical-adapter#claim=1"
STAMP = "2026-10-31T00:00:00Z"


def documents():
    source = build_source_record(
        source_id="canonical-source-1",
        identity="locally authored test fixture",
        rights_basis="owner_created",
        permission_evidence="created for automated tests",
        retrieved_at_utc=STAMP,
        exact_locator=LOCATOR,
        capture_method="inline fixture bytes",
        content=CONTENT,
        provenance_state="test_confirmed",
    )
    claim = build_atomic_claim(
        claim_id="canonical-claim-1",
        source_record=source,
        source_content=CONTENT,
        exact_locator=LOCATOR,
        statement="The test fixture is synthetic.",
        provenance_state="test_confirmed",
    )
    hypothesis = build_hypothesis_card(
        hypothesis_id="canonical-hypothesis-1",
        title="Seeded synthetic replay",
        falsifiable_statement="Same frozen inputs produce identical bytes.",
        linked_claims=[claim],
        predicted_mechanism="Deterministic seeded generator",
        invalidation_criteria="Any replay byte/hash mismatch",
    )
    gate = {
        "schema_version": 1,
        "gate_id": "canonical-synthetic-gate",
        "version": "1.0",
        "frozen_before_trials": True,
        "trial_family_policy": {
            "family_id": "canonical-family",
            "max_trials": 2,
            "count_failures_and_abandoned": True,
        },
        "data_split": {
            "development": "synthetic fixture only",
            "validation": "synthetic fixture only",
            "final_oos": "not applicable to synthetic fixture",
            "final_oos_access_policy": "restricted_human_only",
        },
        "multiple_testing_method": "other_pre_registered",
        "acceptance_thresholds": {"min_sample_size": 20},
        "cost_sensitivity_scenarios": [
            {"scenario_id": "base", "description": "Synthetic costs are not modeled.", "cost_multiplier": 1.0}
        ],
        "created_at_utc": STAMP,
        "notes": "Harness calibration only.",
    }
    strategy = {
        "schema_version": 1,
        "strategy_id": "synthetic-fixture-strategy",
        "version": "1.0",
        "description": "A non-trading synthetic fixture used to test the research adapter.",
        "rules": {
            "entry": [{"rule_id": "entry-1", "statement": "Generate seeded synthetic observations.", "status": "hypothesis"}],
            "exit": [{"rule_id": "exit-1", "statement": "Stop after fixed sample size.", "status": "hypothesis"}],
            "filters": [],
            "risk": [{"rule_id": "risk-1", "statement": "No market risk is modeled.", "status": "unknown"}],
        },
        "claims": [
            {"claim_id": claim["claim_id"], "text": claim["statement"], "label": "source_claim", "source_refs": [source["source_id"]]},
            {"claim_id": "hypothesis-claim", "text": hypothesis["falsifiable_statement"], "label": "hypothesis", "source_refs": [source["source_id"]]},
        ],
        "created_at_utc": STAMP,
        "notes": "Not a live or historical trading strategy.",
    }
    data = {
        "schema_version": 1,
        "profile_id": "synthetic-data-profile",
        "version": "1.0",
        "source": {"provider": "OpenFX test fixture", "dataset_id": "seeded-stream"},
        "symbol": "SYNTHETIC",
        "timeframe": "NA",
        "date_range": {"start_utc": STAMP, "end_utc": "2026-10-31T00:01:00Z"},
        "price_data_mode": "synthetic",
        "timezone": "UTC",
        "data_sha256": hashlib.sha256(CONTENT).hexdigest(),
        "created_at_utc": STAMP,
        "notes": "No market prices.",
    }
    costs = {
        "schema_version": 1,
        "profile_id": "synthetic-cost-profile",
        "version": "1.0",
        "symbol": "SYNTHETIC",
        "spread_model": {"mode": "synthetic", "value_points": 0},
        "commission": {"amount": 0, "currency": "NA", "basis": "per_trade"},
        "slippage": {"model": "none", "value_points": 0},
        "swap": {"model": "none"},
        "symbol_spec": {
            "digits": 0, "point_size": 1, "contract_size": 1,
            "tick_size": 1, "tick_value": 0,
        },
        "created_at_utc": STAMP,
        "notes": "No market costs modeled.",
    }
    engine_path = Path(run_synthetic.__code__.co_filename)
    build_hash = hashlib.sha256(engine_path.read_bytes()).hexdigest()
    from openfx.contract_validation import canonical_sha256
    job = {
        "schema_version": 1,
        "job_id": "canonical-job-1",
        "strategy_spec_ref": {"id": strategy["strategy_id"], "version": strategy["version"], "sha256": canonical_sha256(strategy)},
        "implementation": {"source_revision": "synthetic-engine-test-build", "build_sha256": build_hash},
        "data_profile_ref": {"id": data["profile_id"], "version": data["version"], "sha256": canonical_sha256(data)},
        "cost_profile_ref": {"id": costs["profile_id"], "version": costs["version"], "sha256": canonical_sha256(costs)},
        "gate_config_ref": {"id": gate["gate_id"], "version": gate["version"], "sha256": canonical_sha256(gate)},
        "frozen_parameters": {"seed": 17, "n": 50, "edge": 0.0, "noise": 1.0},
        "budget": {"max_trials": 2, "timeout_seconds": 30},
        "requested_engine": "synthetic",
        "created_at_utc": STAMP,
        "notes": "Synthetic adapter test only.",
    }
    frozen = freeze_trial(
        source_record=source,
        source_content=CONTENT,
        claim=claim,
        hypothesis=hypothesis,
        family_id="canonical-family",
        trial_id="canonical-trial-1",
        seed=17,
        n=50,
        edge=0.0,
        noise=1.0,
        gate_config=gate,
    )
    return job, strategy, data, costs, gate, frozen


class CanonicalSyntheticAdapterTests(unittest.TestCase):
    def test_valid_canonical_job_emits_bound_run_record_and_manifest(self):
        job, strategy, data, costs, gate, frozen = documents()
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            result = run_canonical_synthetic_job(
                job=job, strategy_spec=strategy, data_profile=data,
                cost_profile=costs, gate_config=gate, frozen_trial=frozen,
                registry=registry, workspace=Path(tmp) / "artifacts",
                run_id="canonical-run-1",
            )
            run = result["run_record"]
            manifest = result["artifact_manifest"]
            self.assertEqual(run["status"], "COMPLETED")
            self.assertEqual(run["evidence_level"], "synthetic")
            self.assertEqual(run["inputs"]["job_spec_sha256"], __import__(
                "openfx.contract_validation", fromlist=["canonical_sha256"]
            ).canonical_sha256(job))
            self.assertEqual(len(run["inputs"]), 6)
            self.assertEqual({x["name"] for x in run["outputs"]}, {x["name"] for x in manifest["entries"]})
            self.assertTrue(result["replay_hashes_equal"])
            self.assertFalse(result["is_market_backtest"])
            self.assertEqual(result["registry"]["trial_count"], 1)

    def test_frozen_parameters_must_match_job_spec(self):
        job, strategy, data, costs, gate, frozen = documents()
        job["frozen_parameters"]["seed"] = 99
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            with self.assertRaisesRegex(CanonicalSyntheticAdapterError, "parameters differ"):
                run_canonical_synthetic_job(
                    job=job, strategy_spec=strategy, data_profile=data,
                    cost_profile=costs, gate_config=gate, frozen_trial=frozen,
                    registry=registry, workspace=Path(tmp) / "artifacts",
                    run_id="run-parameter-mismatch",
                )
            self.assertEqual(registry.verify()["event_count"], 0)

    def test_non_synthetic_engine_is_rejected_before_trial_registration(self):
        job, strategy, data, costs, gate, frozen = documents()
        job["requested_engine"] = "mt5-demo"
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            with self.assertRaisesRegex(CanonicalSyntheticAdapterError, "synthetic jobs only"):
                run_canonical_synthetic_job(
                    job=job, strategy_spec=strategy, data_profile=data,
                    cost_profile=costs, gate_config=gate, frozen_trial=frozen,
                    registry=registry, workspace=Path(tmp) / "artifacts",
                    run_id="run-invalid",
                )
            self.assertEqual(registry.verify()["event_count"], 0)

    def test_implementation_digest_mismatch_is_rejected_before_registration(self):
        job, strategy, data, costs, gate, frozen = documents()
        job["implementation"]["build_sha256"] = "0" * 64
        from openfx.contract_validation import canonical_sha256
        job["strategy_spec_ref"]["sha256"] = canonical_sha256(strategy)
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl")
            with self.assertRaisesRegex(CanonicalSyntheticAdapterError, "implementation digest"):
                run_canonical_synthetic_job(
                    job=job, strategy_spec=strategy, data_profile=data,
                    cost_profile=costs, gate_config=gate, frozen_trial=frozen,
                    registry=registry, workspace=Path(tmp) / "artifacts",
                    run_id="run-bad-digest",
                )
            self.assertEqual(registry.verify()["event_count"], 0)

    def test_manifest_rejects_missing_output_entry(self):
        job, strategy, data, costs, gate, frozen = documents()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "a.json"
            artifact.write_text("{}", encoding="utf-8")
            import hashlib
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            run = {"job_id": "job", "run_id": "run", "outputs": [{"name": "a", "sha256": digest}, {"name": "b", "sha256": digest}]}
            manifest = {"schema_version": 1, "job_id": "job", "run_id": "run",
                        "entries": [{"name": "a", "path": "a.json", "size_bytes": 2, "sha256": digest}]}
            with self.assertRaisesRegex(CanonicalSyntheticAdapterError, "count mismatch"):
                _validate_manifest(manifest, run, root)

    def test_registration_lock_failure_prevents_execution(self):
        job, strategy, data, costs, gate, frozen = documents()
        with tempfile.TemporaryDirectory() as tmp:
            registry = LocalTrialRegistry(Path(tmp) / "registry.jsonl", lock_timeout_seconds=0.01)
            registry.lock_path.parent.mkdir(parents=True, exist_ok=True)
            registry.lock_path.write_text("stale", encoding="utf-8")
            with self.assertRaises(TrialRegistryError):
                run_canonical_synthetic_job(
                    job=job, strategy_spec=strategy, data_profile=data,
                    cost_profile=costs, gate_config=gate, frozen_trial=frozen,
                    registry=registry, workspace=Path(tmp) / "artifacts",
                    run_id="run-lock-fail",
                )
            self.assertFalse((Path(tmp) / "artifacts" / "replay_a").exists())


    def test_run_binding_rejects_job_identity_evidence_and_each_contract_digest_mismatch(self):
        job, strategy, data, costs, gate, frozen = documents()
        from openfx.contract_validation import ContractValidationError, validate_run_against_job
        valid = {
            "job_id": job["job_id"],
            "status": "COMPLETED",
            "evidence_level": "synthetic",
            "timestamps": {"created_at_utc": STAMP, "finished_at_utc": STAMP},
            "inputs": {
                "implementation_sha256": job["implementation"]["build_sha256"],
                "strategy_spec_sha256": job["strategy_spec_ref"]["sha256"],
                "data_profile_sha256": job["data_profile_ref"]["sha256"],
                "cost_profile_sha256": job["cost_profile_ref"]["sha256"],
                "gate_config_sha256": job["gate_config_ref"]["sha256"],
            },
        }
        mutations = [
            ("job_id", lambda row: row.update(job_id="other-job")),
            ("evidence_level", lambda row: row.update(evidence_level="mock")),
            ("implementation_sha256", lambda row: row["inputs"].update(implementation_sha256="0" * 64)),
            ("strategy_spec_sha256", lambda row: row["inputs"].update(strategy_spec_sha256="0" * 64)),
            ("data_profile_sha256", lambda row: row["inputs"].update(data_profile_sha256="0" * 64)),
            ("cost_profile_sha256", lambda row: row["inputs"].update(cost_profile_sha256="0" * 64)),
            ("gate_config_sha256", lambda row: row["inputs"].update(gate_config_sha256="0" * 64)),
        ]
        for label, mutate in mutations:
            with self.subTest(binding=label):
                candidate = __import__("copy").deepcopy(valid)
                mutate(candidate)
                with self.assertRaises(ContractValidationError):
                    validate_run_against_job(candidate, job)

    def test_run_record_schema_rejects_unsupported_state(self):
        from openfx.canonical_synthetic_adapter import _validate_schema
        invalid = {
            "schema_version": 1, "run_id": "r1", "job_id": "j1",
            "status": "PENDING", "evidence_level": "synthetic",
            "timestamps": {"created_at_utc": STAMP},
            "inputs": {key: "0" * 64 for key in (
                "job_spec_sha256", "strategy_spec_sha256", "implementation_sha256",
                "data_profile_sha256", "cost_profile_sha256", "gate_config_sha256"
            )},
            "outputs": [], "error": None,
        }
        with self.assertRaisesRegex(CanonicalSyntheticAdapterError, "schema validation failed"):
            _validate_schema(invalid, "run")

    def test_manifest_rejects_extra_output_entry(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entries = []
            outputs = []
            for name in ("a", "b"):
                path = root / f"{name}.json"
                path.write_text("{}", encoding="utf-8")
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                entries.append({"name": name, "path": f"{name}.json", "size_bytes": 2, "sha256": digest})
                outputs.append({"name": name, "sha256": digest})
            run = {"job_id": "job", "run_id": "run", "outputs": outputs}
            manifest = {"schema_version": 1, "job_id": "job", "run_id": "run", "entries": entries}
            _validate_manifest(manifest, run, root)
            manifest["entries"].append(dict(entries[0], name="extra", path="extra.json"))
            extra = root / "extra.json"
            extra.write_text("{}", encoding="utf-8")
            manifest["entries"][-1]["sha256"] = hashlib.sha256(extra.read_bytes()).hexdigest()
            with self.assertRaisesRegex(CanonicalSyntheticAdapterError, "count mismatch"):
                _validate_manifest(manifest, run, root)

    def test_execution_failure_after_registration_is_recorded_as_failed(self):
        job, strategy, data, costs, gate, frozen = documents()
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "registry.jsonl"
            registry = LocalTrialRegistry(registry_path)
            with patch("openfx.canonical_synthetic_adapter._execute_once", side_effect=RuntimeError("injected execution failure")):
                with self.assertRaisesRegex(RuntimeError, "injected execution failure"):
                    run_canonical_synthetic_job(
                        job=job, strategy_spec=strategy, data_profile=data,
                        cost_profile=costs, gate_config=gate, frozen_trial=frozen,
                        registry=registry, workspace=Path(tmp) / "artifacts",
                        run_id="run-post-registration-failure",
                    )
            rows = [__import__("json").loads(line) for line in registry_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["outcome"] for row in rows], ["pending", "failed"])
            self.assertEqual(registry.verify()["trial_count"], 1)


if __name__ == "__main__":
    unittest.main()

"""Canonical M1 contract adapter for the synthetic-only research engine.

This adapter does not authorize external execution and is not market evidence.
It binds canonical v1 documents, registers before execution, and validates the
persisted artifacts before closing the trial.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openfx.contract_validation import (
    canonical_sha256,
    validate_job_bundle,
    validate_run_against_job,
)
from openfx.statistical_gate import evaluate_registered_synthetic_summary
from openfx.synthetic_e2e import _execute_once, verify_frozen_trial
from openfx.synthetic_engine import run_synthetic
from openfx.trial_registry import LocalTrialRegistry


SCHEMA_FILES = {
    "strategy": "strategy-spec-v1.schema.json",
    "data": "data-profile-v1.schema.json",
    "cost": "cost-profile-v1.schema.json",
    "gate": "gate-config-v1.schema.json",
    "job": "job-spec-v1.schema.json",
    "run": "run-record-v1.schema.json",
    "verdict": "gate-verdict-v1.schema.json",
}


class CanonicalSyntheticAdapterError(ValueError):
    """Canonical contract, execution, or artifact validation failed."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_timestamp() -> str:
    """Capture an actual lifecycle boundary at UTC microsecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _build_canonical_gate_verdict(
    *,
    run_id: str,
    gate_config: dict[str, Any],
    evaluation: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Bind the descriptive evaluation to the frozen canonical GateConfig."""
    thresholds = gate_config["acceptance_thresholds"]
    checks: list[dict[str, Any]] = []
    for key, threshold in sorted(thresholds.items()):
        observed = summary[key.removeprefix("min_")]
        passed = observed >= threshold
        checks.append({
            "check_id": key,
            "status": "pass" if passed else "fail",
            "description": f"Observed {key.removeprefix('min_')} compared with frozen {key} threshold.",
            "observed_value": observed,
            "threshold": threshold,
        })

    family_policy = gate_config["trial_family_policy"]
    trial_count = evaluation["trial_count"]
    max_trials = family_policy["max_trials"]
    checks.append({
        "check_id": "trial_family_budget",
        "status": "pass" if trial_count <= max_trials else "fail",
        "description": "Registered trial count compared with the frozen family trial cap.",
        "observed_value": trial_count,
        "threshold": max_trials,
    })
    checks.append({
        "check_id": "multiple_testing_correction",
        "status": "not_run",
        "description": (
            f"{gate_config['multiple_testing_method']} is recorded as the pre-registered "
            "method; this synthetic descriptive gate does not calculate the correction."
        ),
        "observed_value": False,
        "threshold": gate_config["multiple_testing_method"],
    })

    return {
        "schema_version": 1,
        "verdict_id": f"{run_id}-gate-verdict",
        "run_id": run_id,
        "decision": evaluation["decision"],
        "gate_version": gate_config["version"],
        "gate_config_sha256": canonical_sha256(gate_config),
        "trial_family_id": family_policy["family_id"],
        "trial_count_at_decision": trial_count,
        "checks": checks,
        "created_at_utc": _utc_timestamp(),
        "limitations": list(evaluation["limitations"]),
        "notes": "Synthetic descriptive verdict only; not a market-performance conclusion.",
    }


def _validate_schema(document: dict[str, Any], schema_name: str) -> None:
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / SCHEMA_FILES[schema_name]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalSyntheticAdapterError(
            f"cannot load canonical {schema_name} schema"
        ) from exc
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise CanonicalSyntheticAdapterError(
            f"{schema_name} schema validation failed at {location}: {first.message}"
        )


def _manifest_entry(name: str, path: Path, root: Path, expected_hash: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CanonicalSyntheticAdapterError(f"artifact is not a regular non-symlink file: {name}")
    resolved_root = root.resolve(strict=True)
    resolved_path = path.resolve(strict=True)
    if resolved_root not in resolved_path.parents:
        raise CanonicalSyntheticAdapterError(f"artifact escapes workspace: {name}")
    raw = path.read_bytes()
    measured_hash = _sha256_bytes(raw)
    if measured_hash != expected_hash:
        raise CanonicalSyntheticAdapterError(f"artifact hash mismatch: {name}")
    return {
        "name": name,
        "path": path.relative_to(root).as_posix(),
        "size_bytes": len(raw),
        "sha256": measured_hash,
    }


def _validate_manifest(manifest: dict[str, Any], run_record: dict[str, Any],
                       workspace: Path) -> None:
    if set(manifest) != {"schema_version", "job_id", "run_id", "entries"}:
        raise CanonicalSyntheticAdapterError("artifact manifest has unsupported fields")
    if manifest["schema_version"] != 1:
        raise CanonicalSyntheticAdapterError("unsupported artifact manifest version")
    if manifest["job_id"] != run_record["job_id"] or manifest["run_id"] != run_record["run_id"]:
        raise CanonicalSyntheticAdapterError("artifact manifest identity mismatch")
    entries = manifest["entries"]
    outputs = run_record["outputs"]
    if not isinstance(entries, list) or len(entries) != len(outputs):
        raise CanonicalSyntheticAdapterError("artifact manifest/output count mismatch")
    if len({entry["name"] for entry in entries}) != len(entries):
        raise CanonicalSyntheticAdapterError("duplicate artifact names")
    if len({entry["path"] for entry in entries}) != len(entries):
        raise CanonicalSyntheticAdapterError("duplicate artifact paths")
    output_map = {item["name"]: item["sha256"] for item in outputs}
    if set(output_map) != {entry["name"] for entry in entries}:
        raise CanonicalSyntheticAdapterError("artifact manifest names do not exactly match RunRecord outputs")
    for entry in entries:
        relative = Path(entry["path"])
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise CanonicalSyntheticAdapterError("unsafe artifact path")
        if "\\" in entry["path"] or ":" in entry["path"]:
            raise CanonicalSyntheticAdapterError("non-POSIX or drive-qualified artifact path")
        path = workspace / relative
        cursor = workspace
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise CanonicalSyntheticAdapterError("artifact path contains a symlink component")
        if not path.is_file():
            raise CanonicalSyntheticAdapterError("artifact must be a regular file")
        resolved_root = workspace.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
        if resolved_root not in resolved_path.parents:
            raise CanonicalSyntheticAdapterError("artifact path escapes the read-only workspace")
        raw = path.read_bytes()
        if len(raw) != entry["size_bytes"] or _sha256_bytes(raw) != entry["sha256"]:
            raise CanonicalSyntheticAdapterError("artifact size/hash verification failed")
        if entry["sha256"] != output_map[entry["name"]]:
            raise CanonicalSyntheticAdapterError("manifest digest differs from RunRecord output digest")


def run_canonical_synthetic_job(
    *,
    job: dict[str, Any],
    strategy_spec: dict[str, Any],
    data_profile: dict[str, Any],
    cost_profile: dict[str, Any],
    gate_config: dict[str, Any],
    frozen_trial: dict[str, Any],
    registry: LocalTrialRegistry,
    workspace: str | Path,
    run_id: str,
) -> dict[str, Any]:
    """Validate, register, execute twice, and emit canonical RunRecord v1.

    The implementation digest in JobSpec must equal the actual bytes of
    synthetic_engine.py. This narrow check prevents a caller from relabelling
    a different synthetic engine build while keeping this slice synthetic-only.
    """
    if job.get("requested_engine") != "synthetic":
        raise CanonicalSyntheticAdapterError("adapter accepts synthetic jobs only")
    if not isinstance(run_id, str) or not run_id.strip():
        raise CanonicalSyntheticAdapterError("run_id is required")

    documents = {
        "strategy": strategy_spec, "data": data_profile, "cost": cost_profile,
        "gate": gate_config, "job": job,
    }
    for name, document in documents.items():
        _validate_schema(document, name)

    validate_job_bundle(
        job, strategy_spec=strategy_spec, data_profile=data_profile,
        cost_profile=cost_profile, gate_config=gate_config,
    )
    frozen_hash = verify_frozen_trial(frozen_trial)
    if frozen_trial.get("gate_config") != gate_config:
        raise CanonicalSyntheticAdapterError("frozen trial gate config differs from canonical GateConfig")
    if frozen_trial.get("engine_parameters") != job.get("frozen_parameters"):
        raise CanonicalSyntheticAdapterError("frozen trial parameters differ from JobSpec frozen_parameters")
    family_id = gate_config["trial_family_policy"]["family_id"]
    trial_id = frozen_trial["trial_id"]
    if frozen_trial.get("family_id") != family_id:
        raise CanonicalSyntheticAdapterError("frozen trial family differs from canonical GateConfig")
    if job["budget"]["max_trials"] > gate_config["trial_family_policy"]["max_trials"]:
        raise CanonicalSyntheticAdapterError("JobSpec trial budget exceeds frozen GateConfig")

    engine_path = Path(run_synthetic.__code__.co_filename).resolve()
    engine_digest = _sha256_bytes(engine_path.read_bytes())
    if job["implementation"]["build_sha256"].lower() != engine_digest:
        raise CanonicalSyntheticAdapterError("JobSpec implementation digest does not match synthetic_engine.py bytes")

    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Do not overwrite an earlier run's artifacts.
    if (root / "replay_a").exists() or (root / "replay_b").exists():
        raise CanonicalSyntheticAdapterError("workspace already contains replay artifacts")

    # These timestamps are captured at their actual lifecycle boundaries.
    # created_at marks acceptance of the validated run request immediately
    # before durable registration; started_at/finished_at bracket both replays.
    created_at = _utc_timestamp()
    registry.append(
        event_id=f"{trial_id}-canonical-registered",
        family_id=family_id, trial_id=trial_id, outcome="pending",
        payload={
            "frozen_sha256": frozen_hash,
            "job_id": job["job_id"],
            "job_spec_sha256": canonical_sha256(job),
            "evidence_level": "synthetic",
            "adapter": "canonical-m1-v1",
        },
        max_trials=min(
            job["budget"]["max_trials"],
            gate_config["trial_family_policy"]["max_trials"],
        ),
        reject_existing_trial=True,
    )
    terminal_recorded = False
    try:
        # Verify the durable registration before allowing any execution side effect.
        registration_verification = registry.verify()
        if not registration_verification.get("valid"):
            raise CanonicalSyntheticAdapterError("trial registry verification failed after registration")
        started_at = _utc_timestamp()
        a = _execute_once(frozen_trial, root / "replay_a")
        b = _execute_once(frozen_trial, root / "replay_b")
        finished_at = _utc_timestamp()
        if a["artifact_sha256"] != b["artifact_sha256"] or a["record"] != b["record"]:
            raise CanonicalSyntheticAdapterError("deterministic replay artifacts differ")

        outputs = [
            {"name": "replay_a/run_record.json", "sha256": a["artifact_sha256"],
             "media_type": "application/json"},
            {"name": "replay_b/run_record.json", "sha256": b["artifact_sha256"],
             "media_type": "application/json"},
        ]
        run_record = {
            "schema_version": 1,
            "run_id": run_id,
            "job_id": job["job_id"],
            "status": "COMPLETED",
            "evidence_level": "synthetic",
            "timestamps": {
                "created_at_utc": created_at,
                "started_at_utc": started_at,
                "finished_at_utc": finished_at,
            },
            "inputs": {
                "job_spec_sha256": canonical_sha256(job),
                "strategy_spec_sha256": job["strategy_spec_ref"]["sha256"],
                "implementation_sha256": job["implementation"]["build_sha256"].lower(),
                "data_profile_sha256": job["data_profile_ref"]["sha256"],
                "cost_profile_sha256": job["cost_profile_ref"]["sha256"],
                "gate_config_sha256": job["gate_config_ref"]["sha256"],
            },
            "outputs": outputs,
            "error": None,
            "notes": "Synthetic deterministic replay only; not a market backtest or independent replication.",
        }
        _validate_schema(run_record, "run")
        validate_run_against_job(run_record, job)
        if run_record["inputs"]["job_spec_sha256"] != canonical_sha256(job):
            raise CanonicalSyntheticAdapterError("RunRecord job_spec_sha256 does not bind the complete JobSpec")

        manifest = {
            "schema_version": 1,
            "job_id": job["job_id"],
            "run_id": run_id,
            "entries": [
                _manifest_entry(outputs[0]["name"], root / "replay_a" / "run_record.json",
                                root, outputs[0]["sha256"]),
                _manifest_entry(outputs[1]["name"], root / "replay_b" / "run_record.json",
                                root, outputs[1]["sha256"]),
            ],
        }
        _validate_manifest(manifest, run_record, root)
        verdict = evaluate_registered_synthetic_summary(
            a["record"]["result"], gate_config, registry=registry, family_id=family_id,
        )
        canonical_verdict = _build_canonical_gate_verdict(
            run_id=run_id, gate_config=gate_config, evaluation=verdict,
            summary=a["record"]["result"],
        )
        _validate_schema(canonical_verdict, "verdict")
        gate_verdict_digest = _sha256_bytes(_canonical_bytes(canonical_verdict))
        registry.append(
            event_id=f"{trial_id}-canonical-completed",
            family_id=family_id, trial_id=trial_id, outcome="completed",
            payload={
                "job_id": job["job_id"], "run_id": run_id,
                "run_record_sha256": _sha256_bytes(_canonical_bytes(run_record)),
                "artifact_manifest_sha256": _sha256_bytes(_canonical_bytes(manifest)),
                "gate_decision": verdict["decision"],
                "gate_verdict_sha256": gate_verdict_digest,
                "evidence_level": "synthetic",
            },
        )
        terminal_recorded = True
        final_registry_verification = registry.verify()
        if not final_registry_verification.get("valid"):
            raise CanonicalSyntheticAdapterError("trial registry verification failed after completion")
        return {
            "run_record": run_record,
            "artifact_manifest": manifest,
            "gate_verdict": verdict,
            "canonical_gate_verdict": canonical_verdict,
            "registry": final_registry_verification,
            "replay_hashes_equal": True,
            "evidence_level": "synthetic",
            "is_market_backtest": False,
            "limitations": [
                "Synthetic fixture only; no market data, MT5, broker costs, or profitability evidence.",
                "Two deterministic runs use the same code and are not independent replication.",
                "The local JSONL registry is not a trusted central registrar or tamper-proof store.",
                "The descriptive synthetic gate does not calculate DSR, PBO, or family-wise error correction.",
                "RunRecord and artifact manifest integrity do not attest that a trusted external executor ran.",
            ],
        }
    except BaseException as exc:
        if not terminal_recorded:
            terminal_outcome = "interrupted" if not isinstance(exc, Exception) else "failed"
            registry.append(
                event_id=f"{trial_id}-canonical-{terminal_outcome}",
                family_id=family_id, trial_id=trial_id, outcome=terminal_outcome,
                payload={
                    "job_id": job["job_id"], "run_id": run_id,
                    "error_type": type(exc).__name__,
                    "reason": "interrupted" if terminal_outcome == "interrupted" else "execution_error",
                    "finished_at_utc": _utc_timestamp(),
                    "evidence_level": "synthetic",
                },
            )
            registry.verify()
        raise

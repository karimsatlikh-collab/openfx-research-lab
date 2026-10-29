"""Semantic checks across OpenFX contract documents.

These checks complement JSON Schema validation; they do not authorize execution,
attest an engine, or establish scientific validity.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


class ContractValidationError(ValueError):
    """Raised when individually valid documents contradict one another."""


def canonical_sha256(document: dict[str, Any]) -> str:
    """Hash a JSON document using stable UTF-8 canonical serialization."""
    raw = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractValidationError(message)


def validate_job_bundle(
    job: dict[str, Any],
    *,
    strategy_spec: dict[str, Any],
    data_profile: dict[str, Any],
    cost_profile: dict[str, Any],
    gate_config: dict[str, Any],
) -> dict[str, Any]:
    """Check immutable reference identity/version/hash and budget-policy consistency.

    Reference SHA-256 values are defined here as hashes of canonical JSON documents.
    Schema validation remains a separate prerequisite.
    """
    refs = (
        ("strategy_spec_ref", strategy_spec, "strategy_id"),
        ("data_profile_ref", data_profile, "profile_id"),
        ("cost_profile_ref", cost_profile, "profile_id"),
        ("gate_config_ref", gate_config, "gate_id"),
    )
    for ref_key, document, id_key in refs:
        ref = job.get(ref_key)
        _require(isinstance(ref, dict), f"{ref_key} must be an object")
        _require(ref.get("id") == document.get(id_key),
                 f"{ref_key}.id does not match referenced document")
        _require(ref.get("version") == document.get("version"),
                 f"{ref_key}.version does not match referenced document")
        _require(ref.get("sha256") == canonical_sha256(document),
                 f"{ref_key}.sha256 does not match canonical document hash")

    implementation = job.get("implementation")
    budget = job.get("budget")
    policy = gate_config.get("trial_family_policy")
    _require(isinstance(implementation, dict) and bool(implementation.get("source_revision")),
             "implementation source_revision is required")
    _require(isinstance(budget, dict), "job budget is required")
    _require(isinstance(budget.get("max_trials"), int) and not isinstance(budget.get("max_trials"), bool)
             and budget["max_trials"] >= 1, "budget.max_trials must be a positive integer")
    _require(isinstance(budget.get("timeout_seconds"), int)
             and not isinstance(budget.get("timeout_seconds"), bool)
             and budget["timeout_seconds"] >= 1, "budget.timeout_seconds must be a positive integer")
    _require(isinstance(policy, dict), "gate trial_family_policy is required")
    _require(policy.get("count_failures_and_abandoned") is True,
             "gate policy must count failures and abandoned trials")
    _require(isinstance(policy.get("max_trials"), int) and not isinstance(policy.get("max_trials"), bool) and policy["max_trials"] >= 1,
             "gate max_trials must be a positive integer")
    _require(budget["max_trials"] <= policy["max_trials"],
             "job trial budget exceeds the frozen gate family budget")
    _require(gate_config.get("frozen_before_trials") is True,
             "gate config must be frozen before trials")
    return {
        "valid": True,
        "job_id": job.get("job_id"),
        "requested_engine": job.get("requested_engine"),
        "max_trials": budget["max_trials"],
        "gate_max_trials": policy["max_trials"],
        "limitations": [
            "Semantic consistency only; no execution authorization.",
            "A matching engine label is not engine attestation.",
            "Validation does not establish scientific validity or profitability.",
        ],
    }


def validate_run_against_job(run: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    """Check a RunRecord's job binding and evidence label consistency."""
    _require(run.get("job_id") == job.get("job_id"), "run.job_id does not match JobSpec")
    _require(run.get("evidence_level") == job.get("requested_engine"),
             "run evidence_level does not match requested_engine")
    inputs = run.get("inputs")
    _require(isinstance(inputs, dict), "run.inputs is required")
    _require(inputs.get("implementation_sha256") ==
             job.get("implementation", {}).get("build_sha256"),
             "run implementation hash does not match JobSpec build hash")
    expected = {
        "strategy_spec_sha256": job.get("strategy_spec_ref", {}).get("sha256"),
        "data_profile_sha256": job.get("data_profile_ref", {}).get("sha256"),
        "cost_profile_sha256": job.get("cost_profile_ref", {}).get("sha256"),
        "gate_config_sha256": job.get("gate_config_ref", {}).get("sha256"),
    }
    for key, value in expected.items():
        _require(inputs.get(key) == value, f"run {key} does not match JobSpec reference")
    if run.get("status") == "COMPLETED":
        timestamps = run.get("timestamps", {})
        _require(bool(timestamps.get("finished_at_utc")),
                 "COMPLETED run must have finished_at_utc")
    # Deliberately do not infer a positive or negative performance result from status.
    return {
        "valid": True,
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "evidence_level": run.get("evidence_level"),
        "performance_conclusion": "not_inferred_from_run_status",
        "limitations": [
            "Evidence label consistency is not proof that the named engine actually ran.",
            "COMPLETED means lifecycle completion only, not strategy success.",
        ],
    }


RUN_TRANSITIONS = {
    "QUEUED": {"VALIDATED", "REJECTED", "CANCELLED", "FAILED"},
    "VALIDATED": {"APPROVED", "REJECTED", "CANCELLED", "FAILED"},
    "APPROVED": {"RUNNING", "CANCELLED", "FAILED"},
    "RUNNING": {"VERIFYING", "FAILED", "TIMEOUT", "INTERRUPTED"},
    "VERIFYING": {"COMPLETED", "FAILED", "INTERRUPTED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "TIMEOUT": set(),
    "INTERRUPTED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}


def validate_run_transition(old_status: str, new_status: str) -> None:
    """Reject illegal lifecycle transitions for RunRecord status values."""
    if old_status not in RUN_TRANSITIONS:
        raise ContractValidationError(f"unknown old status: {old_status}")
    if new_status not in RUN_TRANSITIONS[old_status]:
        raise ContractValidationError(f"illegal run transition: {old_status} -> {new_status}")

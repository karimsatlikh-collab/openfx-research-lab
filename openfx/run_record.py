"""Strict RunRecord v1 contract, separate from the legacy experiment manifest.

This module validates the RunRecord shape and lifecycle only. It does not
authenticate approvers, prove evidence provenance, persist atomically, or run
MT5. In particular, selecting evidence_level="mt5-demo" is only a declaration.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = 1
RUN_STATUSES = frozenset({
    "QUEUED", "VALIDATED", "APPROVED", "RUNNING", "VERIFYING",
    "COMPLETED", "FAILED", "TIMEOUT", "INTERRUPTED", "REJECTED", "CANCELLED",
})
EVIDENCE_LEVELS = frozenset({"mock", "synthetic", "mt5-demo"})
TERMINAL_STATUSES = frozenset({
    "COMPLETED", "FAILED", "TIMEOUT", "INTERRUPTED", "REJECTED", "CANCELLED",
})
_ALLOWED_TRANSITIONS = {
    "QUEUED": {"VALIDATED", "REJECTED", "CANCELLED"},
    "VALIDATED": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"RUNNING", "CANCELLED"},
    "RUNNING": {"VERIFYING", "FAILED", "TIMEOUT", "INTERRUPTED"},
    "VERIFYING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(), "FAILED": set(), "TIMEOUT": set(),
    "INTERRUPTED": set(), "REJECTED": set(), "CANCELLED": set(),
}
_HASH_FIELDS = (
    "job_spec_sha256", "strategy_spec_sha256", "implementation_sha256",
    "data_profile_sha256", "cost_profile_sha256", "gate_config_sha256",
)
_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_FAILURE_STATUSES = {"FAILED", "TIMEOUT", "INTERRUPTED", "REJECTED"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def validate_run_record(record: dict[str, Any]) -> None:
    """Raise ValueError unless record satisfies the RunRecord v1 contract.

    This is an explicit dependency-free validator for the schema's supported
    constraints, not a general JSON Schema implementation.
    """
    if not isinstance(record, dict):
        raise ValueError("RunRecord must be an object")
    required = {"schema_version", "run_id", "job_id", "status", "evidence_level",
                "timestamps", "inputs", "outputs", "error"}
    if set(record) - (required | {"notes"}) or required - set(record):
        raise ValueError("RunRecord has missing or unknown top-level fields")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")
    for field in ("run_id", "job_id"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if record["status"] not in RUN_STATUSES:
        raise ValueError("invalid run status")
    if record["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError("invalid evidence_level")
    if "notes" in record and not isinstance(record["notes"], str):
        raise ValueError("notes must be a string")

    timestamps = record["timestamps"]
    if not isinstance(timestamps, dict) or set(timestamps) - {
        "created_at_utc", "started_at_utc", "finished_at_utc"
    } or "created_at_utc" not in timestamps:
        raise ValueError("invalid timestamps object")
    if not _valid_datetime(timestamps["created_at_utc"]):
        raise ValueError("created_at_utc must be an ISO-8601 date-time with timezone")
    for field in ("started_at_utc", "finished_at_utc"):
        value = timestamps.get(field)
        if value is not None and not _valid_datetime(value):
            raise ValueError(f"{field} must be null or an ISO-8601 date-time with timezone")
    status = record["status"]
    started = timestamps.get("started_at_utc")
    finished = timestamps.get("finished_at_utc")
    if status in {"RUNNING", "VERIFYING", "COMPLETED", "FAILED", "TIMEOUT", "INTERRUPTED"} and not started:
        raise ValueError("started_at_utc is required once execution has started")
    if status in TERMINAL_STATUSES and not finished:
        raise ValueError("finished_at_utc is required for terminal statuses")
    if status not in TERMINAL_STATUSES and finished is not None:
        raise ValueError("finished_at_utc must be null before a terminal status")
    if status in _FAILURE_STATUSES:
        if not isinstance(record["error"], str) or not record["error"].strip():
            raise ValueError(f"error is required for {status}")
    elif record["error"] is not None:
        raise ValueError("error must be null for non-failure statuses")
    if record["error"] is not None and (
        not isinstance(record["error"], str) or len(record["error"]) > 4000
    ):
        raise ValueError("error must be null or a string of at most 4000 characters")

    inputs = record["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != set(_HASH_FIELDS):
        raise ValueError("inputs must contain exactly the six required SHA-256 fields")
    for field, digest in inputs.items():
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ValueError(f"{field} must be a 64-character SHA-256 hex digest")
    outputs = record["outputs"]
    if not isinstance(outputs, list):
        raise ValueError("outputs must be an array")
    for output in outputs:
        if not isinstance(output, dict) or set(output) - {"name", "sha256", "media_type"}:
            raise ValueError("invalid output artifact object")
        if not isinstance(output.get("name"), str) or not output["name"].strip():
            raise ValueError("output name must be a non-empty string")
        if not isinstance(output.get("sha256"), str) or not _SHA256_RE.fullmatch(output["sha256"]):
            raise ValueError("output sha256 must be a 64-character hex digest")
        if "media_type" in output and not isinstance(output["media_type"], str):
            raise ValueError("output media_type must be a string")


def new_run_record(
    run_id: str, job_id: str, evidence_level: str, inputs: dict[str, str],
    *, notes: str = "",
) -> dict[str, Any]:
    """Create a QUEUED RunRecord. Evidence level is a declaration, not proof."""
    record = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "job_id": job_id,
        "status": "QUEUED",
        "evidence_level": evidence_level,
        "timestamps": {
            "created_at_utc": _utc_now(),
            "started_at_utc": None,
            "finished_at_utc": None,
        },
        "inputs": copy.deepcopy(inputs),
        "outputs": [],
        "error": None,
    }
    if notes:
        record["notes"] = notes
    validate_run_record(record)
    return record


def transition_run_record(
    record: dict[str, Any], new_status: str, *,
    outputs: list[dict[str, str]] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Return a validated copy after one legal lifecycle transition.

    This pure in-memory operation is not a concurrency-safe persistence layer.
    COMPLETED means the run's VERIFYING stage concluded; it does not mean an
    independent validator or statistical gate approved the result.
    """
    validate_run_record(record)
    old_status = record["status"]
    if new_status not in _ALLOWED_TRANSITIONS[old_status]:
        raise ValueError(f"illegal RunRecord transition: {old_status} -> {new_status}")
    updated = copy.deepcopy(record)
    now = _utc_now()
    updated["status"] = new_status
    if new_status == "RUNNING":
        updated["timestamps"]["started_at_utc"] = now
    if new_status in TERMINAL_STATUSES:
        updated["timestamps"]["finished_at_utc"] = now
    if new_status in _FAILURE_STATUSES:
        if not isinstance(error, str) or not error.strip():
            raise ValueError(f"error is required when transitioning to {new_status}")
        updated["error"] = error[:4000]
    elif error is not None:
        raise ValueError("error is only accepted for failure/rejection transitions")
    if outputs is not None:
        updated["outputs"] = copy.deepcopy(outputs)
    validate_run_record(updated)
    return updated

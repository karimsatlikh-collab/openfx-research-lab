"""Versioned experiment records and safe state transitions.

This module deliberately does not launch MT5, run shell commands, or trade.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
STATES = {"QUEUED", "RUNNING", "COMPLETED", "FAILED"}
_ALLOWED_TRANSITIONS = {
    "QUEUED": {"RUNNING", "FAILED"},
    "RUNNING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": set(),
}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def new_experiment(
    experiment_id: str,
    hypothesis: str,
    strategy_version: str,
    symbol: str,
    timeframe: str,
    data_start: str,
    data_end: str,
    parameters: dict[str, Any] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Create a validated, reproducible experiment manifest."""
    if not _ID_RE.fullmatch(experiment_id):
        raise ValueError("experiment_id must be 1-80 safe filename characters")
    required = {
        "hypothesis": hypothesis,
        "strategy_version": strategy_version,
        "symbol": symbol,
        "timeframe": timeframe,
        "data_start": data_start,
        "data_end": data_end,
    }
    for key, value in required.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
    if data_start > data_end:
        raise ValueError("data_start must not be later than data_end")

    now = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "created_at_utc": now,
        "updated_at_utc": now,
        "status": "QUEUED",
        "hypothesis": hypothesis.strip(),
        "strategy_version": strategy_version.strip(),
        "market": {
            "symbol": symbol.strip().upper(),
            "timeframe": timeframe.strip().upper(),
            "data_start": data_start,
            "data_end": data_end,
        },
        "parameters": parameters or {},
        "execution": {
            "mode": "mock",
            "worker_version": None,
            "started_at_utc": None,
            "finished_at_utc": None,
        },
        "result": None,
        "artifacts": [],
        "notes": notes,
    }


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Raise ValueError if the minimum manifest contract is not met."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported or missing schema_version")
    experiment_id = manifest.get("experiment_id")
    if not isinstance(experiment_id, str) or not _ID_RE.fullmatch(experiment_id):
        raise ValueError("invalid experiment_id")
    if manifest.get("status") not in STATES:
        raise ValueError("invalid status")
    for key in ("hypothesis", "strategy_version", "market", "execution", "artifacts"):
        if key not in manifest:
            raise ValueError(f"missing required field: {key}")
    if not isinstance(manifest["market"], dict):
        raise ValueError("market must be an object")
    if not isinstance(manifest["execution"], dict):
        raise ValueError("execution must be an object")
    if not isinstance(manifest["artifacts"], list):
        raise ValueError("artifacts must be a list")


def transition(
    manifest: dict[str, Any],
    new_status: str,
    *,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Return a transitioned copy, rejecting illegal state changes."""
    validate_manifest(manifest)
    old_status = manifest["status"]
    if new_status not in _ALLOWED_TRANSITIONS[old_status]:
        raise ValueError(f"illegal experiment transition: {old_status} -> {new_status}")
    updated = json.loads(json.dumps(manifest))
    now = utc_now()
    updated["status"] = new_status
    updated["updated_at_utc"] = now
    if new_status == "RUNNING":
        updated["execution"]["started_at_utc"] = now
    if new_status in {"COMPLETED", "FAILED"}:
        updated["execution"]["finished_at_utc"] = now
    if result is not None:
        updated["result"] = result
    if error is not None:
        updated["error"] = error[:2000]
    validate_manifest(updated)
    return updated


def save_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    """Validate and atomically write a JSON manifest."""
    validate_manifest(manifest)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be a JSON object")
    validate_manifest(manifest)
    return manifest

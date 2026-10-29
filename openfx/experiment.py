"""Versioned experiment records and safe state transitions.

This module deliberately does not launch MT5, run shell commands, or trade.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
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
    _validate_iso_date(data_start, "data_start")
    _validate_iso_date(data_end, "data_end")
    if date.fromisoformat(data_start) > date.fromisoformat(data_end):
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


def _validate_iso_date(value: Any, field: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} must use YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field} must be a real calendar date") from None


def _validate_datetime(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field} must be an ISO-8601 datetime") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Validate required fields and nested data without optional dependencies."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be a JSON object")
    required = {
        "schema_version", "experiment_id", "created_at_utc", "updated_at_utc",
        "status", "hypothesis", "strategy_version", "market", "parameters",
        "execution", "result", "artifacts", "notes",
    }
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported or missing schema_version")
    experiment_id = manifest.get("experiment_id")
    if not isinstance(experiment_id, str) or not _ID_RE.fullmatch(experiment_id):
        raise ValueError("invalid experiment_id")
    if manifest.get("status") not in STATES:
        raise ValueError("invalid status")
    for key in ("hypothesis", "strategy_version", "notes"):
        if not isinstance(manifest[key], str) or (key != "notes" and not manifest[key].strip()):
            raise ValueError(f"{key} must be a string" + (" and non-empty" if key != "notes" else ""))
    _validate_datetime(manifest["created_at_utc"], "created_at_utc")
    _validate_datetime(manifest["updated_at_utc"], "updated_at_utc")
    market = manifest["market"]
    if not isinstance(market, dict):
        raise ValueError("market must be an object")
    for key in ("symbol", "timeframe"):
        if not isinstance(market.get(key), str) or not market[key].strip():
            raise ValueError(f"market.{key} must be a non-empty string")
    _validate_iso_date(market.get("data_start"), "market.data_start")
    _validate_iso_date(market.get("data_end"), "market.data_end")
    if date.fromisoformat(market["data_start"]) > date.fromisoformat(market["data_end"]):
        raise ValueError("market.data_start must not be later than market.data_end")
    if not isinstance(manifest["parameters"], dict):
        raise ValueError("parameters must be an object")
    execution = manifest["execution"]
    if not isinstance(execution, dict):
        raise ValueError("execution must be an object")
    for key in ("mode", "worker_version", "started_at_utc", "finished_at_utc"):
        if key not in execution:
            raise ValueError(f"execution missing required field: {key}")
    if not isinstance(execution["mode"], str) or not execution["mode"]:
        raise ValueError("execution.mode must be a non-empty string")
    if execution["worker_version"] is not None and not isinstance(execution["worker_version"], str):
        raise ValueError("execution.worker_version must be a string or null")
    for key in ("started_at_utc", "finished_at_utc"):
        if execution[key] is not None:
            _validate_datetime(execution[key], f"execution.{key}")
    if not isinstance(manifest["artifacts"], list):
        raise ValueError("artifacts must be a list")
    for index, artifact in enumerate(manifest["artifacts"]):
        if not isinstance(artifact, dict):
            raise ValueError(f"artifacts[{index}] must be an object")
        if not isinstance(artifact.get("path"), str) or not artifact["path"]:
            raise ValueError(f"artifacts[{index}].path must be a non-empty string")
        size = artifact.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"artifacts[{index}].size_bytes must be a non-negative integer")
        if not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[a-fA-F0-9]{64}", artifact["sha256"]):
            raise ValueError(f"artifacts[{index}].sha256 must be a SHA-256 digest")
    if manifest["result"] is not None and not isinstance(manifest["result"], dict):
        raise ValueError("result must be an object or null")
    if manifest["status"] == "COMPLETED" and not manifest["result"]:
        raise ValueError("COMPLETED requires a non-empty structured result")
    if "error" in manifest and (not isinstance(manifest["error"], str) or len(manifest["error"]) > 2000):
        raise ValueError("error must be a string of at most 2000 characters")


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
        if not isinstance(result, dict):
            raise ValueError("result must be a structured object")
        updated["result"] = result
    if new_status == "COMPLETED" and not updated.get("result"):
        raise ValueError("COMPLETED requires a non-empty structured result")
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


def artifact_record(path: str | Path, root: str | Path) -> dict[str, Any]:
    """Describe a file artifact by safe relative path, size, and SHA-256.

    The artifact must resolve to a regular file inside root. This records
    evidence; it does not imply the artifact itself is a valid MT5 report.
    """
    root_path = Path(root).resolve()
    artifact_path = Path(path).resolve()
    try:
        relative_path = artifact_path.relative_to(root_path)
    except ValueError as exc:
        raise ValueError("artifact must be inside the configured root") from exc
    if not artifact_path.is_file():
        raise ValueError("artifact must be an existing regular file")
    return {
        "path": relative_path.as_posix(),
        "size_bytes": artifact_path.stat().st_size,
        "sha256": sha256_file(artifact_path),
    }

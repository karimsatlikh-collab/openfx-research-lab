"""Versioned experiment records and safe state transitions.

This module deliberately does not launch MT5, run shell commands, or trade.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
import os
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
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
    if not isinstance(experiment_id, str) or not _ID_RE.fullmatch(experiment_id):
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

    if parameters is not None and not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    if not isinstance(notes, str):
        raise ValueError("notes must be a string")
    try:
        json.dumps(parameters or {}, allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("parameters must contain only finite JSON values") from None

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
    if not isinstance(manifest, dict) or any(not isinstance(key, str) for key in manifest):
        raise ValueError("manifest root must be a JSON object with string keys")
    required = {
        "schema_version", "experiment_id", "created_at_utc", "updated_at_utc",
        "status", "hypothesis", "strategy_version", "market", "parameters",
        "execution", "result", "artifacts", "notes",
    }
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    unknown = set(manifest) - required - {"error"}
    if unknown:
        raise ValueError(f"unknown manifest fields: {', '.join(sorted(unknown))}")
    if (not isinstance(manifest.get("schema_version"), int)
            or isinstance(manifest.get("schema_version"), bool)
            or manifest.get("schema_version") != SCHEMA_VERSION):
        raise ValueError("unsupported or missing schema_version")
    experiment_id = manifest.get("experiment_id")
    if not isinstance(experiment_id, str) or not _ID_RE.fullmatch(experiment_id):
        raise ValueError("invalid experiment_id")
    if not isinstance(manifest.get("status"), str) or manifest.get("status") not in STATES:
        raise ValueError("invalid status")
    for key in ("hypothesis", "strategy_version", "notes"):
        if not isinstance(manifest[key], str) or (key != "notes" and not manifest[key].strip()):
            raise ValueError(f"{key} must be a string" + (" and non-empty" if key != "notes" else ""))
    _validate_datetime(manifest["created_at_utc"], "created_at_utc")
    _validate_datetime(manifest["updated_at_utc"], "updated_at_utc")
    market = manifest["market"]
    if not isinstance(market, dict) or any(not isinstance(key, str) for key in market):
        raise ValueError("market must be an object with string keys")
    if set(market) != {"symbol", "timeframe", "data_start", "data_end"}:
        raise ValueError("market must contain only symbol, timeframe, data_start, and data_end")
    for key in ("symbol", "timeframe"):
        if not isinstance(market.get(key), str) or not market[key].strip():
            raise ValueError(f"market.{key} must be a non-empty string")
    _validate_iso_date(market.get("data_start"), "market.data_start")
    _validate_iso_date(market.get("data_end"), "market.data_end")
    if date.fromisoformat(market["data_start"]) > date.fromisoformat(market["data_end"]):
        raise ValueError("market.data_start must not be later than market.data_end")
    if not isinstance(manifest["parameters"], dict):
        raise ValueError("parameters must be an object")
    try:
        json.dumps(manifest["parameters"], allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("parameters must contain only finite JSON values") from None
    execution = manifest["execution"]
    if not isinstance(execution, dict) or any(not isinstance(key, str) for key in execution):
        raise ValueError("execution must be an object with string keys")
    if set(execution) != {"mode", "worker_version", "started_at_utc", "finished_at_utc"}:
        raise ValueError("execution contains missing or unknown fields")
    for key in ("mode", "worker_version", "started_at_utc", "finished_at_utc"):
        if key not in execution:
            raise ValueError(f"execution missing required field: {key}")
    if not isinstance(execution["mode"], str) or not execution["mode"].strip():
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
        artifact_path = artifact.get("path")
        if not isinstance(artifact_path, str) or not artifact_path or "\\" in artifact_path:
            raise ValueError(f"artifacts[{index}].path must be a safe relative POSIX path")
        parsed_path = PurePosixPath(artifact_path)
        if parsed_path.is_absolute() or any(part in {"", ".", ".."} for part in artifact_path.split("/")):
            raise ValueError(f"artifacts[{index}].path must not escape the artifact root")
        if set(artifact) != {"path", "size_bytes", "sha256"}:
            raise ValueError(f"artifacts[{index}] must contain only path, size_bytes, and sha256")
        size = artifact.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"artifacts[{index}].size_bytes must be a non-negative integer")
        if not isinstance(artifact.get("sha256"), str) or not re.fullmatch(r"[a-fA-F0-9]{64}", artifact["sha256"]):
            raise ValueError(f"artifacts[{index}].sha256 must be a SHA-256 digest")
    if manifest["result"] is not None and not isinstance(manifest["result"], dict):
        raise ValueError("result must be an object or null")
    if manifest["status"] == "COMPLETED" and not manifest["result"]:
        raise ValueError("COMPLETED requires a non-empty structured result")
    if "error" in manifest and (
        not isinstance(manifest["error"], str) or not manifest["error"].strip()
        or len(manifest["error"]) > 2000
    ):
        raise ValueError("error must be a non-empty string of at most 2000 characters")
    if manifest["status"] == "FAILED" and "error" not in manifest:
        raise ValueError("FAILED experiments require an error explanation")
    if manifest["status"] != "FAILED" and "error" in manifest:
        raise ValueError("error is only permitted for FAILED experiments")
    try:
        created = datetime.fromisoformat(manifest["created_at_utc"].replace("Z", "+00:00"))
        updated = datetime.fromisoformat(manifest["updated_at_utc"].replace("Z", "+00:00"))
        started_raw = execution["started_at_utc"]
        finished_raw = execution["finished_at_utc"]
        started = datetime.fromisoformat(started_raw.replace("Z", "+00:00")) if started_raw else None
        finished = datetime.fromisoformat(finished_raw.replace("Z", "+00:00")) if finished_raw else None
    except (AttributeError, TypeError, ValueError):
        raise ValueError("manifest timestamps are inconsistent") from None
    if updated < created:
        raise ValueError("updated_at_utc must not precede created_at_utc")
    if started and (started < created or started > updated):
        raise ValueError("execution.started_at_utc must be between creation and last update")
    if finished and (finished < created or finished > updated or (started and finished < started)):
        raise ValueError("execution.finished_at_utc is inconsistent with other timestamps")
    status = manifest["status"]
    if status == "QUEUED" and (started or finished or manifest["result"] is not None):
        raise ValueError("QUEUED experiments cannot have execution timestamps or results")
    if status == "RUNNING" and (started is None or finished is not None or manifest["result"] is not None):
        raise ValueError("RUNNING experiments require a start time and no finish time/result")
    if status in {"COMPLETED", "FAILED"} and finished is None:
        raise ValueError(f"{status} experiments require a finish timestamp")
    if status == "COMPLETED" and (started is None or not manifest["result"]):
        raise ValueError("COMPLETED experiments require start/finish timestamps and a non-empty result")
    try:
        json.dumps(manifest, allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("manifest must contain only finite JSON values") from None


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
    if not isinstance(new_status, str) or new_status not in _ALLOWED_TRANSITIONS[old_status]:
        raise ValueError(f"illegal experiment transition: {old_status} -> {new_status}")
    if error is not None and (not isinstance(error, str) or not error.strip()):
        raise ValueError("error must be a non-empty string")
    if new_status == "FAILED" and error is None:
        raise ValueError("FAILED transitions require an error explanation")
    if new_status != "FAILED" and error is not None:
        raise ValueError("error may only be supplied when transitioning to FAILED")
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
    """Validate and atomically write a JSON manifest using a unique temp file."""
    validate_manifest(manifest)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            prefix=f".{destination.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temp_name = stream.name
            stream.write(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(temp_name).replace(destination)
    except Exception:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)
        raise


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

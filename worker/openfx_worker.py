"""OpenFX Windows VPS worker prototype.

This module validates declarative jobs and records a local audit trail only.
It intentionally does NOT execute commands or invoke MT5. The real control plane
and MT5 adapter must be implemented and reviewed before deployment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
ALLOWED_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1"}
ALLOWED_MODELING = {"every_tick", "1m_ohlc", "open_prices"}
REQUIRED_JOB_KEYS = {
    "job_id", "idempotency_key", "ea_id", "ea_sha256", "symbol",
    "timeframe", "start_date", "end_date", "modeling_mode",
    "parameters", "approved", "timeout_seconds"
}
ALLOWED_JOB_KEYS = REQUIRED_JOB_KEYS | {"metadata"}


class JobValidationError(ValueError):
    """Raised when a job fails the explicit allow-list policy."""


@dataclass(frozen=True)
class WorkerConfig:
    control_plane_url: str
    poll_interval_seconds: int
    request_timeout_seconds: int
    max_jobs_per_poll: int
    allowed_ea_ids: tuple[str, ...]
    max_backtest_days: int
    max_runtime_seconds: int
    local_state_file: str
    execution_enabled: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "WorkerConfig":
        required = {
            "control_plane_url", "poll_interval_seconds",
            "request_timeout_seconds", "max_jobs_per_poll",
            "allowed_ea_ids", "max_backtest_days", "max_runtime_seconds",
            "local_state_file", "execution_enabled"
        }
        if set(data) != required:
            raise ValueError("Configuration has missing or unknown keys.")
        url = data["control_plane_url"]
        if not isinstance(url, str):
            raise ValueError("control_plane_url must be a string.")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.hostname is None:
            raise ValueError("control_plane_url must be an HTTPS URL.")
        if parsed.hostname.endswith(".invalid") or "PLACEHOLDER" in url:
            # Allowed only for local validation; network calls will be refused.
            pass
        for key, low, high in (
            ("poll_interval_seconds", 5, 3600),
            ("request_timeout_seconds", 3, 120),
            ("max_jobs_per_poll", 1, 5),
            ("max_backtest_days", 1, 3650),
            ("max_runtime_seconds", 30, 86400),
        ):
            value = data[key]
            if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
                raise ValueError(f"{key} must be an integer from {low} to {high}.")
        if not isinstance(data["allowed_ea_ids"], list) or not data["allowed_ea_ids"]:
            raise ValueError("allowed_ea_ids must be a non-empty list.")
        if any(not isinstance(item, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", item)
               for item in data["allowed_ea_ids"]):
            raise ValueError("allowed_ea_ids contains an invalid identifier.")
        if not isinstance(data["local_state_file"], str) or not data["local_state_file"]:
            raise ValueError("local_state_file must be a non-empty path.")
        if not isinstance(data["execution_enabled"], bool):
            raise ValueError("execution_enabled must be boolean.")
        # Even if a config sets true, this prototype never executes jobs.
        return cls(
            control_plane_url=url,
            poll_interval_seconds=data["poll_interval_seconds"],
            request_timeout_seconds=data["request_timeout_seconds"],
            max_jobs_per_poll=data["max_jobs_per_poll"],
            allowed_ea_ids=tuple(data["allowed_ea_ids"]),
            max_backtest_days=data["max_backtest_days"],
            max_runtime_seconds=data["max_runtime_seconds"],
            local_state_file=data["local_state_file"],
            execution_enabled=data["execution_enabled"],
        )


def validate_job(job: Any, config: WorkerConfig) -> dict[str, Any]:
    """Validate a job strictly; return a shallow copy if accepted."""
    if not isinstance(job, dict):
        raise JobValidationError("Job must be a JSON object.")
    keys = set(job)
    if REQUIRED_JOB_KEYS - keys:
        raise JobValidationError("Job is missing required fields.")
    if keys - ALLOWED_JOB_KEYS:
        raise JobValidationError("Job contains unknown fields.")
    if not isinstance(job["job_id"], str) or not JOB_ID_RE.fullmatch(job["job_id"]):
        raise JobValidationError("Invalid job_id.")
    if not isinstance(job["idempotency_key"], str) or not JOB_ID_RE.fullmatch(job["idempotency_key"]):
        raise JobValidationError("Invalid idempotency_key.")
    if not isinstance(job["ea_id"], str) or job["ea_id"] not in config.allowed_ea_ids:
        raise JobValidationError("EA is not on the worker allow-list.")
    if not isinstance(job["ea_sha256"], str) or not SHA256_RE.fullmatch(job["ea_sha256"]):
        raise JobValidationError("ea_sha256 must be a 64-character SHA-256 hex digest.")
    if not isinstance(job["symbol"], str) or not re.fullmatch(r"[A-Z0-9._-]{3,20}", job["symbol"]):
        raise JobValidationError("Invalid symbol.")
    if not isinstance(job["timeframe"], str) or job["timeframe"] not in ALLOWED_TIMEFRAMES:
        raise JobValidationError("Unsupported timeframe.")
    try:
        start = date.fromisoformat(job["start_date"])
        end = date.fromisoformat(job["end_date"])
    except (TypeError, ValueError):
        raise JobValidationError("Dates must use YYYY-MM-DD.") from None
    if end <= start:
        raise JobValidationError("end_date must be after start_date.")
    if (end - start).days > config.max_backtest_days:
        raise JobValidationError("Date range exceeds the configured limit.")
    if not isinstance(job["modeling_mode"], str) or job["modeling_mode"] not in ALLOWED_MODELING:
        raise JobValidationError("Unsupported modeling mode.")
    if not isinstance(job["parameters"], dict) or len(job["parameters"]) > 100:
        raise JobValidationError("parameters must be a JSON object with at most 100 entries.")
    # Only finite JSON primitive values are accepted; no nested executable payloads.
    for key, value in job["parameters"].items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,64}", key):
            raise JobValidationError("Invalid parameter name.")
        if isinstance(value, (dict, list)) or value is None or isinstance(value, bool):
            raise JobValidationError("Parameter values must be numbers or strings.")
        if not isinstance(value, (int, float, str)):
            raise JobValidationError("Unsupported parameter value.")
        if isinstance(value, float) and (value != value or abs(value) == float("inf")):
            raise JobValidationError("Non-finite parameter values are not allowed.")
        if isinstance(value, str) and len(value) > 256:
            raise JobValidationError("String parameter value is too long.")
    if job["approved"] is not True:
        raise JobValidationError("Job has not been explicitly approved.")
    timeout = job["timeout_seconds"]
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 30 <= timeout <= config.max_runtime_seconds:
        raise JobValidationError("timeout_seconds exceeds the permitted range.")
    if "metadata" in job and not isinstance(job["metadata"], dict):
        raise JobValidationError("metadata must be an object.")
    return dict(job)


def load_state(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"seen_jobs": {}, "events": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise RuntimeError("State file is unreadable; refusing to continue.") from None
    if not isinstance(data, dict) or not isinstance(data.get("seen_jobs"), dict) or not isinstance(data.get("events"), list):
        raise RuntimeError("State file has invalid structure; refusing to continue.")
    return data


def save_state(path: str, state: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_suffix(p.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(p)


def record_event(state: dict[str, Any], job_id: str, status: str, detail: str) -> None:
    # Keep audit detail intentionally small and never include request headers/tokens.
    state["events"].append({
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "job_id": job_id,
        "status": status,
        "detail": detail[:240],
    })
    state["events"] = state["events"][-2000:]


def safe_poll(config: WorkerConfig, token: str) -> list[dict[str, Any]]:
    """Fail closed until signed authorization and canonical contract checks exist."""
    # The current prototype has no signed AuthorizationRecord verifier,
    # canonical JobSpec/RunRecord binding, or trusted nonce-consuming registrar.
    # A bearer token and caller-controlled `approved` flag are not authorization.
    raise RuntimeError(
        "Network polling is disabled until signed authorization and canonical "
        "research-contract verification are implemented and independently tested."
    )


def process_job(job_data: Any, config: WorkerConfig, state: dict[str, Any]) -> str:
    """Validate and record a job; execution is deliberately disabled in this prototype."""
    try:
        job = validate_job(job_data, config)
    except JobValidationError as exc:
        record_event(state, "unknown", "REJECTED", str(exc))
        return "REJECTED"
    job_id = job["job_id"]
    if job_id in state["seen_jobs"]:
        record_event(state, job_id, "DUPLICATE", "Previously seen job; no action taken.")
        return "DUPLICATE"
    state["seen_jobs"][job_id] = {
        "idempotency_key": job["idempotency_key"],
        "ea_sha256": job["ea_sha256"].lower(),
        "status": "VALIDATED_NOT_EXECUTED",
    }
    record_event(
        state, job_id, "VALIDATED_NOT_EXECUTED",
        "Schema accepted; MT5 execution is not implemented in this prototype."
    )
    return "VALIDATED_NOT_EXECUTED"


def self_test() -> int:
    config = WorkerConfig.from_mapping({
        "control_plane_url": "https://CONTROL-PLANE-PLACEHOLDER.invalid",
        "poll_interval_seconds": 30,
        "request_timeout_seconds": 15,
        "max_jobs_per_poll": 1,
        "allowed_ea_ids": ["openfx-demo-ea"],
        "max_backtest_days": 365,
        "max_runtime_seconds": 1800,
        "local_state_file": "worker_state.json",
        "execution_enabled": False,
    })
    good = {
        "job_id": "test-job-001",
        "idempotency_key": "test-key-001",
        "ea_id": "openfx-demo-ea",
        "ea_sha256": hashlib.sha256(b"demo").hexdigest(),
        "symbol": "EURUSD",
        "timeframe": "M15",
        "start_date": "2025-01-01",
        "end_date": "2025-02-01",
        "modeling_mode": "every_tick",
        "parameters": {"RiskPercent": 0.5, "UseFilter": "true"},
        "approved": True,
        "timeout_seconds": 300,
    }
    validate_job(good, config)
    try:
        validate_job({**good, "command": "whoami"}, config)
    except JobValidationError:
        pass
    else:
        raise AssertionError("Unknown command field was not rejected.")
    try:
        validate_job({**good, "ea_id": "unapproved-ea"}, config)
    except JobValidationError:
        pass
    else:
        raise AssertionError("Unapproved EA was not rejected.")
    state = {"seen_jobs": {}, "events": []}
    assert process_job(good, config, state) == "VALIDATED_NOT_EXECUTED"
    assert process_job(good, config, state) == "DUPLICATE"
    assert len(state["events"]) == 2
    print("OpenFX worker self-test: PASS (validation only; no network or MT5 execution).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline validation checks")
    parser.add_argument("--config", help="path to private JSON configuration")
    parser.add_argument("--once", action="store_true", help="poll once (disabled until control plane exists)")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.config:
        parser.error("provide --config or use --self-test")
    try:
        config_data = json.loads(Path(args.config).read_text(encoding="utf-8"))
        config = WorkerConfig.from_mapping(config_data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    if not args.once:
        print("Prototype only. Use --once for a single poll; no background service is implemented.")
        return 0
    if not config.execution_enabled:
        print("Worker execution is disabled by configuration; no job will be executed.")
    token = os.environ.get("OPENFX_WORKER_TOKEN", "")
    try:
        jobs = safe_poll(config, token)
    except RuntimeError as exc:
        print(f"Polling stopped safely: {exc}", file=sys.stderr)
        return 3
    state = load_state(config.local_state_file)
    for job in jobs:
        print(process_job(job, config, state))
    save_state(config.local_state_file, state)
    print("Prototype only: jobs were validated/recorded, not executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

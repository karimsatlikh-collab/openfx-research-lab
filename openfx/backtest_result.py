"""Strict MT5 Strategy Tester result contract and review-readiness checks."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any

_SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")
_COMMIT_RE = re.compile(r"^[a-fA-F0-9]{40}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_MODELING_MODES = {"every_tick", "1m_ohlc", "open_prices"}
_SPLIT_NAMES = ("development", "validation", "final_oos")
_REQUIRED_ARTIFACTS = {"tester_report", "journal_log", "ea_binary", "data_manifest"}
_EXECUTION_FIELDS = {
    "terminal_build", "ea_sha256", "data_sha256", "symbol", "timeframe",
    "data_start", "data_end", "modeling_mode", "initial_deposit",
    "deposit_currency", "leverage", "spread_points", "commission_per_lot",
    "slippage_points",
}
_METRIC_FIELDS = {
    "trade_count", "net_profit", "gross_profit", "gross_loss",
    "profit_factor", "expected_payoff", "max_drawdown_pct", "relative_drawdown_pct",
}
_VERIFICATION_FIELDS = {
    "tester_report_parsed", "journal_complete", "data_coverage_verified",
    "costs_recorded", "split_boundaries_verified",
}
_ROOT_FIELDS = {
    "schema_version", "experiment_id", "created_at_utc", "source_commit_sha",
    "result_origin", "execution", "splits", "metrics", "artifacts",
    "verification", "notes",
}


def _real_date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field} must be a real calendar date") from None


def _finite_number(value: Any, field: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} must be at most {maximum}")
    return float(value)


def validate_backtest_result(result: Any) -> dict[str, Any]:
    """Validate result provenance and return review-readiness blockers/warnings.

    A result marked ready is only ready for independent review. This function
    does not verify artifact bytes, parse MT5 reports, or prove profitability.
    """
    if not isinstance(result, dict) or any(not isinstance(key, str) for key in result):
        raise ValueError("result root must be an object with string keys")
    if set(result) != _ROOT_FIELDS:
        missing = _ROOT_FIELDS - set(result)
        unknown = set(result) - _ROOT_FIELDS
        raise ValueError(f"result fields mismatch (missing={sorted(missing)}, unknown={sorted(unknown)})")
    if type(result["schema_version"]) is not int or result["schema_version"] != 1:
        raise ValueError("unsupported result schema_version")
    if not isinstance(result["experiment_id"], str) or not _ID_RE.fullmatch(result["experiment_id"]):
        raise ValueError("invalid experiment_id")
    if not isinstance(result["source_commit_sha"], str) or not _COMMIT_RE.fullmatch(result["source_commit_sha"]):
        raise ValueError("source_commit_sha must be a 40-character Git commit SHA")
    if result["result_origin"] != "mt5_strategy_tester":
        raise ValueError("result_origin must be mt5_strategy_tester; mock results are not backtests")
    if not isinstance(result["created_at_utc"], str):
        raise ValueError("created_at_utc must be timezone-aware ISO-8601")
    try:
        created_at = datetime.fromisoformat(result["created_at_utc"].replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("created_at_utc must be timezone-aware ISO-8601") from None
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at_utc must include a timezone")
    if not isinstance(result["notes"], str):
        raise ValueError("notes must be a string")

    execution = result["execution"]
    if not isinstance(execution, dict) or set(execution) != _EXECUTION_FIELDS:
        raise ValueError("execution must contain the exact required fields")
    for field in ("terminal_build", "symbol", "timeframe", "deposit_currency"):
        if not isinstance(execution[field], str) or not execution[field].strip():
            raise ValueError(f"execution.{field} must be a non-empty string")
    for field in ("ea_sha256", "data_sha256"):
        if not isinstance(execution[field], str) or not _SHA256_RE.fullmatch(execution[field]):
            raise ValueError(f"execution.{field} must be a SHA-256 digest")
    if not isinstance(execution["modeling_mode"], str) or execution["modeling_mode"] not in _MODELING_MODES:
        raise ValueError("unsupported modeling_mode")
    data_start = _real_date(execution["data_start"], "execution.data_start")
    data_end = _real_date(execution["data_end"], "execution.data_end")
    if data_start > data_end:
        raise ValueError("execution.data_start must not be later than data_end")
    _finite_number(execution["initial_deposit"], "execution.initial_deposit", minimum=0.0000001)
    leverage = execution["leverage"]
    if not isinstance(leverage, int) or isinstance(leverage, bool) or leverage < 1:
        raise ValueError("execution.leverage must be a positive integer")
    for field in ("spread_points", "commission_per_lot", "slippage_points"):
        _finite_number(execution[field], f"execution.{field}", minimum=0)

    splits = result["splits"]
    if not isinstance(splits, dict) or set(splits) != set(_SPLIT_NAMES):
        raise ValueError("splits must contain development, validation, and final_oos")
    parsed_splits = []
    for name in _SPLIT_NAMES:
        interval = splits[name]
        if not isinstance(interval, dict) or set(interval) != {"start", "end"}:
            raise ValueError(f"splits.{name} must contain start and end")
        start = _real_date(interval["start"], f"splits.{name}.start")
        end = _real_date(interval["end"], f"splits.{name}.end")
        if start > end:
            raise ValueError(f"splits.{name}.start must not be later than end")
        if start < data_start or end > data_end:
            raise ValueError(f"splits.{name} must be within the execution data range")
        parsed_splits.append((name, start, end))
    for previous, current in zip(parsed_splits, parsed_splits[1:]):
        if current[1] <= previous[2]:
            raise ValueError(f"{current[0]} split overlaps or precedes {previous[0]}")

    metrics = result["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != _METRIC_FIELDS:
        raise ValueError("metrics must contain the exact required fields")
    trade_count = metrics["trade_count"]
    if not isinstance(trade_count, int) or isinstance(trade_count, bool) or trade_count < 0:
        raise ValueError("metrics.trade_count must be a non-negative integer")
    for field in ("net_profit", "expected_payoff"):
        _finite_number(metrics[field], f"metrics.{field}")
    for field in ("gross_profit", "gross_loss"):
        _finite_number(metrics[field], f"metrics.{field}", minimum=0)
    profit_factor = metrics["profit_factor"]
    if profit_factor is not None:
        _finite_number(profit_factor, "metrics.profit_factor", minimum=0)
    for field in ("max_drawdown_pct", "relative_drawdown_pct"):
        _finite_number(metrics[field], f"metrics.{field}", minimum=0, maximum=100)

    artifacts = result["artifacts"]
    if not isinstance(artifacts, list):
        raise ValueError("artifacts must be a list")
    artifact_kinds = set()
    artifact_paths = set()
    artifacts_by_kind: dict[str, list[dict[str, Any]]] = {}
    empty_required_artifacts = set()
    for index, artifact in enumerate(artifacts):
        required = {"kind", "path", "size_bytes", "sha256"}
        if not isinstance(artifact, dict) or set(artifact) != required:
            raise ValueError(f"artifacts[{index}] has missing or unknown fields")
        if not isinstance(artifact["kind"], str) or not artifact["kind"]:
            raise ValueError(f"artifacts[{index}].kind must be a non-empty string")
        path = artifact["path"]
        if not isinstance(path, str) or not path or "\\" in path:
            raise ValueError(f"artifacts[{index}].path must be a safe relative POSIX path")
        parsed_path = PurePosixPath(path)
        if (parsed_path.is_absolute() or re.match(r"^[A-Za-z]:", path)
                or any(ord(ch) < 32 for ch in path)
                or any(part in {"", ".", ".."} for part in path.split("/"))):
            raise ValueError(f"artifacts[{index}].path must not escape the artifact root")
        if path in artifact_paths:
            raise ValueError(f"duplicate artifact path: {path}")
        artifact_paths.add(path)
        size = artifact["size_bytes"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"artifacts[{index}].size_bytes must be a non-negative integer")
        if not isinstance(artifact["sha256"], str) or not _SHA256_RE.fullmatch(artifact["sha256"]):
            raise ValueError(f"artifacts[{index}].sha256 must be a SHA-256 digest")
        artifact_kinds.add(artifact["kind"])
        artifacts_by_kind.setdefault(artifact["kind"], []).append(artifact)
        if artifact["kind"] in _REQUIRED_ARTIFACTS and size == 0:
            empty_required_artifacts.add(artifact["kind"])

    verification = result["verification"]
    if not isinstance(verification, dict) or set(verification) != _VERIFICATION_FIELDS:
        raise ValueError("verification must contain the exact required checks")
    for field, value in verification.items():
        if not isinstance(value, bool):
            raise ValueError(f"verification.{field} must be boolean")

    blockers = []
    missing_artifacts = _REQUIRED_ARTIFACTS - artifact_kinds
    if missing_artifacts:
        blockers.append("missing_required_artifacts:" + ",".join(sorted(missing_artifacts)))
    if empty_required_artifacts:
        blockers.append("empty_required_artifacts:" + ",".join(sorted(empty_required_artifacts)))
    if "ea_binary" in artifacts_by_kind and not any(
        artifact["sha256"].lower() == execution["ea_sha256"].lower()
        for artifact in artifacts_by_kind["ea_binary"]
    ):
        blockers.append("ea_binary_hash_mismatch")
    if "data_manifest" in artifacts_by_kind and not any(
        artifact["sha256"].lower() == execution["data_sha256"].lower()
        for artifact in artifacts_by_kind["data_manifest"]
    ):
        blockers.append("data_manifest_hash_mismatch")
    for field, value in verification.items():
        if not value:
            blockers.append("verification_incomplete:" + field)

    warnings = []
    if trade_count > 0:
        expected_payoff = metrics["expected_payoff"]
        derived_payoff = metrics["net_profit"] / trade_count
        if not math.isclose(expected_payoff, derived_payoff, rel_tol=0.05, abs_tol=0.05):
            warnings.append("expected_payoff_differs_from_net_profit_per_trade")
    gross_loss = metrics["gross_loss"]
    if gross_loss > 0 and profit_factor is None:
        warnings.append("profit_factor_missing_despite_gross_loss")
    elif gross_loss > 0 and profit_factor is not None:
        derived_pf = metrics["gross_profit"] / gross_loss
        if not math.isclose(profit_factor, derived_pf, rel_tol=0.05, abs_tol=0.05):
            warnings.append("profit_factor_differs_from_gross_profit_over_gross_loss")

    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("result must contain only finite JSON values") from None
    return {
        "experiment_id": result["experiment_id"],
        "review_status": "ready_for_independent_review" if not blockers else "incomplete",
        "blockers": blockers,
        "warnings": warnings,
        "scope": "schema_and_metadata_validation_not_profitability_verification",
    }



def verify_artifact_files(result: dict[str, Any], artifact_root: str | Path) -> dict[str, Any]:
    """Verify declared artifact file sizes and SHA-256 hashes under a trusted root."""
    validate_backtest_result(result)
    try:
        root = Path(artifact_root).resolve(strict=True)
    except OSError:
        return {"status": "artifact_verification_failed", "verified_artifacts": [], "blockers": ["artifact_root_missing"]}
    if not root.is_dir():
        return {"status": "artifact_verification_failed", "verified_artifacts": [], "blockers": ["artifact_root_not_directory"]}

    verified = []
    blockers = []
    for artifact in result["artifacts"]:
        relative = PurePosixPath(artifact["path"])
        candidate = root
        unsafe_symlink = False
        for part in relative.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                unsafe_symlink = True
                break
        if unsafe_symlink:
            blockers.append(f"artifact_symlink:{artifact['path']}")
            continue
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, ValueError):
            blockers.append(f"artifact_missing_or_outside_root:{artifact['path']}")
            continue
        if not resolved.is_file():
            blockers.append(f"artifact_not_file:{artifact['path']}")
            continue
        try:
            stat = resolved.stat()
            if stat.st_size != artifact["size_bytes"]:
                blockers.append(f"artifact_size_mismatch:{artifact['path']}")
                continue
            digest = hashlib.sha256()
            with resolved.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            blockers.append(f"artifact_read_error:{artifact['path']}")
            continue
        if digest.hexdigest().lower() != artifact["sha256"].lower():
            blockers.append(f"artifact_hash_mismatch:{artifact['path']}")
            continue
        verified.append(artifact["path"])

    return {
        "status": "artifact_bytes_verified" if not blockers else "artifact_verification_failed",
        "verified_artifacts": verified,
        "blockers": blockers,
        "scope": "file_size_and_sha256_only_not_report_semantics_or_profitability",
    }

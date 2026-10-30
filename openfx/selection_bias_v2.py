"""M3 v2 candidate: HAC-studentized circular moving-block bootstrap + Holm.

This is a separate, unaccepted research candidate. It does not replace M3 v1.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import re
import sys
from datetime import datetime, timedelta
from numbers import Real
from typing import Any

METHOD_ID = "M3-HOLM-HAC-MBB-V2"
METHOD_VERSION = "2.0.1"
DEFAULT_ALPHA = 0.05
DEFAULT_REPLICATES = 9999
DEFAULT_MIN_OBSERVATIONS = 252
HAC_KERNEL_ID = "NEWEY_WEST_BARTLETT"
BLOCK_LENGTH_RULE = "ceil(n^(1/3))"
HAC_LAG_RULE = "ceil(n^(1/3))"
MAX_TRIALS = 10_000
MAX_OBSERVATIONS = 100_000
MAX_BOOTSTRAP_WORK = 1_000_000_000
_SOURCE_REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class SelectionBiasV2Error(ValueError):
    """Raised when the registered family cannot be evaluated safely."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _finite_vector(values: Any) -> list[float]:
    if not isinstance(values, list) or not values or len(values) > MAX_OBSERVATIONS:
        raise SelectionBiasV2Error("validation_returns must be a non-empty list within the observation limit")
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
            raise SelectionBiasV2Error("returns must contain only finite numeric values")
        result.append(float(value))
    return result


def _timestamp_vector(values: Any, expected_length: int) -> list[str]:
    if not isinstance(values, list) or len(values) != expected_length:
        raise SelectionBiasV2Error("timestamps must align one-to-one with returns")
    parsed = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise SelectionBiasV2Error("timestamps must be non-empty ISO-8601 strings")
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SelectionBiasV2Error("timestamp is not valid ISO-8601") from exc
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise SelectionBiasV2Error("timestamps must include an explicit timezone")
        parsed.append(stamp)
    if any(right <= left for left, right in zip(parsed, parsed[1:])):
        raise SelectionBiasV2Error("timestamps must be unique and strictly increasing")
    return values


def _hac_lag(n: int) -> int:
    return max(1, math.ceil(n ** (1.0 / 3.0)))


def _block_length(n: int) -> int:
    return max(1, math.ceil(n ** (1.0 / 3.0)))


def _hac_studentized_mean(values: list[float], lag: int) -> float:
    n = len(values)
    if n < 2 or lag < 1 or lag >= n:
        raise SelectionBiasV2Error("invalid sample size or HAC lag")
    mean = sum(values) / n
    centered = [value - mean for value in values]
    long_run_variance = sum(value * value for value in centered) / n
    for offset in range(1, lag + 1):
        covariance = sum(centered[i] * centered[i - offset]
                         for i in range(offset, n)) / n
        weight = 1.0 - offset / (lag + 1.0)
        long_run_variance += 2.0 * weight * covariance
    if not math.isfinite(long_run_variance) or long_run_variance <= 0.0:
        raise SelectionBiasV2Error("zero or invalid HAC long-run variance")
    statistic = mean / math.sqrt(long_run_variance / n)
    if not math.isfinite(statistic):
        raise SelectionBiasV2Error("non-finite HAC-studentized statistic")
    return statistic


def holm_step_down(pvalues: dict[str, float],
                   alpha: float = DEFAULT_ALPHA) -> dict[str, dict[str, Any]]:
    if not isinstance(pvalues, dict) or not pvalues:
        raise SelectionBiasV2Error("pvalues must contain the complete non-empty family")
    if isinstance(alpha, bool) or not isinstance(alpha, Real) or float(alpha) != DEFAULT_ALPHA:
        raise SelectionBiasV2Error("M3 v2 requires the frozen alpha=0.05")
    clean = {}
    for trial_id, pvalue in pvalues.items():
        if not isinstance(trial_id, str) or not trial_id:
            raise SelectionBiasV2Error("trial IDs must be non-empty strings")
        if (isinstance(pvalue, bool) or not isinstance(pvalue, Real)
                or not math.isfinite(float(pvalue)) or not 0 <= pvalue <= 1):
            raise SelectionBiasV2Error("p-values must be finite and within [0, 1]")
        clean[trial_id] = float(pvalue)
    ordered = sorted(clean, key=lambda key: (clean[key], key))
    family_size = len(ordered)
    rejected = True
    adjusted_running = 0.0
    result = {}
    for rank, trial_id in enumerate(ordered, start=1):
        threshold = DEFAULT_ALPHA / (family_size - rank + 1)
        reject = rejected and clean[trial_id] <= threshold
        if not reject:
            rejected = False
        adjusted_running = max(
            adjusted_running,
            min(1.0, (family_size - rank + 1) * clean[trial_id]),
        )
        result[trial_id] = {
            "rank": rank, "raw_p_value": clean[trial_id],
            "holm_adjusted_p_value": adjusted_running,
            "threshold": threshold, "rejected": bool(reject),
        }
    return result


def _bootstrap_pvalues(series: dict[str, list[float]], *,
                       replicates: int = DEFAULT_REPLICATES,
                       seed: int) -> dict[str, float]:
    trial_ids = sorted(series)
    n = len(series[trial_ids[0]])
    block = _block_length(n)
    lag = _hac_lag(n)
    blocks_needed = math.ceil(n / block)
    observed = {trial_id: _hac_studentized_mean(series[trial_id], lag)
                for trial_id in trial_ids}
    centered = {
        trial_id: [value - sum(series[trial_id]) / n for value in series[trial_id]]
        for trial_id in trial_ids
    }
    rng = random.Random(seed)
    exceedances = {trial_id: 0 for trial_id in trial_ids}
    for _ in range(replicates):
        indices = []
        for _block in range(blocks_needed):
            start = rng.randrange(n)
            indices.extend((start + offset) % n for offset in range(block))
        indices = indices[:n]
        for trial_id in trial_ids:
            sample = [centered[trial_id][index] for index in indices]
            try:
                statistic = _hac_studentized_mean(sample, lag)
            except SelectionBiasV2Error:
                # A degenerate bootstrap draw is conservatively an exceedance.
                exceedances[trial_id] += 1
                continue
            if statistic >= observed[trial_id]:
                exceedances[trial_id] += 1
    return {
        trial_id: (1 + exceedances[trial_id]) / (replicates + 1)
        for trial_id in trial_ids
    }


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("frozen_before_trials") is not True:
        raise SelectionBiasV2Error("a frozen family manifest is required")
    required = (
        "method_id", "method_version", "family_id", "data_profile_id",
        "cost_profile_id", "validation_split_id", "return_frequency",
        "source_revision", "max_trials", "frozen_at_utc", "alpha",
        "bootstrap_replicates", "min_observations", "hac_kernel",
        "hac_lag_rule", "block_length_rule",
    )
    for key in required:
        if key not in manifest or manifest[key] in (None, ""):
            raise SelectionBiasV2Error(f"manifest missing {key}")
    if manifest["method_id"] != METHOD_ID or manifest["method_version"] != METHOD_VERSION:
        raise SelectionBiasV2Error("manifest method ID/version does not match this implementation")
    string_fields = (
        "family_id", "data_profile_id", "cost_profile_id",
        "validation_split_id", "return_frequency", "source_revision",
    )
    if any(not isinstance(manifest[key], str) or not manifest[key].strip()
           for key in string_fields):
        raise SelectionBiasV2Error("family and input binding fields must be non-empty strings")
    if (not isinstance(manifest["max_trials"], int)
            or isinstance(manifest["max_trials"], bool)
            or not 1 <= manifest["max_trials"] <= MAX_TRIALS):
        raise SelectionBiasV2Error(f"max_trials must be an integer from 1 to {MAX_TRIALS}")
    if _SOURCE_REVISION_RE.fullmatch(manifest["source_revision"]) is None:
        raise SelectionBiasV2Error("source_revision must be a 40- or 64-character lowercase git SHA")
    try:
        frozen_at = datetime.fromisoformat(str(manifest["frozen_at_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SelectionBiasV2Error("frozen_at_utc must be ISO-8601") from exc
    if frozen_at.tzinfo is None or frozen_at.utcoffset() != timedelta(0):
        raise SelectionBiasV2Error("frozen_at_utc must be explicitly UTC")
    if (isinstance(manifest["alpha"], bool) or not isinstance(manifest["alpha"], Real)
            or float(manifest["alpha"]) != DEFAULT_ALPHA):
        raise SelectionBiasV2Error("M3 v2 requires frozen alpha=0.05")
    if (isinstance(manifest["bootstrap_replicates"], bool)
            or not isinstance(manifest["bootstrap_replicates"], int)
            or manifest["bootstrap_replicates"] != DEFAULT_REPLICATES):
        raise SelectionBiasV2Error("M3 v2 requires frozen 9999 bootstrap replicates")
    if (isinstance(manifest["min_observations"], bool)
            or not isinstance(manifest["min_observations"], int)
            or manifest["min_observations"] != DEFAULT_MIN_OBSERVATIONS):
        raise SelectionBiasV2Error("M3 v2 requires a frozen minimum of 252 observations")
    if manifest["hac_kernel"] != HAC_KERNEL_ID:
        raise SelectionBiasV2Error("unsupported HAC kernel")
    if manifest["hac_lag_rule"] != HAC_LAG_RULE:
        raise SelectionBiasV2Error("unsupported HAC lag rule")
    if manifest["block_length_rule"] != BLOCK_LENGTH_RULE:
        raise SelectionBiasV2Error("unsupported bootstrap block-length rule")
    return {"alpha": DEFAULT_ALPHA, "bootstrap_replicates": DEFAULT_REPLICATES,
            "min_observations": DEFAULT_MIN_OBSERVATIONS}


def evaluate_registered_family(*, registry: Any,
                               manifest: dict[str, Any]) -> dict[str, Any]:
    settings = _validate_manifest(manifest)
    if not hasattr(registry, "family_snapshot"):
        raise SelectionBiasV2Error("registry must expose family_snapshot(family_id)")
    snapshot = registry.family_snapshot(manifest["family_id"])
    if not isinstance(snapshot, dict) or snapshot.get("valid") is not True:
        raise SelectionBiasV2Error("registry family snapshot is invalid")
    if snapshot.get("family_id") != manifest["family_id"]:
        raise SelectionBiasV2Error("registry snapshot family_id does not match frozen manifest")
    trials = snapshot.get("trials")
    if not isinstance(trials, list) or not trials:
        raise SelectionBiasV2Error("family has no registered trials")
    event_count = snapshot.get("event_count")
    trial_count = snapshot.get("trial_count")
    event_hashes = snapshot.get("family_event_sha256")
    if (isinstance(event_count, bool) or not isinstance(event_count, int)
            or event_count < len(trials) or trial_count != len(trials)
            or not isinstance(event_hashes, list) or len(event_hashes) != event_count
            or any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
                   for value in event_hashes)
            or len(set(event_hashes)) != event_count):
        raise SelectionBiasV2Error("registry family snapshot event/trial counts or event hashes are invalid")
    if snapshot.get("trust") != "local_prototype_not_independently_authenticated":
        raise SelectionBiasV2Error("registry snapshot trust declaration is missing or unexpected")
    if len(trials) > manifest["max_trials"]:
        raise SelectionBiasV2Error("family trial budget exceeded")
    if any(not isinstance(row, dict) for row in trials):
        raise SelectionBiasV2Error("registry snapshot contains a non-object trial")
    trial_ids = [row.get("trial_id") for row in trials]
    if any(not isinstance(value, str) or not value for value in trial_ids):
        raise SelectionBiasV2Error("registry snapshot contains malformed trial IDs")
    if len(set(trial_ids)) != len(trial_ids):
        raise SelectionBiasV2Error("registry snapshot contains duplicate trial IDs")
    indices = [row.get("trial_index") for row in trials]
    if (any(isinstance(index, bool) or not isinstance(index, int) or index < 1
            for index in indices)
            or sorted(indices) != list(range(1, len(trials) + 1))):
        raise SelectionBiasV2Error("registry trial_index values must be unique and contiguous from one")
    ordered = sorted(trials, key=lambda row: (row["trial_index"], row["trial_id"]))
    manifest_digest = sha256_json(manifest)
    for row in ordered:
        registration = row.get("registration_payload")
        if (row.get("registration_outcome") != "pending"
                or not isinstance(registration, dict)
                or registration.get("family_manifest_sha256") != manifest_digest
                or registration.get("registered_before_execution") is not True):
            raise SelectionBiasV2Error("every trial requires pending pre-execution registration bound to manifest")

    pvalues = {row["trial_id"]: 1.0 for row in ordered}
    series: dict[str, list[float]] = {}
    return_hashes: dict[str, str] = {}
    exclusions = {}
    timestamps_ref = None
    for row in ordered:
        trial_id = row["trial_id"]
        if row.get("outcome") != "completed":
            exclusions[trial_id] = "non_completed_trial_counted_with_p1"
            continue
        payload = row.get("payload")
        validation = payload.get("validation") if isinstance(payload, dict) else None
        if not isinstance(validation, dict):
            exclusions[trial_id] = "missing_validation_payload_counted_with_p1"
            continue
        bindings = {
            "data_profile_id": manifest["data_profile_id"],
            "cost_profile_id": manifest["cost_profile_id"],
            "split_id": manifest["validation_split_id"],
            "return_frequency": manifest["return_frequency"],
            "source_revision": manifest["source_revision"],
        }
        mismatch = [key for key, expected in bindings.items()
                    if validation.get(key) != expected]
        if mismatch:
            exclusions[trial_id] = "binding_mismatch:" + ",".join(mismatch)
            continue
        try:
            values = _finite_vector(validation.get("returns"))
            if len(values) < settings["min_observations"]:
                exclusions[trial_id] = "insufficient_observations_counted_with_p1"
                continue
            timestamps = _timestamp_vector(validation.get("timestamps"), len(values))
            digest = sha256_json(values)
            if validation.get("returns_sha256") != digest:
                exclusions[trial_id] = "return_artifact_hash_mismatch_counted_with_p1"
                continue
            _hac_studentized_mean(values, _hac_lag(len(values)))
            if timestamps_ref is not None and timestamps != timestamps_ref:
                exclusions[trial_id] = "unaligned_timestamps_counted_with_p1"
                continue
        except (SelectionBiasV2Error, TypeError):
            exclusions[trial_id] = "invalid_or_degenerate_returns_counted_with_p1"
            continue
        if timestamps_ref is None:
            timestamps_ref = timestamps
        series[trial_id] = values
        return_hashes[trial_id] = digest

    if not series:
        return {
            "decision": "BLOCKED", "reason": "no_eligible_completed_trials",
            "method_id": METHOD_ID, "method_version": METHOD_VERSION,
            "family_id": manifest["family_id"], "trial_count": len(ordered),
            "trial_ids": [row["trial_id"] for row in ordered],
            "exclusions": exclusions, "registry_snapshot_sha256": sha256_json(snapshot),
            "limitations": ["Local registry is not an independently trusted registrar.",
                            "No eligible validation return series; no statistical pass is possible."],
        }

    n = len(next(iter(series.values())))
    estimated_bootstrap_work = (settings["bootstrap_replicates"] * len(series)
                                * n * (_hac_lag(n) + 1))
    if estimated_bootstrap_work > MAX_BOOTSTRAP_WORK:
        return {
            "decision": "BLOCKED", "reason": "bootstrap_work_budget_exceeded",
            "method_id": METHOD_ID, "method_version": METHOD_VERSION,
            "family_id": manifest["family_id"], "trial_count": len(ordered),
            "eligible_trial_count": len(series), "estimated_bootstrap_work": estimated_bootstrap_work,
            "max_bootstrap_work": MAX_BOOTSTRAP_WORK,
            "trial_ids": [row["trial_id"] for row in ordered],
            "exclusions": exclusions, "registry_snapshot_sha256": sha256_json(snapshot),
            "limitations": ["Estimated bootstrap work exceeds the frozen runtime safety budget; no p-values were computed."],
        }

    seed_material = (manifest_digest + METHOD_ID + METHOD_VERSION).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
    raw = _bootstrap_pvalues(series, replicates=settings["bootstrap_replicates"], seed=seed)
    pvalues.update(raw)
    adjusted = holm_step_down(pvalues)
    trial_results = []
    for row in ordered:
        trial_id = row["trial_id"]
        stat = adjusted[trial_id]
        trial_results.append({
            "trial_id": trial_id, "trial_index": row["trial_index"],
            "outcome": row.get("outcome"), "eligible": trial_id in series,
            "exclusion_reason": exclusions.get(trial_id),
            "sample_size": len(series[trial_id]) if trial_id in series else 0,
            "returns_sha256": return_hashes.get(trial_id), **stat,
        })
    rejected = [item["trial_id"] for item in trial_results
                if item["eligible"] and item["rejected"]]
    verdict = {
        "decision": "PASS" if rejected else "FAIL",
        "reason": "holm_rejected_at_least_one_trial" if rejected else "no_trial_rejected_by_holm",
        "method_id": METHOD_ID, "method_version": METHOD_VERSION,
        "alpha": settings["alpha"], "bootstrap_replicates": settings["bootstrap_replicates"],
        "block_length": _block_length(n), "block_length_rule": BLOCK_LENGTH_RULE,
        "hac_kernel": HAC_KERNEL_ID, "hac_lag": _hac_lag(n), "hac_lag_rule": HAC_LAG_RULE,
        "bootstrap_seed": seed, "family_id": manifest["family_id"],
        "estimated_bootstrap_work": estimated_bootstrap_work,
        "max_bootstrap_work": MAX_BOOTSTRAP_WORK,
        "max_observations": MAX_OBSERVATIONS,
        "max_trials": MAX_TRIALS,
        "family_manifest_sha256": manifest_digest,
        "registry_snapshot_sha256": sha256_json(snapshot),
        "trial_count": len(ordered), "trial_ids": [row["trial_id"] for row in ordered],
        "trials": trial_results, "rejected_trial_ids": rejected, "exclusions": exclusions,
        "evidence_level": "synthetic" if snapshot.get("evidence_level") == "synthetic" else "unverified",
        "registry_trust": "local_prototype_not_independently_authenticated",
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
        "limitations": [
            "HAC-studentized MBB v2 is an unaccepted research candidate pending calibration.",
            "Holm controls family-wise error only when marginal p-values are valid.",
            "HAC/MBB inference is not guaranteed under structural breaks, long memory, or non-stationarity.",
            "A statistical pass is not a profitability guarantee or deployment authorization.",
            "Local registry integrity does not authenticate family completeness against a privileged rewrite.",
            "Final OOS is not read or evaluated by this function.",
        ],
    }
    verdict["verdict_sha256"] = sha256_json(verdict)
    return verdict

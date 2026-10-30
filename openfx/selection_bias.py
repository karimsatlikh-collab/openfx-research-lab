"""M3 family-wise selection-bias gate: moving-block bootstrap + Holm.

This module operates on the complete family snapshot supplied by the local
trial registry. It is an engineering prototype, not a trusted registrar and
not evidence of market profitability. See docs/M3_SELECTION_BIAS_METHOD_DECISION_V1.md.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import sys
from datetime import datetime
from numbers import Real
from typing import Any

METHOD_ID = "M3-HOLM-BLOCK-BOOTSTRAP-V1"
METHOD_VERSION = "1.0.0"
DEFAULT_ALPHA = 0.05
DEFAULT_REPLICATES = 9999
DEFAULT_MIN_OBSERVATIONS = 252


class SelectionBiasError(ValueError):
    """Raised when the family cannot be evaluated safely."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _timestamp_vector(values: Any, expected_length: int) -> list[str]:
    if not isinstance(values, list) or len(values) != expected_length:
        raise SelectionBiasError("timestamps must align one-to-one with returns")
    parsed = []
    for value in values:
        if not isinstance(value, str) or not value:
            raise SelectionBiasError("timestamps must be non-empty ISO-8601 strings")
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SelectionBiasError("timestamp is not valid ISO-8601") from exc
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise SelectionBiasError("timestamps must include an explicit timezone")
        parsed.append(stamp)
    if any(right <= left for left, right in zip(parsed, parsed[1:])):
        raise SelectionBiasError("timestamps must be unique and strictly increasing")
    return values


def _finite_vector(values: Any) -> list[float]:
    if not isinstance(values, list) or not values:
        raise SelectionBiasError("validation_returns must be a non-empty list")
    out = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
            raise SelectionBiasError("returns must contain only finite numeric values")
        out.append(float(value))
    return out


def _studentized_mean(values: list[float]) -> float:
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    if not math.isfinite(variance) or variance <= 0:
        raise SelectionBiasError("zero or invalid return variance")
    result = mean / math.sqrt(variance / n)
    if not math.isfinite(result):
        raise SelectionBiasError("non-finite studentized statistic")
    return result


def _bootstrap_pvalues(series: dict[str, list[float]], *, replicates: int,
                       seed: int) -> dict[str, float]:
    """Synchronized circular moving-block bootstrap under each zero-mean null."""
    ids = sorted(series)
    n = len(series[ids[0]])
    block = max(1, math.ceil(n ** (1.0 / 3.0)))
    observed = {trial_id: _studentized_mean(series[trial_id]) for trial_id in ids}
    centered = {trial_id: [x - sum(series[trial_id]) / n for x in series[trial_id]]
                for trial_id in ids}
    rng = random.Random(seed)
    exceed = {trial_id: 0 for trial_id in ids}
    blocks_needed = math.ceil(n / block)
    for _ in range(replicates):
        indices = []
        for _block in range(blocks_needed):
            start = rng.randrange(n)
            indices.extend((start + offset) % n for offset in range(block))
        indices = indices[:n]
        for trial_id in ids:
            sample = [centered[trial_id][i] for i in indices]
            try:
                statistic = _studentized_mean(sample)
            except SelectionBiasError:
                # A degenerate resample is conservatively counted as an exceedance.
                exceed[trial_id] += 1
                continue
            if statistic >= observed[trial_id]:
                exceed[trial_id] += 1
    return {trial_id: (1 + exceed[trial_id]) / (replicates + 1) for trial_id in ids}


def holm_step_down(pvalues: dict[str, float], alpha: float = DEFAULT_ALPHA) -> dict[str, dict[str, Any]]:
    """Holm step-down with deterministic trial-ID tie breaking."""
    if not isinstance(pvalues, dict) or not pvalues:
        raise SelectionBiasError("pvalues must contain the complete non-empty family")
    if isinstance(alpha, bool) or not isinstance(alpha, Real) or not 0 < float(alpha) < 1:
        raise SelectionBiasError("alpha must be between zero and one")
    clean = {}
    for trial_id, pvalue in pvalues.items():
        if not isinstance(trial_id, str) or not trial_id:
            raise SelectionBiasError("trial IDs must be non-empty strings")
        if isinstance(pvalue, bool) or not isinstance(pvalue, Real) or not math.isfinite(float(pvalue)) or not 0 <= pvalue <= 1:
            raise SelectionBiasError("p-values must be finite and within [0, 1]")
        clean[trial_id] = float(pvalue)
    ordered = sorted(clean, key=lambda key: (clean[key], key))
    m = len(ordered)
    rejected = True
    adjusted_running = 0.0
    result = {}
    for rank, trial_id in enumerate(ordered, start=1):
        threshold = float(alpha) / (m - rank + 1)
        reject = rejected and clean[trial_id] <= threshold
        if not reject:
            rejected = False
        adjusted_running = max(adjusted_running, min(1.0, (m - rank + 1) * clean[trial_id]))
        result[trial_id] = {
            "rank": rank,
            "raw_p_value": clean[trial_id],
            "holm_adjusted_p_value": adjusted_running,
            "threshold": threshold,
            "rejected": bool(reject),
        }
    return result


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("frozen_before_trials") is not True:
        raise SelectionBiasError("a frozen family manifest is required")
    required = ("family_id", "data_profile_id", "cost_profile_id", "validation_split_id",
                "return_frequency", "source_revision", "max_trials", "frozen_at_utc",
                "alpha", "bootstrap_replicates", "min_observations")
    for key in required:
        if key not in manifest or manifest[key] in (None, ""):
            raise SelectionBiasError(f"manifest missing {key}")
    try:
        frozen_at = datetime.fromisoformat(str(manifest["frozen_at_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SelectionBiasError("frozen_at_utc must be ISO-8601") from exc
    if frozen_at.tzinfo is None or frozen_at.utcoffset() is None:
        raise SelectionBiasError("frozen_at_utc must include an explicit timezone")
    string_fields = ("family_id", "data_profile_id", "cost_profile_id",
                     "validation_split_id", "return_frequency", "source_revision")
    if any(not isinstance(manifest[key], str) or not manifest[key].strip()
           for key in string_fields):
        raise SelectionBiasError("family and input binding fields must be non-empty strings")
    if (not isinstance(manifest["max_trials"], int)
            or isinstance(manifest["max_trials"], bool) or manifest["max_trials"] < 1):
        raise SelectionBiasError("max_trials must be a positive integer")
    alpha = manifest.get("alpha", DEFAULT_ALPHA)
    reps = manifest.get("bootstrap_replicates", DEFAULT_REPLICATES)
    minimum = manifest.get("min_observations", DEFAULT_MIN_OBSERVATIONS)
    if isinstance(alpha, bool) or not isinstance(alpha, Real) or float(alpha) != DEFAULT_ALPHA:
        raise SelectionBiasError("M3 v1 requires the frozen alpha=0.05")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps != DEFAULT_REPLICATES:
        raise SelectionBiasError("M3 v1 requires the frozen 9999 bootstrap replicates")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum != DEFAULT_MIN_OBSERVATIONS:
        raise SelectionBiasError("M3 v1 requires the frozen minimum of 252 observations")
    return {"alpha": float(alpha), "bootstrap_replicates": reps, "min_observations": minimum}


def evaluate_registered_family(*, registry: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    """Evaluate all registered trials; callers cannot supply a trial count/list."""
    settings = _validate_manifest(manifest)
    if not hasattr(registry, "family_snapshot"):
        raise SelectionBiasError("registry must expose family_snapshot(family_id)")
    snapshot = registry.family_snapshot(manifest["family_id"])
    if not isinstance(snapshot, dict) or snapshot.get("valid") is not True:
        raise SelectionBiasError("registry family snapshot is invalid")
    if snapshot.get("family_id") != manifest["family_id"]:
        raise SelectionBiasError("registry snapshot family_id does not match the frozen manifest")
    trials = snapshot.get("trials")
    if not isinstance(trials, list) or not trials:
        raise SelectionBiasError("family has no registered trials")
    if len(trials) > manifest["max_trials"]:
        raise SelectionBiasError("family trial budget exceeded")
    trial_ids = [row.get("trial_id") for row in trials if isinstance(row, dict)]
    if len(trial_ids) != len(trials) or len(set(trial_ids)) != len(trial_ids):
        raise SelectionBiasError("registry snapshot contains malformed or duplicate trial IDs")
    indices = [row.get("trial_index") for row in trials]
    if any(isinstance(index, bool) or not isinstance(index, int) or index < 1
           for index in indices) or sorted(indices) != list(range(1, len(trials) + 1)):
        raise SelectionBiasError("registry trial_index values must be unique and contiguous from one")
    ordered_trials = sorted(trials, key=lambda row: (row["trial_index"], row["trial_id"]))
    manifest_digest = sha256_json(manifest)
    for row in ordered_trials:
        registration = row.get("registration_payload")
        if (row.get("registration_outcome") != "pending"
                or not isinstance(registration, dict)
                or registration.get("family_manifest_sha256") != manifest_digest
                or registration.get("registered_before_execution") is not True):
            raise SelectionBiasError(
                "every trial must have a pending pre-execution registration bound to the frozen family manifest"
            )
    pvalues = {row["trial_id"]: 1.0 for row in ordered_trials}
    eligible_series: dict[str, list[float]] = {}
    artifact_hashes: dict[str, str] = {}
    timestamps_ref = None
    exclusions = {}
    for row in ordered_trials:
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
        }
        mismatch = [key for key, expected in bindings.items() if validation.get(key) != expected]
        if mismatch:
            exclusions[trial_id] = "binding_mismatch:" + ",".join(mismatch)
            continue
        try:
            values = _finite_vector(validation.get("returns"))
            if len(values) < settings["min_observations"]:
                exclusions[trial_id] = "insufficient_observations_counted_with_p1"
                continue
            timestamps = _timestamp_vector(validation.get("timestamps"), len(values))
            if timestamps_ref is not None and timestamps != timestamps_ref:
                exclusions[trial_id] = "unaligned_timestamps_counted_with_p1"
                continue
            digest = sha256_json(values)
            if validation.get("returns_sha256") != digest:
                exclusions[trial_id] = "return_artifact_hash_mismatch_counted_with_p1"
                continue
            _studentized_mean(values)
        except (SelectionBiasError, TypeError):
            exclusions[trial_id] = "invalid_or_degenerate_returns_counted_with_p1"
            continue
        if timestamps_ref is None:
            timestamps_ref = timestamps
        eligible_series[trial_id] = values
        artifact_hashes[trial_id] = digest
    if not eligible_series:
        return {
            "decision": "BLOCKED", "reason": "no_eligible_completed_trials",
            "method_id": METHOD_ID, "method_version": METHOD_VERSION,
            "family_id": manifest["family_id"], "trial_count": len(ordered_trials),
            "trial_ids": [row["trial_id"] for row in ordered_trials],
            "exclusions": exclusions, "registry_snapshot_sha256": sha256_json(snapshot),
            "limitations": ["Local registry is not an independently trusted registrar.",
                            "No eligible validation return series; no statistical pass is possible."],
        }
    seed_material = (manifest_digest + METHOD_ID + METHOD_VERSION).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
    raw = _bootstrap_pvalues(eligible_series, replicates=settings["bootstrap_replicates"], seed=seed)
    pvalues.update(raw)
    adjusted = holm_step_down(pvalues, settings["alpha"])
    trial_results = []
    for row in ordered_trials:
        trial_id = row["trial_id"]
        stat = adjusted[trial_id]
        trial_results.append({
            "trial_id": trial_id, "trial_index": row.get("trial_index"),
            "outcome": row.get("outcome"), "eligible": trial_id in eligible_series,
            "exclusion_reason": exclusions.get(trial_id),
            "sample_size": len(eligible_series[trial_id]) if trial_id in eligible_series else 0,
            "returns_sha256": artifact_hashes.get(trial_id),
            **stat,
        })
    rejected = [item["trial_id"] for item in trial_results if item["rejected"] and item["eligible"]]
    verdict = {
        "decision": "PASS" if rejected else "FAIL",
        "reason": "holm_rejected_at_least_one_trial" if rejected else "no_trial_rejected_by_holm",
        "method_id": METHOD_ID, "method_version": METHOD_VERSION,
        "alpha": settings["alpha"], "bootstrap_replicates": settings["bootstrap_replicates"],
        "block_length_rule": "ceil(n^(1/3))", "bootstrap_seed": seed,
        "family_id": manifest["family_id"], "family_manifest_sha256": manifest_digest,
        "registry_snapshot_sha256": sha256_json(snapshot),
        "trial_count": len(ordered_trials), "trial_ids": [row["trial_id"] for row in ordered_trials],
        "trials": trial_results, "rejected_trial_ids": rejected,
        "exclusions": exclusions,
        "evidence_level": "synthetic" if snapshot.get("evidence_level") == "synthetic" else "unverified",
        "registry_trust": "local_prototype_not_independently_authenticated",
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
        "limitations": [
            "Holm controls family-wise error only when marginal p-values are valid.",
            "Moving-block bootstrap validity is not guaranteed under structural breaks, long memory, or non-stationarity.",
            "A statistical pass is not a profitability guarantee or deployment authorization.",
            "Local registry integrity does not authenticate family completeness against a privileged rewrite.",
            "Final OOS is not read or evaluated by this function.",
        ],
    }
    verdict["verdict_sha256"] = sha256_json(verdict)
    return verdict

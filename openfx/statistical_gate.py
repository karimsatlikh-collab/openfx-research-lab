"""Small pre-registered descriptive gate; not a multiple-testing correction."""
from __future__ import annotations

import math
from numbers import Real
from typing import Any


class GateConfigError(ValueError):
    pass


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _finite_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def evaluate_synthetic_summary(summary: dict[str, Any], config: dict[str, Any],
                               *, trial_count: int) -> dict[str, Any]:
    """Apply frozen descriptive thresholds and trial budget to a synthetic summary.

    This deliberately does NOT implement DSR, PBO, or market profitability inference.
    A configured multiple-testing method is recorded as required but not calculated.
    """
    if not isinstance(config, dict):
        raise GateConfigError("gate config must be an object")
    if config.get("frozen_before_trials") is not True:
        raise GateConfigError("gate config must be frozen before trials")
    family = config.get("trial_family_policy")
    if not isinstance(family, dict) or not _positive_int(family.get("max_trials")):
        raise GateConfigError("trial-family max_trials must be a positive integer")
    if not _positive_int(trial_count):
        raise GateConfigError("trial_count must be a positive integer")
    method = config.get("multiple_testing_method")
    if method not in {"DSR", "PBO", "familywise_error", "other_pre_registered"}:
        raise GateConfigError("missing or unsupported pre-registered multiple-testing method")

    thresholds = config.get("acceptance_thresholds")
    if not isinstance(thresholds, dict):
        raise GateConfigError("acceptance_thresholds must be an object")
    supported = {"min_sample_size", "min_mean_return"}
    unknown = set(thresholds) - supported
    if unknown:
        raise GateConfigError(f"unsupported threshold(s): {sorted(unknown)}")
    if not thresholds:
        raise GateConfigError("at least one supported threshold is required")
    if "min_sample_size" in thresholds and not _positive_int(thresholds["min_sample_size"]):
        raise GateConfigError("min_sample_size must be a positive integer")
    if "min_mean_return" in thresholds and not _finite_number(thresholds["min_mean_return"]):
        raise GateConfigError("min_mean_return must be a finite number")

    if not isinstance(summary, dict):
        raise GateConfigError("synthetic summary must be an object")
    if summary.get("evidence_level") != "synthetic" or summary.get("is_market_backtest") is not False:
        raise GateConfigError("gate accepts synthetic-only summaries, not market-backtest claims")
    sample_size = summary.get("sample_size")
    if not _positive_int(sample_size):
        raise GateConfigError("summary sample_size must be a positive integer")
    if "min_mean_return" in thresholds:
        mean_return = summary.get("mean_return")
        if not _finite_number(mean_return):
            raise GateConfigError("summary mean_return must be a finite number")

    if trial_count > family["max_trials"]:
        decision = "fail"
        reason = "trial_budget_exceeded"
    else:
        checks = []
        if "min_sample_size" in thresholds:
            checks.append(sample_size >= thresholds["min_sample_size"])
        if "min_mean_return" in thresholds:
            checks.append(summary["mean_return"] >= thresholds["min_mean_return"])
        decision = "pass" if all(checks) else "fail"
        reason = "descriptive_thresholds"

    return {
        "decision": decision,
        "reason": reason,
        "trial_count": trial_count,
        "gate_id": config.get("gate_id"),
        "gate_version": config.get("version"),
        "multiple_testing_method": method,
        "multiple_testing_correction_applied": False,
        "evidence_level": "synthetic",
        "limitations": [
            "Synthetic/descriptive gate only; not a market backtest.",
            "No DSR/PBO or other multiple-testing correction is calculated.",
            "Passing thresholds does not establish profitability or predictive validity.",
        ],
    }


def evaluate_registered_synthetic_summary(summary: dict[str, Any], config: dict[str, Any],
                                           *, registry: Any, family_id: str) -> dict[str, Any]:
    """Evaluate using a trial count read from the registry, not caller-supplied.

    The local registry is a prototype; this helper does not make it a trusted
    central registrar or protect against a privileged full-ledger rewrite.
    """
    if not hasattr(registry, "trial_count"):
        raise GateConfigError("registry must provide registrar-owned trial_count(family_id)")
    count = registry.trial_count(family_id)
    if not _positive_int(count):
        raise GateConfigError("registry must report a positive integer trial count")
    verdict = evaluate_synthetic_summary(summary, config, trial_count=count)
    verdict["trial_count_source"] = "local_registry"
    verdict["trial_family_id"] = family_id
    verdict["limitations"] = list(verdict.get("limitations", [])) + [
        "Trial count is read from a local prototype ledger, not a trusted central registrar."
    ]
    return verdict

"""Small pre-registered descriptive gate; not a multiple-testing correction."""
from __future__ import annotations
from typing import Any


class GateConfigError(ValueError):
    pass


def evaluate_synthetic_summary(summary: dict[str, Any], config: dict[str, Any],
                               *, trial_count: int) -> dict[str, Any]:
    """Apply frozen descriptive thresholds and trial budget to a synthetic summary.

    This deliberately does NOT implement DSR, PBO, or market profitability inference.
    A configured multiple-testing method is recorded as required but not calculated.
    """
    if config.get("frozen_before_trials") is not True:
        raise GateConfigError("gate config must be frozen before trials")
    family = config.get("trial_family_policy")
    if not isinstance(family, dict) or not isinstance(family.get("max_trials"), int):
        raise GateConfigError("missing trial-family max_trials")
    if trial_count < 1:
        raise GateConfigError("trial_count must be >= 1")
    if trial_count > family["max_trials"]:
        decision = "fail"
        reason = "trial_budget_exceeded"
    else:
        thresholds = config.get("acceptance_thresholds", {})
        checks = []
        if "min_sample_size" in thresholds:
            checks.append(summary.get("sample_size", 0) >= thresholds["min_sample_size"])
        if "min_mean_return" in thresholds:
            checks.append(summary.get("mean_return", float("-inf")) >= thresholds["min_mean_return"])
        if not checks:
            raise GateConfigError("at least one supported threshold is required")
        decision = "pass" if all(checks) else "fail"
        reason = "descriptive_thresholds"
    return {
        "decision": decision,
        "reason": reason,
        "trial_count": trial_count,
        "gate_id": config.get("gate_id"),
        "gate_version": config.get("version"),
        "multiple_testing_method": config.get("multiple_testing_method"),
        "multiple_testing_correction_applied": False,
        "evidence_level": summary.get("evidence_level", "unknown"),
        "limitations": [
            "Synthetic/descriptive gate only; not a market backtest.",
            "No DSR/PBO or other multiple-testing correction is calculated.",
            "Passing thresholds does not establish profitability or predictive validity.",
        ],
    }

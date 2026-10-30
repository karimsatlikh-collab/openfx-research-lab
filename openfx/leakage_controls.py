"""Finite, explicit leakage controls for M2 synthetic fixtures.

These guards cover only the declared fixture classes. They do not prove that
arbitrary feature values or opaque datasets are free of look-ahead.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


class LeakageDetected(ValueError):
    """Raised when a declared leakage condition is found or cannot be compared."""


def _aware_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise LeakageDetected(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LeakageDetected(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LeakageDetected(f"{field} must include a timezone")
    return parsed


def assert_available_by(*, value_name: str, available_at: str,
                        decision_at: str) -> None:
    """Require a feature/label/revision to be available no later than decision."""
    available = _aware_datetime(available_at, f"{value_name}.available_at")
    decision = _aware_datetime(decision_at, "decision_at")
    if available > decision:
        raise LeakageDetected(f"{value_name} was not available at decision time")


def assert_ordered_splits(*, development_end: str, validation_start: str,
                          validation_end: str, final_oos_start: str) -> None:
    """Require strictly non-overlapping chronological development/validation/OOS."""
    dev_end = _aware_datetime(development_end, "development_end")
    val_start = _aware_datetime(validation_start, "validation_start")
    val_end = _aware_datetime(validation_end, "validation_end")
    oos_start = _aware_datetime(final_oos_start, "final_oos_start")
    if not (dev_end < val_start <= val_end < oos_start):
        raise LeakageDetected("development, validation, and final-OOS splits overlap or are unordered")


def assert_feature_window_within_split(*, window_start: str, window_end: str,
                                       split_start: str, split_end: str) -> None:
    """Require a feature's entire source window to remain inside its assigned split."""
    start = _aware_datetime(window_start, "window_start")
    end = _aware_datetime(window_end, "window_end")
    allowed_start = _aware_datetime(split_start, "split_start")
    allowed_end = _aware_datetime(split_end, "split_end")
    if start > end or start < allowed_start or end > allowed_end:
        raise LeakageDetected("feature window crosses or lies outside its assigned split")


def assert_final_oos_access(*, split_name: str, audience: str) -> None:
    """Block final-OOS artifacts from proposer/optimizer-facing interfaces."""
    if split_name == "final_oos" and audience in {"proposer", "optimizer"}:
        raise LeakageDetected("final-OOS data/metrics cannot be exposed to proposer or optimizer")
    if audience not in {"proposer", "optimizer", "independent_validator", "authorized_human"}:
        raise LeakageDetected("unknown audience; access denied")

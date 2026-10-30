"""Pre-registered M2 synthetic calibration campaign.

Synthetic diagnostics only. This module is not a market simulator, backtest,
or multiple-testing correction.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import sys
from typing import Any

PLAN_ID = "m2-synthetic-calibration-v1"
PLAN_VERSION = "1.0.0"
FAMILIES = ("N-IID", "T5-IID", "HET-IID", "AR1-030", "CONTAM-05")
EFFECTS = (0.25, 0.40, 0.60)
N_OBSERVATIONS = 100
REPLICATES_PER_CELL = 1000
DECISION_THRESHOLD = 0.25
MDE = 0.40
WILSON_Z_95 = 1.959963984540054


def _normal(rng: random.Random) -> float:
    return rng.gauss(0.0, 1.0)


def generate_noise(*, family: str, seed: int, n: int = N_OBSERVATIONS) -> list[float]:
    """Generate one zero-mean, unit-marginal-variance synthetic noise stream."""
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n must be a positive integer")
    if family not in FAMILIES:
        raise ValueError(f"unknown generator family: {family}")
    rng = random.Random(seed)

    if family == "N-IID":
        return [_normal(rng) for _ in range(n)]
    if family == "T5-IID":
        # Student-t(df=5) has variance 5/3; multiply by sqrt(3/5).
        result = []
        for _ in range(n):
            numerator = _normal(rng)
            chi_square = rng.gammavariate(2.5, 2.0)
            result.append(numerator / math.sqrt(chi_square / 5.0) * math.sqrt(3.0 / 5.0))
        return result
    if family == "HET-IID":
        return [_normal(rng) * (0.5 if i % 2 == 0 else math.sqrt(1.75))
                for i in range(n)]
    if family == "AR1-030":
        phi = 0.30
        innovation_scale = math.sqrt(1.0 - phi * phi)
        value = _normal(rng)  # stationary initial state, variance 1
        result = []
        for _ in range(n):
            result.append(value)
            value = phi * value + innovation_scale * _normal(rng)
        return result
    # CONTAM-05: 95% N(0, variance=.25), 5% N(0, variance=15.25).
    # Mixture variance is .95*.25 + .05*15.25 = 1.
    result = []
    for _ in range(n):
        if rng.random() < 0.95:
            result.append(0.5 * _normal(rng))
        else:
            result.append(math.sqrt(15.25) * _normal(rng))
    return result


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def wilson_interval(successes: int, trials: int, *, z: float = WILSON_Z_95) -> tuple[float, float]:
    """Two-sided Wilson score interval for a binomial proportion."""
    if (not isinstance(trials, int) or isinstance(trials, bool) or trials < 1
            or not isinstance(successes, int) or isinstance(successes, bool)
            or successes < 0 or successes > trials
            or not isinstance(z, (int, float)) or isinstance(z, bool)
            or not math.isfinite(float(z)) or z <= 0):
        raise ValueError("invalid Wilson interval inputs")
    p = successes / trials
    z2 = z * z
    denominator = 1.0 + z2 / trials
    center = (p + z2 / (2.0 * trials)) / denominator
    radius = (z / denominator) * math.sqrt(
        p * (1.0 - p) / trials + z2 / (4.0 * trials * trials)
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def seed_cells() -> list[dict[str, Any]]:
    """Return the frozen, disjoint seed-to-cell allocation."""
    cells = []
    seed = 100000
    for family in FAMILIES:
        cells.append({"kind": "null", "family": family, "effect": 0.0,
                      "seed_start": seed, "seed_end": seed + 999})
        seed += 1000
    seed = 200000
    for family in FAMILIES:
        for effect in EFFECTS:
            cells.append({"kind": "power", "family": family, "effect": effect,
                          "seed_start": seed, "seed_end": seed + 999})
            seed += 1000
    return cells


def run_cell(*, kind: str, family: str, effect: float, seed_start: int,
             count: int = REPLICATES_PER_CELL) -> dict[str, Any]:
    """Execute a single frozen cell and retain one canonical record per seed."""
    if kind not in {"null", "power"}:
        raise ValueError("kind must be null or power")
    if family not in FAMILIES:
        raise ValueError("unknown generator family")
    if not isinstance(count, int) or isinstance(count, bool) or count != REPLICATES_PER_CELL:
        raise ValueError("calibration cell size is frozen at exactly 1000 replicates")
    if kind == "null" and effect != 0.0:
        raise ValueError("null cells must use zero effect")
    if kind == "power" and effect not in EFFECTS:
        raise ValueError("power effect is not in the frozen plan")

    records = []
    successes = 0
    for seed in range(seed_start, seed_start + count):
        noise = generate_noise(family=family, seed=seed, n=N_OBSERVATIONS)
        returns = [value + effect for value in noise]
        mean_return = math.fsum(returns) / len(returns)
        passed = mean_return >= DECISION_THRESHOLD
        successes += int(passed)
        digest = hashlib.sha256(canonical_json(returns).encode("utf-8")).hexdigest()
        records.append({
            "plan_id": PLAN_ID, "plan_version": PLAN_VERSION,
            "kind": kind, "family": family, "effect": effect,
            "seed": seed, "sample_size": N_OBSERVATIONS,
            "mean_return": mean_return, "passed": passed,
            "returns_sha256": digest, "evidence_level": "synthetic",
        })

    lower, upper = wilson_interval(successes, count)
    rate = successes / count
    accepted = (upper <= 0.05) if kind == "null" else (
        lower >= 0.80 if effect == MDE else None
    )
    return {
        "plan_id": PLAN_ID, "plan_version": PLAN_VERSION,
        "kind": kind, "family": family, "effect": effect,
        "seed_start": seed_start, "seed_end": seed_start + count - 1,
        "successes": successes, "trials": count, "rate": rate,
        "wilson_95_lower": lower, "wilson_95_upper": upper,
        "acceptance": accepted, "records": records,
    }


def run_campaign() -> dict[str, Any]:
    """Run all 20,000 pre-registered replicates and return raw plus aggregate data."""
    cells = []
    for allocation in seed_cells():
        cell_args = {key: value for key, value in allocation.items() if key != "seed_end"}
        cells.append(run_cell(**cell_args))
    null_ok = all(cell["acceptance"] is True for cell in cells if cell["kind"] == "null")
    mde_ok = all(cell["acceptance"] is True for cell in cells
                 if cell["kind"] == "power" and cell["effect"] == MDE)
    return {
        "plan_id": PLAN_ID, "plan_version": PLAN_VERSION,
        "evidence_level": "synthetic", "is_market_backtest": False,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "acceptance": {
            "null_false_positive_all_families": null_ok,
            "mde_power_all_families": mde_ok,
            "overall_calibration_pass": null_ok and mde_ok,
        },
        "cells": [
            {key: value for key, value in cell.items() if key != "records"}
            for cell in cells
        ],
        "raw_records": [record for cell in cells for record in cell["records"]],
    }

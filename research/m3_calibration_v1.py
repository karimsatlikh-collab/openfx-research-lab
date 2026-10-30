"""Independent synthetic calibration runner for M3 v1.

Optional dependencies: NumPy and Numba. This module intentionally does not import
openfx.selection_bias; it independently implements the frozen bootstrap and
Holm procedure for calibration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import numba
import numpy as np
from numba import njit

N = 252
BOOTSTRAP_REPLICATES = 9999
BLOCK_LENGTH = math.ceil(N ** (1.0 / 3.0))
ALPHA = 0.05
MDE = 0.35
OUTER_REPLICATES = 1000
COPULA_FAMILIES = 100_000
GENERATORS = ("N1_GAUSSIAN_IID", "N2_STUDENT_T5_IID", "N3_AR1_GAUSSIAN",
              "N4_GARCH_1_1", "N5_AR1_STUDENT_T5")
FAMILY_SIZES = (5, 20)
CORRELATIONS = (0.0, 0.5, 0.9)
WILSON_Z = 1.959963984540054


@njit
def _count_bootstrap_exceedances(centered, indices, observed):
    n = centered.shape[0]
    count = 0
    for b in range(indices.shape[0]):
        mean = 0.0
        for j in range(n):
            mean += centered[indices[b, j]]
        mean /= n
        variance = 0.0
        for j in range(n):
            delta = centered[indices[b, j]] - mean
            variance += delta * delta
        variance /= n - 1
        if variance <= 0.0:
            count += 1
        else:
            statistic = mean / math.sqrt(variance / n)
            if statistic >= observed:
                count += 1
    return count


@njit
def _copula_holm_counts(z, null_sorted, alternative_sorted, use_alternative,
                        alpha):
    families, family_size = z.shape
    null_fwer = 0
    alternative_power = 0
    root_two = math.sqrt(2.0)
    for row in range(families):
        pvalues = np.empty(family_size, dtype=np.float64)
        order = np.arange(family_size)
        for col in range(family_size):
            u = 0.5 * (1.0 + math.erf(z[row, col] / root_two))
            index = int(u * null_sorted.shape[0])
            if index >= null_sorted.shape[0]:
                index = null_sorted.shape[0] - 1
            if use_alternative and col == 0:
                pvalues[col] = alternative_sorted[index]
            else:
                pvalues[col] = null_sorted[index]
        # Stable insertion sort by (p-value, trial index).
        for i in range(1, family_size):
            key = order[i]
            j = i - 1
            while j >= 0 and (pvalues[order[j]] > pvalues[key] or
                              (pvalues[order[j]] == pvalues[key] and order[j] > key)):
                order[j + 1] = order[j]
                j -= 1
            order[j + 1] = key
        any_rejected = False
        signal_rejected = False
        for rank in range(family_size):
            trial_index = order[rank]
            threshold = alpha / (family_size - rank)
            if pvalues[trial_index] <= threshold:
                any_rejected = True
                if trial_index == 0:
                    signal_rejected = True
            else:
                break
        if any_rejected and not use_alternative:
            null_fwer += 1
        if signal_rejected and use_alternative:
            alternative_power += 1
    return null_fwer, alternative_power


def _series(generator_id: str, seed: int, effect: float = 0.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if generator_id == "N1_GAUSSIAN_IID":
        values = rng.standard_normal(N)
    elif generator_id == "N2_STUDENT_T5_IID":
        values = rng.standard_t(5, N) * math.sqrt(3.0 / 5.0)
    elif generator_id == "N3_AR1_GAUSSIAN":
        eps = rng.standard_normal(N)
        values = np.empty(N, dtype=np.float64)
        values[0] = eps[0]
        scale = math.sqrt(1.0 - 0.30 ** 2)
        for i in range(1, N):
            values[i] = 0.30 * values[i - 1] + scale * eps[i]
    elif generator_id == "N4_GARCH_1_1":
        eps = rng.standard_normal(N)
        values = np.empty(N, dtype=np.float64)
        variance = 1.0
        for i in range(N):
            values[i] = math.sqrt(variance) * eps[i]
            variance = 0.05 + 0.05 * values[i] ** 2 + 0.90 * variance
    elif generator_id == "N5_AR1_STUDENT_T5":
        eps = rng.standard_t(5, N) * math.sqrt(3.0 / 5.0)
        values = np.empty(N, dtype=np.float64)
        values[0] = eps[0]
        scale = math.sqrt(1.0 - 0.30 ** 2)
        for i in range(1, N):
            values[i] = 0.30 * values[i - 1] + scale * eps[i]
    else:
        raise ValueError(f"unknown generator: {generator_id}")
    return np.asarray(values + effect, dtype=np.float64)


def _series_sha256(values: np.ndarray) -> str:
    payload = json.dumps([float(x) for x in values], separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _bootstrap_pvalue(values: np.ndarray, seed: int) -> float:
    n = len(values)
    blocks = math.ceil(n / BLOCK_LENGTH)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(BOOTSTRAP_REPLICATES, blocks),
                          dtype=np.int32)
    offsets = np.arange(BLOCK_LENGTH, dtype=np.int32)
    indices = ((starts[:, :, None] + offsets[None, None, :]) % n)
    indices = indices.reshape(BOOTSTRAP_REPLICATES, -1)[:, :n]
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    if not math.isfinite(std) or std <= 0.0:
        raise ValueError("degenerate observed return series")
    observed = mean / (std / math.sqrt(n))
    centered = np.asarray(values - mean, dtype=np.float64)
    exceedances = int(_count_bootstrap_exceedances(centered, indices, observed))
    return (1 + exceedances) / (BOOTSTRAP_REPLICATES + 1)


def _wilson(successes: int, total: int) -> dict[str, float]:
    p = successes / total
    z2 = WILSON_Z ** 2
    denominator = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denominator
    margin = WILSON_Z * math.sqrt(
        p * (1.0 - p) / total + z2 / (4.0 * total * total)
    ) / denominator
    return {"estimate": p, "lower_95": max(0.0, center - margin),
            "upper_95": min(1.0, center + margin),
            "successes": successes, "total": total}


def _marginal_campaign(generator_id: str, generator_index: int,
                       alternative: bool) -> dict:
    base = 20_000_000 if alternative else 10_000_000
    replicates = []
    pvalues = []
    for replicate in range(OUTER_REPLICATES):
        data_seed = base + generator_index * 100_000 + replicate
        bootstrap_seed = 40_000_000 + data_seed
        values = _series(generator_id, data_seed, MDE if alternative else 0.0)
        pvalue = _bootstrap_pvalue(values, bootstrap_seed)
        pvalues.append(pvalue)
        replicates.append({
            "replicate": replicate, "data_seed": data_seed,
            "bootstrap_seed": bootstrap_seed,
            "returns_sha256": _series_sha256(values), "p_value": pvalue,
        })
    ordered = sorted(pvalues)
    return {"generator": generator_id, "alternative": alternative,
            "effect": MDE if alternative else 0.0,
            "p_values": pvalues, "p_values_sorted": ordered,
            "replicates": replicates}


def _copula_cell(generator_index: int, family_size: int,
                 correlation: float, null_sorted: list[float],
                 alternative_sorted: list[float], alternative: bool) -> dict:
    size_index = FAMILY_SIZES.index(family_size)
    corr_index = CORRELATIONS.index(correlation)
    seed = (30_000_000 + generator_index * 1_000_000 +
            size_index * 100_000 + corr_index * 10_000)
    rng = np.random.default_rng(seed)
    factor = rng.standard_normal((COPULA_FAMILIES, 1))
    idiosyncratic = rng.standard_normal((COPULA_FAMILIES, family_size))
    z = math.sqrt(correlation) * factor + math.sqrt(1.0 - correlation) * idiosyncratic
    null_count, power_count = _copula_holm_counts(
        z, np.asarray(null_sorted, dtype=np.float64),
        np.asarray(alternative_sorted, dtype=np.float64), alternative, ALPHA
    )
    result = {
        "family_size": family_size, "correlation": correlation,
        "seed": seed, "families": COPULA_FAMILIES,
    }
    if alternative:
        result["mde_family_power"] = _wilson(power_count, COPULA_FAMILIES)
    else:
        result["global_null_fwer"] = _wilson(null_count, COPULA_FAMILIES)
    return result


def run_campaign(plan_sha256: str, engine_revision: str) -> dict:
    marginal_null = []
    marginal_alternative = []
    copula_results = []
    for generator_index, generator_id in enumerate(GENERATORS):
        null_result = _marginal_campaign(generator_id, generator_index, False)
        alternative_result = _marginal_campaign(generator_id, generator_index, True)
        null_false_positives = sum(p <= ALPHA for p in null_result["p_values"])
        alternative_detections = sum(p <= ALPHA for p in alternative_result["p_values"])
        null_result["summary"] = _wilson(null_false_positives, OUTER_REPLICATES)
        alternative_result["summary"] = _wilson(alternative_detections, OUTER_REPLICATES)
        null_sorted = null_result["p_values_sorted"]
        alternative_sorted = alternative_result["p_values_sorted"]
        marginal_null.append(null_result)
        marginal_alternative.append(alternative_result)
        for family_size in FAMILY_SIZES:
            for correlation in CORRELATIONS:
                copula_results.append({
                    "generator": generator_id, "scenario": "global_null",
                    **_copula_cell(generator_index, family_size, correlation,
                                   null_sorted, alternative_sorted, False),
                })
                copula_results.append({
                    "generator": generator_id, "scenario": "one_mde_candidate",
                    **_copula_cell(generator_index, family_size, correlation,
                                   null_sorted, alternative_sorted, True),
                })
    campaign = {
        "plan_id": "M3-CALIBRATION-V1",
        "method_id": "M3-HOLM-BLOCK-BOOTSTRAP-V1",
        "method_version": "1.0.0",
        "engine_revision": engine_revision,
        "plan_sha256": plan_sha256,
        "settings": {
            "n": N, "alpha": ALPHA, "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "block_length": BLOCK_LENGTH, "mde": MDE,
            "outer_replicates_per_generator_and_scenario": OUTER_REPLICATES,
            "copula_families_per_cell": COPULA_FAMILIES,
            "family_sizes": FAMILY_SIZES, "correlations": CORRELATIONS,
        },
        "runtime": {
            "python": sys.version.split()[0], "numpy": np.__version__,
            "numba": numba.__version__, "platform": platform.platform(),
        },
        "marginal_null": marginal_null,
        "marginal_alternative": marginal_alternative,
        "copula_results": copula_results,
    }
    campaign["campaign_sha256"] = hashlib.sha256(
        json.dumps(campaign, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return campaign


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--engine-revision", required=True)
    parser.add_argument("--output", default="artifacts/m3_calibration_v1.json")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing campaign artifact: {output}")
    result = run_campaign(args.plan_sha256, args.engine_revision)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({
        "output": str(output), "campaign_sha256": result["campaign_sha256"],
        "null_generators": len(result["marginal_null"]),
        "alternative_generators": len(result["marginal_alternative"]),
        "copula_cells": len(result["copula_results"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()

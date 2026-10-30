"""Cell-based independent calibration runner for M3 HAC-MBB v2.

Requires the optional pinned NumPy/Numba dependencies. This runner does not
import the production M3 v2 evaluator. Each immutable output file is one
marginal or direct-family cell; reruns must use a new path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
from pathlib import Path

import numba
import numpy as np
from numba import njit

N = 252
BOOTSTRAP_REPLICATES = 9999
ALPHA = 0.05
MDE = 0.35
MARGINAL_NULL_REPLICATES = 5000
MARGINAL_MDE_REPLICATES = 1000
FAMILY_REPLICATES = 1000
FAMILY_SIZE = 20
BLOCK_LENGTH = 7
HAC_LAG = 7
WILSON_Z = 1.959963984540054
GENERATORS = ("N1_GAUSSIAN_IID", "N2_STUDENT_T5_IID", "N3_AR1_GAUSSIAN",
              "N4_GARCH_1_1", "N5_AR1_STUDENT_T5")
CORRELATIONS = (0.0, 0.5, 0.9)


@njit
def _hac_statistic(values, lag):
    n = values.shape[0]
    mean = 0.0
    for i in range(n):
        mean += values[i]
    mean /= n
    lrv = 0.0
    for i in range(n):
        delta = values[i] - mean
        lrv += delta * delta
    lrv /= n
    for offset in range(1, lag + 1):
        covariance = 0.0
        for i in range(offset, n):
            covariance += (values[i] - mean) * (values[i - offset] - mean)
        covariance /= n
        weight = 1.0 - offset / (lag + 1.0)
        lrv += 2.0 * weight * covariance
    if lrv <= 0.0 or not math.isfinite(lrv):
        return math.nan
    return mean / math.sqrt(lrv / n)


@njit
def _family_bootstrap_pvalues(centered, observed, indices, lag):
    family_size, n = centered.shape
    exceedances = np.zeros(family_size, dtype=np.int64)
    sample = np.empty(n, dtype=np.float64)
    for b in range(indices.shape[0]):
        for trial in range(family_size):
            for i in range(n):
                sample[i] = centered[trial, indices[b, i]]
            statistic = _hac_statistic(sample, lag)
            if not math.isfinite(statistic) or statistic >= observed[trial]:
                exceedances[trial] += 1
    return (exceedances + 1.0) / (indices.shape[0] + 1.0)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha256(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _series_sha256(values: np.ndarray) -> str:
    return _sha256([float(x) for x in values])


def _make_indices(seed: int, replicates: int = BOOTSTRAP_REPLICATES) -> np.ndarray:
    rng = random.Random(seed)
    blocks = math.ceil(N / BLOCK_LENGTH)
    starts = np.fromiter(
        (rng.randrange(N) for _ in range(replicates * blocks)),
        dtype=np.int32,
    ).reshape(replicates, blocks)
    offsets = np.arange(BLOCK_LENGTH, dtype=np.int32)
    return ((starts[:, :, None] + offsets[None, None, :]) % N).reshape(
        replicates, -1
    )[:, :N]


def _bootstrap_pvalues(series: np.ndarray, seed: int,
                       replicates: int = BOOTSTRAP_REPLICATES) -> np.ndarray:
    observed = np.empty(series.shape[0], dtype=np.float64)
    centered = np.empty_like(series, dtype=np.float64)
    for trial in range(series.shape[0]):
        observed[trial] = _hac_statistic(series[trial], HAC_LAG)
        mean = sum(float(value) for value in series[trial]) / N
        centered[trial] = series[trial] - mean
    if not np.all(np.isfinite(observed)):
        raise ValueError("invalid observed HAC statistic")
    indices = _make_indices(seed, replicates)
    return _family_bootstrap_pvalues(centered, observed, indices, HAC_LAG)


def _generate_family(generator_id: str, seed: int, rho: float,
                     mde: bool) -> np.ndarray:
    rng = np.random.default_rng(seed)
    common = rng.standard_normal(N)
    idiosyncratic = rng.standard_normal((FAMILY_SIZE, N))
    gaussian = math.sqrt(rho) * common[None, :] + math.sqrt(1.0 - rho) * idiosyncratic

    if generator_id == "N1_GAUSSIAN_IID":
        values = gaussian
    elif generator_id in ("N2_STUDENT_T5_IID", "N5_AR1_STUDENT_T5"):
        chi_square = rng.chisquare(5, size=N)
        values = gaussian / np.sqrt(chi_square[None, :] / 5.0) * math.sqrt(3.0 / 5.0)
    elif generator_id == "N3_AR1_GAUSSIAN":
        values = np.empty_like(gaussian)
        values[:, 0] = gaussian[:, 0]
        scale = math.sqrt(1.0 - 0.30 ** 2)
        for t in range(1, N):
            values[:, t] = 0.30 * values[:, t - 1] + scale * gaussian[:, t]
    elif generator_id == "N4_GARCH_1_1":
        values = np.empty_like(gaussian)
        variance = np.ones(FAMILY_SIZE, dtype=np.float64)
        for t in range(N):
            values[:, t] = np.sqrt(variance) * gaussian[:, t]
            variance = 0.05 + 0.05 * values[:, t] ** 2 + 0.90 * variance
    else:
        raise ValueError(f"unknown generator: {generator_id}")

    if generator_id == "N5_AR1_STUDENT_T5":
        ar = np.empty_like(values)
        ar[:, 0] = values[:, 0]
        scale = math.sqrt(1.0 - 0.30 ** 2)
        for t in range(1, N):
            ar[:, t] = 0.30 * ar[:, t - 1] + scale * values[:, t]
        values = ar
    if mde:
        values[0] = values[0] + MDE
    return np.asarray(values, dtype=np.float64)


def _generate_marginal(generator_id: str, seed: int, effect: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if generator_id == "N1_GAUSSIAN_IID":
        values = rng.standard_normal(N)
    elif generator_id == "N2_STUDENT_T5_IID":
        values = rng.standard_t(5, N) * math.sqrt(3.0 / 5.0)
    elif generator_id == "N3_AR1_GAUSSIAN":
        eps = rng.standard_normal(N)
        values = np.empty(N)
        values[0] = eps[0]
        scale = math.sqrt(1.0 - 0.30 ** 2)
        for t in range(1, N):
            values[t] = 0.30 * values[t - 1] + scale * eps[t]
    elif generator_id == "N4_GARCH_1_1":
        eps = rng.standard_normal(N)
        values = np.empty(N)
        variance = 1.0
        for t in range(N):
            values[t] = math.sqrt(variance) * eps[t]
            variance = 0.05 + 0.05 * values[t] ** 2 + 0.90 * variance
    elif generator_id == "N5_AR1_STUDENT_T5":
        eps = rng.standard_t(5, N) * math.sqrt(3.0 / 5.0)
        values = np.empty(N)
        values[0] = eps[0]
        scale = math.sqrt(1.0 - 0.30 ** 2)
        for t in range(1, N):
            values[t] = 0.30 * values[t - 1] + scale * eps[t]
    else:
        raise ValueError(f"unknown generator: {generator_id}")
    return np.asarray(values + effect, dtype=np.float64)


def _holm_rejections(pvalues: list[float], ids: list[str]) -> list[bool]:
    order = sorted(range(len(pvalues)), key=lambda i: (pvalues[i], ids[i]))
    rejected = [False] * len(pvalues)
    keep_rejecting = True
    m = len(pvalues)
    for rank, index in enumerate(order, start=1):
        threshold = ALPHA / (m - rank + 1)
        if keep_rejecting and pvalues[index] <= threshold:
            rejected[index] = True
        else:
            keep_rejecting = False
    return rejected


def _wilson(successes: int, total: int) -> dict:
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


def run_marginal_cell(generator_id: str, alternative: bool,
                      plan_sha256: str, engine_revision: str,
                      runner_revision: str) -> dict:
    gi = GENERATORS.index(generator_id)
    count = MARGINAL_MDE_REPLICATES if alternative else MARGINAL_NULL_REPLICATES
    data_base = 1_400_000_000 if alternative else 1_300_000_000
    bootstrap_base = 1_900_000_000 if alternative else 1_800_000_000
    rows = []
    successes = 0
    failures = 0
    for replicate in range(count):
        data_seed = data_base + gi * 100_000 + replicate
        bootstrap_seed = bootstrap_base + data_seed
        try:
            values = _generate_marginal(generator_id, data_seed, MDE if alternative else 0.0)
            series_hash = _series_sha256(values)
            pvalue = float(_bootstrap_pvalues(values.reshape(1, N), bootstrap_seed)[0])
            status, error = "completed", None
        except (ValueError, FloatingPointError, OverflowError) as exc:
            pvalue, series_hash = 1.0, None
            status, error = "failed", f"{type(exc).__name__}: {exc}"
            failures += 1
        successes += int(pvalue <= ALPHA)
        rows.append({"replicate": replicate, "data_seed": data_seed,
                     "bootstrap_seed": bootstrap_seed, "engine_revision": engine_revision,
            "returns_sha256": series_hash,
                     "p_value": pvalue, "status": status, "failure": error})
    cell = {
        "plan_id": "M3-HAC-MBB-CALIBRATION-V2-1",
        "method_id": "M3-HOLM-HAC-MBB-V2", "method_version": "2.0.1",
        "phase": "marginal_mde" if alternative else "marginal_null",
        "generator": generator_id, "effect": MDE if alternative else 0.0,
        "engine_revision": engine_revision, "runner_revision": runner_revision,
        "plan_sha256": plan_sha256, "runtime": _runtime(),
        "settings": {"n": N, "alpha": ALPHA, "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                     "block_length": BLOCK_LENGTH, "hac_lag": HAC_LAG,
                     "max_observations": 100_000, "max_trials": 10_000,
                     "max_bootstrap_work": 1_000_000_000,
                     "estimated_bootstrap_work_per_replicate": BOOTSTRAP_REPLICATES * N * (HAC_LAG + 1),
                     "replicates": count},
        "failed_replicates": failures, "summary": _wilson(successes, count),
        "replicates": rows,
    }
    cell["cell_sha256"] = _sha256(cell)
    return cell


def run_family_cell(generator_id: str, rho: float, alternative: bool,
                    plan_sha256: str, engine_revision: str,
                    runner_revision: str) -> dict:
    gi = GENERATORS.index(generator_id)
    ci = CORRELATIONS.index(rho)
    data_base = 1_600_000_000 if alternative else 1_500_000_000
    records = []
    fwer5 = fwer20 = power5 = power20 = failures = 0
    for family_index in range(FAMILY_REPLICATES):
        family_seed = data_base + gi * 1_000_000 + ci * 10_000 + family_index
        bootstrap_seed = 1_700_000_000 + family_seed
        hashes = None
        try:
            values = _generate_family(generator_id, family_seed, rho, alternative)
            hashes = [_series_sha256(values[i]) for i in range(FAMILY_SIZE)]
            pvalues = [float(x) for x in _bootstrap_pvalues(values, bootstrap_seed)]
            ids = [f"trial_{i:02d}" for i in range(FAMILY_SIZE)]
            rejected20 = _holm_rejections(pvalues, ids)
            rejected5 = _holm_rejections(pvalues[:5], ids[:5])
            fwer5_result = any(rejected5)
            fwer20_result = any(rejected20)
            power5_result = bool(rejected5[0]) if alternative else False
            power20_result = bool(rejected20[0]) if alternative else False
            status, error = "completed", None
        except (ValueError, FloatingPointError, OverflowError) as exc:
            pvalues = [1.0] * FAMILY_SIZE
            fwer5_result = fwer20_result = power5_result = power20_result = False
            status, error = "failed", f"{type(exc).__name__}: {exc}"
            failures += 1
        fwer5 += int(fwer5_result and not alternative)
        fwer20 += int(fwer20_result and not alternative)
        power5 += int(power5_result)
        power20 += int(power20_result)
        realized_corr = None
        if hashes is not None:
            corr_matrix = np.corrcoef(values)
            upper = corr_matrix[np.triu_indices(FAMILY_SIZE, k=1)]
            realized_corr = float(np.mean(upper))
        record = {
            "family_index": family_index, "family_seed": family_seed,
            "bootstrap_seed": bootstrap_seed, "status": status, "failure": error,
            "trial_ids": [f"trial_{i:02d}" for i in range(FAMILY_SIZE)],
            "trial_engine_revisions": [engine_revision] * FAMILY_SIZE,
            "trial_return_hashes": hashes, "raw_p_values": pvalues,
            "realized_average_pairwise_return_correlation": realized_corr,
        }
        if alternative:
            record["mde_candidate_rejected_m5"] = bool(power5_result)
            record["mde_candidate_rejected_m20"] = bool(power20_result)
        else:
            record["global_null_fwer_m5"] = bool(fwer5_result)
            record["global_null_fwer_m20"] = bool(fwer20_result)
        records.append(record)
    cell = {
        "plan_id": "M3-HAC-MBB-CALIBRATION-V2-1",
        "method_id": "M3-HOLM-HAC-MBB-V2", "method_version": "2.0.1",
        "phase": "family_mde" if alternative else "family_null",
        "generator": generator_id, "rho": rho,
        "engine_revision": engine_revision, "runner_revision": runner_revision,
        "plan_sha256": plan_sha256, "runtime": _runtime(),
        "settings": {"n": N, "alpha": ALPHA, "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                     "block_length": BLOCK_LENGTH, "hac_lag": HAC_LAG,
                     "max_observations": 100_000, "max_trials": 10_000,
                     "max_bootstrap_work": 1_000_000_000,
                     "estimated_bootstrap_work_per_family": BOOTSTRAP_REPLICATES * FAMILY_SIZE * N * (HAC_LAG + 1),
                     "families": FAMILY_REPLICATES, "family_size_primary": FAMILY_SIZE,
                     "family_size_secondary": 5},
        "failed_families": failures,
        "summary": ({
            "mde_family_power_m5": _wilson(power5, FAMILY_REPLICATES),
            "mde_family_power_m20": _wilson(power20, FAMILY_REPLICATES),
        } if alternative else {
            "global_null_fwer_m5": _wilson(fwer5, FAMILY_REPLICATES),
            "global_null_fwer_m20": _wilson(fwer20, FAMILY_REPLICATES),
        }),
        "families": records,
    }
    cell["cell_sha256"] = _sha256(cell)
    return cell


def _runtime() -> dict:
    return {"python": sys.version.split()[0], "numpy": np.__version__,
            "numba": numba.__version__, "platform": platform.platform()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("marginal-null", "marginal-mde",
                                            "family-null", "family-mde"), required=True)
    parser.add_argument("--generator", choices=GENERATORS, required=True)
    parser.add_argument("--rho", type=float, choices=CORRELATIONS)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--engine-revision", required=True)
    parser.add_argument("--runner-revision", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing cell artifact: {output}")
    family_phase = args.phase.startswith("family-")
    if family_phase and args.rho is None:
        raise SystemExit("--rho is required for family phases")
    if not family_phase and args.rho is not None:
        raise SystemExit("--rho is only valid for family phases")
    if args.phase == "marginal-null":
        cell = run_marginal_cell(args.generator, False, args.plan_sha256,
                                 args.engine_revision, args.runner_revision)
    elif args.phase == "marginal-mde":
        cell = run_marginal_cell(args.generator, True, args.plan_sha256,
                                 args.engine_revision, args.runner_revision)
    elif args.phase == "family-null":
        cell = run_family_cell(args.generator, args.rho, False, args.plan_sha256,
                               args.engine_revision, args.runner_revision)
    else:
        cell = run_family_cell(args.generator, args.rho, True, args.plan_sha256,
                               args.engine_revision, args.runner_revision)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(cell, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"output": str(output), "cell_sha256": cell["cell_sha256"],
                      "failed": cell.get("failed_replicates", cell.get("failed_families", 0)),
                      "summary": cell["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()

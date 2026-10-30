"""Cross-check selected independent M3 v2 calibration primitives against production."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m3_calibration_provenance import verify_execution_bindings

import numpy as np

from openfx.selection_bias_v2 import (
    _bootstrap_pvalues as production_bootstrap_pvalues,
    _hac_studentized_mean,
    holm_step_down,
    sha256_json,
)
from research.m3_hac_mbb_v2_calibration import (
    CORRELATIONS,
    GENERATORS,
    MDE,
    _bootstrap_pvalues as independent_bootstrap_pvalues,
    _generate_family,
    _hac_statistic,
    _holm_rejections,
    _series_sha256,
)


def _fixture_series() -> dict[str, list[float]]:
    result = {}
    for trial in range(3):
        result[f"trial_{trial:02d}"] = [
            0.02 * (trial + 1) + (((i * 17 + trial * 13) % 31) - 15) * 0.001
            for i in range(252)
        ]
    return result


def validate(plan_file: Path, engine_revision: str) -> dict:
    provenance = verify_execution_bindings(
        plan_file, engine_revision, Path(__file__).resolve().parents[1] / "research" / "m3_hac_mbb_v2_calibration.py",
        Path(__file__).resolve().parents[1] / "openfx" / "selection_bias_v2.py",
    )
    series = _fixture_series()
    seed = 424242
    replicates = 199
    production = production_bootstrap_pvalues(
        series, replicates=replicates, seed=seed
    )
    matrix = np.asarray([series[key] for key in sorted(series)], dtype=np.float64)
    independent = independent_bootstrap_pvalues(
        matrix, seed=seed, replicates=replicates
    )
    comparisons = {}
    for index, trial_id in enumerate(sorted(series)):
        production_stat = _hac_studentized_mean(series[trial_id], 7)
        independent_stat = float(_hac_statistic(matrix[index], 7))
        if abs(production_stat - independent_stat) > 1e-12:
            raise AssertionError(f"HAC statistic mismatch for {trial_id}")
        if abs(production[trial_id] - float(independent[index])) > 1e-12:
            raise AssertionError(f"bootstrap p-value mismatch for {trial_id}")
        comparisons[trial_id] = {
            "hac_statistic": production_stat,
            "p_value": production[trial_id],
            "production_independent_absolute_difference":
                abs(production[trial_id] - float(independent[index])),
            "returns_sha256": sha256_json(series[trial_id]),
        }

    pvalues = {"a": 0.001, "b": 0.03, "c": 0.04, "d": 1.0}
    production_holm = holm_step_down(pvalues)
    ids = sorted(pvalues)
    independent_rejections = _holm_rejections(
        [pvalues[key] for key in ids], ids
    )
    for index, trial_id in enumerate(ids):
        if production_holm[trial_id]["rejected"] != independent_rejections[index]:
            raise AssertionError(f"Holm rejection mismatch for {trial_id}")

    family_fixtures = []
    for generator_index, generator in enumerate(GENERATORS):
        for correlation_index, rho in enumerate(CORRELATIONS):
            family_seed = 123456 + generator_index * 1000 + correlation_index * 10
            null_family = _generate_family(generator, family_seed, rho, False)
            mde_family = _generate_family(generator, family_seed, rho, True)
            if null_family.shape != (20, 252) or not np.all(np.isfinite(null_family)):
                raise AssertionError(f"invalid generated family: {generator}, rho={rho}")
            if not np.allclose(mde_family[0] - null_family[0], MDE, rtol=0.0, atol=1e-12):
                raise AssertionError(f"planted MDE mismatch: {generator}, rho={rho}")
            if not np.array_equal(mde_family[1:], null_family[1:]):
                raise AssertionError(f"MDE changed a non-signal trial: {generator}, rho={rho}")
            corr = np.corrcoef(null_family)
            realized = float(np.mean(corr[np.triu_indices(20, k=1)]))
            fixture = {
                "generator": generator, "rho": rho, "family_seed": family_seed,
                "realized_average_pairwise_return_correlation": realized,
                "trial_return_hashes": [_series_sha256(null_family[i]) for i in range(20)],
            }
            if rho == 0.5:
                family_series = {f"trial_{i:02d}": null_family[i].tolist() for i in range(20)}
                family_prod = production_bootstrap_pvalues(
                    family_series, replicates=replicates, seed=seed + family_seed
                )
                family_ind = independent_bootstrap_pvalues(
                    null_family, seed=seed + family_seed, replicates=replicates
                )
                for i in range(20):
                    trial_id = f"trial_{i:02d}"
                    if abs(family_prod[trial_id] - float(family_ind[i])) > 1e-12:
                        raise AssertionError(f"family bootstrap mismatch: {generator}, {trial_id}")
                for m in (5, 20):
                    ids_m = [f"trial_{i:02d}" for i in range(m)]
                    p_m = {key: family_prod[key] for key in ids_m}
                    prod_m = holm_step_down(p_m)
                    ind_m = _holm_rejections([p_m[key] for key in ids_m], ids_m)
                    if [prod_m[key]["rejected"] for key in ids_m] != ind_m:
                        raise AssertionError(f"family Holm mismatch: {generator}, m={m}")
                fixture["production_runner_p_values_match"] = True
            else:
                fixture["production_runner_p_values_match"] = None
            family_fixtures.append(fixture)

    result = {
        "status": "PASS",
        **provenance,
        "fixture_seed": seed,
        "bootstrap_replicates": replicates,
        "series_count": len(series),
        "family_fixture_count": len(family_fixtures),
        "trial_comparisons": comparisons,
        "family_fixtures": family_fixtures,
        "holm_rejections": {
            key: production_holm[key]["rejected"] for key in sorted(production_holm)
        },
        "limitations": [
            "This is a deterministic primitive-level cross-check, not a full campaign.",
            "The reduced 199-replicate fixture is not a production or calibration setting.",
        ],
    }
    result["validation_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--engine-revision", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = validate(Path(args.plan_file), args.engine_revision)
    payload = json.dumps(result, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        path = Path(args.output)
        if path.exists():
            raise SystemExit(f"refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()

"""Cross-check selected independent M3 v2 calibration primitives against production."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from openfx.selection_bias_v2 import (
    _bootstrap_pvalues as production_bootstrap_pvalues,
    _hac_studentized_mean,
    holm_step_down,
    sha256_json,
)
from research.m3_hac_mbb_v2_calibration import (
    _bootstrap_pvalues as independent_bootstrap_pvalues,
    _hac_statistic,
    _holm_rejections,
)


def _fixture_series() -> dict[str, list[float]]:
    result = {}
    for trial in range(3):
        result[f"trial_{trial:02d}"] = [
            0.02 * (trial + 1) + (((i * 17 + trial * 13) % 31) - 15) * 0.001
            for i in range(252)
        ]
    return result


def validate() -> dict:
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

    result = {
        "status": "PASS",
        "fixture_seed": seed,
        "bootstrap_replicates": replicates,
        "series_count": len(series),
        "trial_comparisons": comparisons,
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
    parser.add_argument("--output")
    args = parser.parse_args()
    result = validate()
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

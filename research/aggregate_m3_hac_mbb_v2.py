"""Validate and aggregate immutable M3 v2 calibration cell artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from research.m3_calibration_provenance import verify_execution_bindings

GENERATORS = ("N1_GAUSSIAN_IID", "N2_STUDENT_T5_IID", "N3_AR1_GAUSSIAN",
              "N4_GARCH_1_1", "N5_AR1_STUDENT_T5")
CORRELATIONS = (0.0, 0.5, 0.9)


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha256(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load_cell(path: Path, expected_plan: str | None = None) -> dict:
    cell = json.loads(path.read_text(encoding="utf-8"))
    claimed = cell.get("cell_sha256")
    unhashed = dict(cell)
    unhashed.pop("cell_sha256", None)
    if claimed != _sha256(unhashed):
        raise ValueError(f"cell hash mismatch: {path.name}")
    if expected_plan and cell.get("plan_sha256") != expected_plan:
        raise ValueError(f"plan hash mismatch: {path.name}")
    return cell


def _check_runtime_and_revisions(cells: list[dict]) -> None:
    for key in ("plan_sha256", "engine_revision", "runner_revision", "runtime"):
        values = {json.dumps(cell.get(key), sort_keys=True) for cell in cells}
        if len(values) != 1:
            raise ValueError(f"calibration cells disagree on {key}")


def _check_marginal(cell: dict, phase: str, generator: str, generator_index: int) -> None:
    expected_phase = "marginal_null" if phase == "null" else "marginal_mde"
    expected_count = 5000 if phase == "null" else 1000
    if (cell.get("phase") != expected_phase or cell.get("generator") != generator
            or cell.get("plan_id") != "M3-HAC-MBB-CALIBRATION-V2-2"
            or cell.get("method_id") != "M3-HOLM-HAC-MBB-V2"
            or cell.get("method_version") != "2.0.2"):
        raise ValueError("marginal cell identity/method version mismatch")
    settings = cell.get("settings", {})
    expected_settings = {"n": 252, "alpha": 0.05, "bootstrap_replicates": 9999,
                         "block_length": 7, "hac_lag": 7, "max_observations": 100_000,
                         "max_trials": 10_000, "max_bootstrap_work": 1_000_000_000,
                         "replicates": expected_count}
    if any(settings.get(key) != value for key, value in expected_settings.items()):
        raise ValueError("marginal cell settings do not match frozen v2.0.2 plan")
    if cell.get("failed_replicates") != 0:
        raise ValueError("marginal cell contains failed replicates")
    rows = cell.get("replicates")
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise ValueError("marginal replicate count mismatch")
    seen = set()
    for row in rows:
        index = row.get("replicate")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < expected_count or index in seen:
            raise ValueError("marginal replicate indices are malformed")
        seen.add(index)
        data_base = 2_400_000_000 if phase == "mde" else 2_300_000_000
        bootstrap_base = 2_900_000_000 if phase == "mde" else 2_800_000_000
        expected_data_seed = data_base + generator_index * 100_000 + index
        if (row.get("data_seed") != expected_data_seed
                or row.get("bootstrap_seed") != bootstrap_base + expected_data_seed):
            raise ValueError("marginal seed map mismatch")
        if row.get("engine_revision") != cell.get("engine_revision"):
            raise ValueError("marginal engine revision does not match frozen calibration engine revision")
        if row.get("status") != "completed" or not isinstance(row.get("returns_sha256"), str) or len(row["returns_sha256"]) != 64:
            raise ValueError("marginal replicate missing completed evidence")
        p = row.get("p_value")
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("invalid marginal p-value")
    if seen != set(range(expected_count)):
        raise ValueError("marginal replicate sequence is incomplete")


def _check_family(cell: dict, phase: str, generator: str, generator_index: int, rho: float) -> None:
    expected_phase = "family_null" if phase == "null" else "family_mde"
    if (cell.get("phase") != expected_phase or cell.get("generator") != generator
            or cell.get("rho") != rho
            or cell.get("plan_id") != "M3-HAC-MBB-CALIBRATION-V2-2"
            or cell.get("method_id") != "M3-HOLM-HAC-MBB-V2"
            or cell.get("method_version") != "2.0.2"):
        raise ValueError("family cell identity/method version mismatch")
    settings = cell.get("settings", {})
    expected_settings = {"n": 252, "alpha": 0.05, "bootstrap_replicates": 9999,
                         "block_length": 7, "hac_lag": 7, "max_observations": 100_000,
                         "max_trials": 10_000, "max_bootstrap_work": 1_000_000_000,
                         "families": 1000, "family_size_primary": 20,
                         "family_size_secondary": 5,
                         "estimated_bootstrap_work_per_family": 9999 * 20 * 252 * 8}
    if any(settings.get(key) != value for key, value in expected_settings.items()):
        raise ValueError("family cell settings do not match frozen v2.0.2 plan")
    if cell.get("failed_families") != 0:
        raise ValueError("family cell contains failed families")
    rows = cell.get("families")
    if not isinstance(rows, list) or len(rows) != 1000:
        raise ValueError("family replicate count mismatch")
    seen = set()
    for row in rows:
        index = row.get("family_index")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 1000 or index in seen:
            raise ValueError("family indices are malformed")
        seen.add(index)
        correlation_index = CORRELATIONS.index(rho)
        data_base = 2_600_000_000 if phase == "mde" else 2_500_000_000
        expected_family_seed = data_base + generator_index * 1_000_000 + correlation_index * 10_000 + index
        if row.get("family_seed") != expected_family_seed or row.get("bootstrap_seed") != 2_700_000_000 + expected_family_seed:
            raise ValueError("family seed map mismatch")
        if row.get("status") != "completed":
            raise ValueError("family replicate is not completed")
        hashes = row.get("trial_return_hashes")
        pvalues = row.get("raw_p_values")
        if row.get("trial_ids") != [f"trial_{i:02d}" for i in range(20)]:
            raise ValueError("family trial membership/order mismatch")
        if row.get("trial_engine_revisions") != [cell.get("engine_revision")] * 20:
            raise ValueError("family trial engine revisions do not match frozen calibration engine revision")
        if not isinstance(hashes, list) or len(hashes) != 20 or any(not isinstance(x, str) or len(x) != 64 for x in hashes):
            raise ValueError("family trial return hashes are incomplete")
        if not isinstance(pvalues, list) or len(pvalues) != 20:
            raise ValueError("family raw p-values are incomplete")
        if any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1 for p in pvalues):
            raise ValueError("family contains an invalid raw p-value")
        realized = row.get("realized_average_pairwise_return_correlation")
        if isinstance(realized, bool) or not isinstance(realized, (int, float)) or not math.isfinite(realized) or not -1 <= realized <= 1:
            raise ValueError("family realized correlation is missing or invalid")
    if seen != set(range(1000)):
        raise ValueError("family replicate sequence is incomplete")


def aggregate(input_dir: Path, output_path: Path, reference_path: Path, plan_file: Path) -> dict:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path}")
    expected_plan_sha256 = hashlib.sha256(plan_file.read_bytes()).hexdigest()
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    reference_hash = reference.get("validation_sha256")
    reference_unhashed = dict(reference)
    reference_unhashed.pop("validation_sha256", None)
    if reference.get("status") != "PASS" or reference_hash != _sha256(reference_unhashed):
        raise ValueError("independent production-vs-runner reference check is missing or invalid")
    if (reference.get("bootstrap_replicates") != 199 or reference.get("series_count") != 3
            or reference.get("family_fixture_count") != 15):
        raise ValueError("reference check fixture contract mismatch")
    cells = []
    marginal_null = {}
    marginal_mde = {}
    family_null = {}
    family_mde = {}

    for generator in GENERATORS:
        for phase, target in (("null", marginal_null), ("mde", marginal_mde)):
            path = input_dir / f"marginal-{phase}-{generator}.json"
            cell = _load_cell(path, expected_plan_sha256)
            _check_marginal(cell, phase, generator, GENERATORS.index(generator))
            target[generator] = cell
            cells.append(cell)
        for rho in CORRELATIONS:
            tag = str(rho).replace(".", "p")
            for phase, target in (("null", family_null), ("mde", family_mde)):
                path = input_dir / f"family-{phase}-{generator}-rho-{tag}.json"
                cell = _load_cell(path, expected_plan_sha256)
                _check_family(cell, phase, generator, GENERATORS.index(generator), rho)
                target[(generator, rho)] = cell
                cells.append(cell)

    _check_runtime_and_revisions(cells)
    provenance = verify_execution_bindings(
        plan_file, cells[0]["engine_revision"],
        Path(__file__).resolve().parents[1] / "research" / "m3_hac_mbb_v2_calibration.py",
        Path(__file__).resolve().parents[1] / "openfx" / "selection_bias_v2.py",
    )
    if cells[0]["runner_revision"] != provenance["runner_revision"]:
        raise ValueError("cell runner revision does not match the current clean checkout")
    if (reference.get("plan_sha256") != expected_plan_sha256
            or reference.get("engine_revision") != cells[0]["engine_revision"]
            or reference.get("runner_revision") != cells[0]["runner_revision"]):
        raise ValueError("reference check provenance does not match calibration cells")
    plan_hash = cells[0]["plan_sha256"]
    if not isinstance(plan_hash, str) or len(plan_hash) != 64:
        raise ValueError("invalid plan SHA-256")
    for key in ("engine_revision", "runner_revision"):
        revision = cells[0][key]
        if not isinstance(revision, str) or len(revision) not in (40, 64) or any(ch not in "0123456789abcdef" for ch in revision):
            raise ValueError(f"invalid {key} Git SHA")

    marginal_null_checks = {}
    for generator, cell in marginal_null.items():
        s = cell["summary"]
        marginal_null_checks[generator] = bool(
            s["estimate"] <= 0.055 and s["upper_95"] <= 0.065
        )
    marginal_mde_checks = {
        generator: bool(cell["summary"]["lower_95"] >= 0.80)
        for generator, cell in marginal_mde.items()
    }
    family_null_checks = {}
    for key, cell in family_null.items():
        s = cell["summary"]
        family_null_checks[f"{key[0]}|rho={key[1]}|m=5"] = bool(
            s["global_null_fwer_m5"]["estimate"] <= 0.055
            and s["global_null_fwer_m5"]["upper_95"] <= 0.065
        )
        family_null_checks[f"{key[0]}|rho={key[1]}|m=20"] = bool(
            s["global_null_fwer_m20"]["estimate"] <= 0.055
            and s["global_null_fwer_m20"]["upper_95"] <= 0.065
        )
    family_mde_checks = {}
    for key, cell in family_mde.items():
        s = cell["summary"]
        family_mde_checks[f"{key[0]}|rho={key[1]}|m=5"] = bool(
            s["mde_family_power_m5"]["lower_95"] >= 0.80
        )
        family_mde_checks[f"{key[0]}|rho={key[1]}|m=20"] = bool(
            s["mde_family_power_m20"]["lower_95"] >= 0.80
        )

    acceptance = {
        "marginal_null": all(marginal_null_checks.values()),
        "marginal_mde_power": all(marginal_mde_checks.values()),
        "direct_family_global_null_fwer": all(family_null_checks.values()),
        "direct_family_mde_power": all(family_mde_checks.values()),
    }
    acceptance["accepted"] = all(acceptance.values())
    result = {
        "plan_id": "M3-HAC-MBB-CALIBRATION-V2-2",
        "plan_sha256": plan_hash,
        "engine_revision": cells[0]["engine_revision"],
        "runner_revision": cells[0]["runner_revision"],
        "runtime": cells[0]["runtime"],
        "reference_validation_sha256": reference_hash,
        "cell_count": len(cells),
        "expected_cell_count": 40,
        "acceptance": acceptance,
        "checks": {
            "marginal_null": marginal_null_checks,
            "marginal_mde_power": marginal_mde_checks,
            "direct_family_global_null_fwer": family_null_checks,
            "direct_family_mde_power": family_mde_checks,
        },
        "summaries": {
            "marginal_null": {key: value["summary"] for key, value in marginal_null.items()},
            "marginal_mde_power": {key: value["summary"] for key, value in marginal_mde.items()},
            "direct_family_global_null_fwer": {
                f"{key[0]}|rho={key[1]}": value["summary"] for key, value in family_null.items()
            },
            "direct_family_mde_power": {
                f"{key[0]}|rho={key[1]}": value["summary"] for key, value in family_mde.items()
            },
        },
        "cell_hashes": sorted(cell["cell_sha256"] for cell in cells),
        "limitations": [
            "Synthetic calibration only; not market evidence or a profitability guarantee.",
            "HAC/MBB assumptions may fail under structural breaks, long memory, or non-stationarity.",
            "A calibration pass does not authorize broad optimization, MT5, VPS, broker access, or live trading.",
        ],
    }
    result["campaign_sha256"] = _sha256(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=False) + "\n",
                           encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--reference-check", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = aggregate(Path(args.input_dir), Path(args.output), Path(args.reference_check),
                       Path(args.plan_file))
    print(json.dumps({"output": args.output, "campaign_sha256": result["campaign_sha256"],
                      "acceptance": result["acceptance"]}, sort_keys=True))


if __name__ == "__main__":
    main()

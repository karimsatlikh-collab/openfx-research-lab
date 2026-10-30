"""Validate and aggregate immutable M3 v2 calibration cell artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

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
    if cell.get("phase") != expected_phase or cell.get("generator") != generator:
        raise ValueError("marginal cell identity mismatch")
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
        data_base = 400_000_000 if phase == "mde" else 300_000_000
        bootstrap_base = 900_000_000 if phase == "mde" else 800_000_000
        expected_data_seed = data_base + generator_index * 100_000 + index
        if (row.get("data_seed") != expected_data_seed
                or row.get("bootstrap_seed") != bootstrap_base + expected_data_seed):
            raise ValueError("marginal seed map mismatch")
        if row.get("status") != "completed" or not isinstance(row.get("returns_sha256"), str) or len(row["returns_sha256"]) != 64:
            raise ValueError("marginal replicate missing completed evidence")
        p = row.get("p_value")
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("invalid marginal p-value")
    if seen != set(range(expected_count)):
        raise ValueError("marginal replicate sequence is incomplete")


def _check_family(cell: dict, phase: str, generator: str, generator_index: int, rho: float) -> None:
    expected_phase = "family_null" if phase == "null" else "family_mde"
    if cell.get("phase") != expected_phase or cell.get("generator") != generator or cell.get("rho") != rho:
        raise ValueError("family cell identity mismatch")
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
        data_base = 600_000_000 if phase == "mde" else 500_000_000
        expected_family_seed = data_base + generator_index * 1_000_000 + correlation_index * 10_000 + index
        if row.get("family_seed") != expected_family_seed or row.get("bootstrap_seed") != 700_000_000 + expected_family_seed:
            raise ValueError("family seed map mismatch")
        if row.get("status") != "completed":
            raise ValueError("family replicate is not completed")
        hashes = row.get("trial_return_hashes")
        pvalues = row.get("raw_p_values")
        if row.get("trial_ids") != [f"trial_{i:02d}" for i in range(20)]:
            raise ValueError("family trial membership/order mismatch")
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


def aggregate(input_dir: Path, output_path: Path) -> dict:
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite {output_path}")
    cells = []
    marginal_null = {}
    marginal_mde = {}
    family_null = {}
    family_mde = {}

    for generator in GENERATORS:
        for phase, target in (("null", marginal_null), ("mde", marginal_mde)):
            path = input_dir / f"marginal-{phase}-{generator}.json"
            cell = _load_cell(path)
            _check_marginal(cell, phase, generator, GENERATORS.index(generator))
            target[generator] = cell
            cells.append(cell)
        for rho in CORRELATIONS:
            tag = str(rho).replace(".", "p")
            for phase, target in (("null", family_null), ("mde", family_mde)):
                path = input_dir / f"family-{phase}-{generator}-rho-{tag}.json"
                cell = _load_cell(path)
                _check_family(cell, phase, generator, GENERATORS.index(generator), rho)
                target[(generator, rho)] = cell
                cells.append(cell)

    _check_runtime_and_revisions(cells)
    plan_hash = cells[0]["plan_sha256"]
    if not isinstance(plan_hash, str) or len(plan_hash) != 64:
        raise ValueError("invalid plan SHA-256")

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
        "plan_id": "M3-HAC-MBB-CALIBRATION-V2",
        "plan_sha256": plan_hash,
        "engine_revision": cells[0]["engine_revision"],
        "runner_revision": cells[0]["runner_revision"],
        "runtime": cells[0]["runtime"],
        "cell_count": len(cells),
        "expected_cell_count": 40,
        "acceptance": acceptance,
        "checks": {
            "marginal_null": marginal_null_checks,
            "marginal_mde_power": marginal_mde_checks,
            "direct_family_global_null_fwer": family_null_checks,
            "direct_family_mde_power": family_mde_checks,
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
    parser.add_argument("--expected-plan-sha256")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = aggregate(Path(args.input_dir), Path(args.output))
    if args.expected_plan_sha256 and result["plan_sha256"] != args.expected_plan_sha256:
        Path(args.output).unlink(missing_ok=True)
        raise SystemExit("aggregated plan hash does not match --expected-plan-sha256")
    print(json.dumps({"output": args.output, "campaign_sha256": result["campaign_sha256"],
                      "acceptance": result["acceptance"]}, sort_keys=True))


if __name__ == "__main__":
    main()

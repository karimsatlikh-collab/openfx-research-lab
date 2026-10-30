"""Performance preflight for the frozen M3 v2.0.3 family workload.

This produces runtime estimates only. It is not a calibration cell and its
outputs must never be included in the 40-cell acceptance campaign.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.m3_calibration_provenance import verify_execution_bindings
from research.m3_hac_mbb_v2_calibration import (
    BOOTSTRAP_REPLICATES,
    _generate_family,
    _bootstrap_pvalues,
    _runtime,
    _series_sha256,
)

ENGINE_REVISION = "087e66622f27350f1999d2e5b2ec82a9ead78982"
BENCHMARK_FAMILY_SEED_BASE = 3_950_000_000
BENCHMARK_BOOTSTRAP_SEED_BASE = 3_960_000_000
TOTAL_FAMILY_EQUIVALENTS = 151_500


def run(plan_file: Path, families: int) -> dict:
    provenance = verify_execution_bindings(
        plan_file, ENGINE_REVISION,
        ROOT / "research" / "m3_hac_mbb_v2_calibration.py",
        ROOT / "openfx" / "selection_bias_v2.py",
    )

    # Compile the Numba kernel using a small, non-campaign warm-up.
    warmup = _generate_family(
        "N3_AR1_GAUSSIAN", BENCHMARK_FAMILY_SEED_BASE, 0.5, False
    )
    _bootstrap_pvalues(warmup, BENCHMARK_BOOTSTRAP_SEED_BASE, replicates=199)

    timings = []
    pvalue_outputs = []
    return_hashes = []
    for index in range(families):
        seed = BENCHMARK_FAMILY_SEED_BASE + index + 1
        started = time.perf_counter()
        values = _generate_family("N3_AR1_GAUSSIAN", seed, 0.5, False)
        series_hashes = [_series_sha256(values[i]) for i in range(20)]
        pvalues = _bootstrap_pvalues(
            values, BENCHMARK_BOOTSTRAP_SEED_BASE + index + 1,
            replicates=BOOTSTRAP_REPLICATES,
        )
        elapsed = time.perf_counter() - started
        if len(pvalues) != 20 or not all(0.0 <= float(p) <= 1.0 for p in pvalues):
            raise RuntimeError("benchmark produced invalid p-values")
        timings.append(elapsed)
        pvalue_outputs.append([float(x) for x in pvalues])
        return_hashes.append(series_hashes)

    average = sum(timings) / len(timings)
    result = {
        "evidence_class": "performance_preflight_only_not_calibration",
        "plan_id": "M3-HAC-MBB-CALIBRATION-V2-3",
        **provenance,
        "runtime": _runtime(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "warmup_bootstrap_replicates": 199,
        "timed_bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "timed_families": families,
        "family_seconds": timings,
        "mean_seconds_per_family": average,
        "estimated_total_family_equivalents": TOTAL_FAMILY_EQUIVALENTS,
        "estimated_campaign_cpu_hours": average * TOTAL_FAMILY_EQUIVALENTS / 3600.0,
        "benchmark_seed_ranges": {
            "family": [BENCHMARK_FAMILY_SEED_BASE, BENCHMARK_FAMILY_SEED_BASE + families],
            "bootstrap": [BENCHMARK_BOOTSTRAP_SEED_BASE, BENCHMARK_BOOTSTRAP_SEED_BASE + families],
        },
        "pvalue_output_sha256": __import__("hashlib").sha256(
            json.dumps(pvalue_outputs, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest(),
        "return_hashes_sha256": __import__("hashlib").sha256(
            json.dumps(return_hashes, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest(),
        "limitations": [
            "This measures one declared family generator on this host only.",
            "It excludes cell serialization, storage, aggregation, and process startup.",
            "It is a throughput estimate, not evidence about null error rates, power, or profitability.",
        ],
    }
    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode("utf-8")
    result["benchmark_sha256"] = __import__("hashlib").sha256(canonical).hexdigest()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--families", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not 3 <= args.families <= 20:
        raise SystemExit("--families must be between 3 and 20")
    result = run(Path(args.plan_file), args.families)
    payload = json.dumps(result, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        path = Path(args.output)
        if path.exists():
            raise SystemExit(f"refusing to overwrite existing benchmark artifact: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
